# usr/bin/env python
# -*- coding: utf-8 -*-
import random
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import get_callable as _get_callable


def get_callable(*args, **kwargs):
    quiet = kwargs.pop('quiet', False)
    if quiet:
        try:
            return _get_callable(*args, **kwargs)
        except Exception as e:
            print(e)
            return None
    return _get_callable(*args, **kwargs)


default_client = None
sms_config = getattr(settings, 'SMS_CONFIG', {})
backend = get_callable(sms_config.get('BACKEND'), quiet=True)
sms_client = None
if backend:
    sms_client = backend(sms_config)
code_expires = getattr(sms_config, 'CODE_EXPIRES', 300)


def default_dead_time():
    return timezone.now() + timezone.timedelta(seconds=code_expires)


class SMSToken(models.Model):
    """ SMS Token """
    phone = models.CharField(_('Phone'), max_length=20, unique=True)
    code = models.CharField(_('Code'), max_length=10)
    create_time = models.DateTimeField(_('Create Time'), auto_now_add=True)
    dead_time = models.DateTimeField(_('Dead Time'), default=default_dead_time)

    class Meta:
        verbose_name = verbose_name_plural = _('SMS Token')
        ordering = ('-create_time', )

    def is_valid(self, code):
        if self.dead_time > timezone.now():
            return self.code == code
        return False

    def send_code(self):
        template_code = sms_config.get('CODE_TEMPLATE', '')
        params = {
            'code': self.code,
            'expire': str(int(code_expires/60))
        }
        return sms_client.send_sms(self.phone, params=params, template_code=template_code)

    @staticmethod
    def generate_code(code_bits):
        l = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ]
        return ''.join(random.sample(l, code_bits))

    @classmethod
    def create(cls, phone):
        dead_delay = sms_config.get('CODE_EXPIRES', 300)
        dead_time = timezone.now() + timezone.timedelta(seconds=dead_delay)
        code_bits = sms_config.get('TOKEN_BIT', 6)
        code = cls.generate_code(code_bits)
        obj, created = cls.objects.update_or_create(phone=phone, defaults={
            'code': code, 'dead_time': dead_time
        })
        return obj

    @classmethod
    def check_code(cls, phone, code):
        try:
            obj = cls.objects.get(phone=phone)
            return obj.is_valid(code)
        except cls.DoesNotExist:
            return False
