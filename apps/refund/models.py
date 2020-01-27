import time
from random import Random
from django.db import models

# Create your models here.


def generate_ptgroup_sn(user):
    random_ins = Random()
    return f'RF{time.strftime("%m%d%H%M%S")}{user.id%1000:0>4}{random_ins.randint(10, 99)}'


class RefundRecord(models.Model):

    APPLY = 'apply'
    REFUND = 'refund'

    STATUS = ((APPLY, '申请中'), (REFUND, '已到账'))

    refund_no = models.CharField(max_length=30, null=True, blank=True, unique=True, verbose_name="退款单号")
    order = models.ForeignKey('trade.Orders', related_name='refund_records', verbose_name='退款记录', on_delete=models.CASCADE)
    user = models.ForeignKey('wxapp.WxUser', related_name='refund_records', verbose_name='微信用户', on_delete=models.CASCADE)
    refund_id = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="微信退款单号")
    real_amount = models.DecimalField(verbose_name="微信支付退款金额", max_digits=15, decimal_places=2, default=0)
    asset_pay = models.DecimalField(verbose_name="收益支付退款金额", max_digits=15, decimal_places=2, default=0)
    recharge_pay = models.DecimalField(verbose_name="充值支付退款金额", max_digits=15, decimal_places=2, default=0)
    refund_desc = models.CharField(verbose_name='退款原因', max_length=255)
    status = models.CharField(verbose_name='退款状态',max_length=30,  choices=STATUS, default=APPLY)
    add_time = models.DateTimeField(verbose_name='发起时间', auto_now_add=True)
    refund_time = models.DateTimeField(verbose_name='到账时间', null=True)

    @classmethod
    def create(cls, order, user, real_amount, asset_pay, recharge_pay, refund_desc):
        kwargs = locals()
        kwargs.pop('cls', None)
        kwargs.update({'refund_no': generate_ptgroup_sn(user)})
        return cls.objects.create(**kwargs)

    @property
    def refund_money(self):
        """ 退款的金额 """
        return self.real_amount + self.asset_pay + self.recharge_pay
