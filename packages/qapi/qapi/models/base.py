from django.db import models
from django.conf import settings


__all__ = ['CreateModifyModel', ]


class CreateModifyModel(models.Model):

    create_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='创建者', related_name='create_%(class)s', on_delete=models.CASCADE, null=True, blank=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    modify_user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='修改者', related_name='modify_%(class)s', on_delete=models.CASCADE, null=True, blank=True)
    modify_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        abstract = True
