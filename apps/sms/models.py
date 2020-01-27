import random
import string
import time
from django.db import models

# Create your models here.


class SmsRecord(models.Model):
    phone = models.CharField(verbose_name='手机号码', max_length=20)
    model_code = models.CharField(verbose_name='模板CODE', max_length=20)
    add_time = models.DateTimeField(verbose_name='发送时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '短信发送记录'
        ordering = ('-add_time', )


class SmsSwitch(models.Model):
    label = models.CharField(verbose_name='短信类型', max_length=100)
    sms_type = models.CharField(verbose_name='code', max_length=100)
    switch = models.BooleanField(verbose_name='开关', default=True)

    class Meta:
        verbose_name = verbose_name_plural = '短信服务开关'

    def __str__(self):
        return self.label

    @classmethod
    def get(cls, value):
        try:
            instance = cls.objects.get(sms_type=value)
            return instance.switch
        except cls.DoesNotExist:
            return False


class SmsBalance(models.Model):
    num = models.PositiveSmallIntegerField(verbose_name='短信余额', default=0)

    class Meta:
        verbose_name = verbose_name_plural = '短信余额'

    @classmethod
    def get(cls):
        instance = cls.objects.first()
        if not instance:
            instance = cls.objects.create(num=0)
        return instance


def generate_no():
    salt = ''.join(random.choice(string.digits) for _ in range(6))
    return 'SMS' + "{}{}".format(time.strftime("%Y%m%d%H%M%S"), salt)


class SMSRechargeRecord(models.Model):
    out_trade_no = models.CharField(verbose_name='订单号', max_length=100, default=generate_no)
    transaction_id = models.CharField(verbose_name='微信交易号', max_length=100, null=True)
    amount = models.PositiveSmallIntegerField(verbose_name='充值金额')
    num = models.PositiveSmallIntegerField(verbose_name='增加短信个数')
    has_paid = models.BooleanField(verbose_name='是否已支付', default=False)
    paid_time = models.DateTimeField(verbose_name='支付时间', null=True)
    created_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '短信服务充值记录'

    @classmethod
    def create(cls, amount):
        num = amount * 10
        if amount >= 100:
            num += (amount // 100) * 200
        instance = cls.objects.create(amount=amount, num=num)
        return instance
