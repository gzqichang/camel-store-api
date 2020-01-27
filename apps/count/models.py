from django.db import models


class Count(models.Model):
    date = models.DateField(verbose_name='日期')
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', null=True, blank=True, on_delete=models.SET_NULL)
    turnovers = models.DecimalField(verbose_name='营业额', max_digits=30, decimal_places=2, default=0)
    order_count = models.PositiveIntegerField(verbose_name='订单量')

    class Meta:
        verbose_name = verbose_name_plural = '每日订单量营业额统计'
        ordering = ('-date', )

        permissions = (
            ('view_total_count', '查看所有店汇总'),
        )


class FeedbackStatistics(models.Model):
    date = models.DateField(verbose_name='日期')
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', null=True, blank=True, on_delete=models.SET_NULL)
    new_num = models.PositiveIntegerField(verbose_name='新增反馈数量', default=0)
    solve_num = models.PositiveIntegerField(verbose_name='解决反馈数量', default=0)

    class Meta:
        verbose_name = verbose_name_plural = '每日用户反馈统计'
        ordering = ('-date', )


class WithdrawStatistics(models.Model):
    date = models.DateField(verbose_name='日期')
    withdraw_num = models.PositiveIntegerField(verbose_name='申请提现数量', default=0)
    amount_total = models.DecimalField(verbose_name='申请提现记录总金额', decimal_places=2, max_digits=15)
    succ_num = models.PositiveIntegerField(verbose_name='完成提现数量')

    class Meta:
        verbose_name = verbose_name_plural = '每日提现统计'
        ordering = ('-date', )


class RechargeStatistics(models.Model):
    date = models.DateField(verbose_name='日期')
    recharge_num = models.PositiveIntegerField(verbose_name='充值数量', default=0)
    amount_total = models.DecimalField(verbose_name='充值总金额', decimal_places=2, max_digits=15)

    class Meta:
        verbose_name = verbose_name_plural = '每日充值统计'
        ordering = ('-date', )


class WxUserStatistics(models.Model):
    date = models.DateField(verbose_name='日期')
    new_user_num = models.PositiveIntegerField(verbose_name='新增用户数量', default=0)
    user_total = models.PositiveIntegerField(verbose_name='新增用户数量', default=0)

    class Meta:
        verbose_name = verbose_name_plural = '每日新增用户统计'
        ordering = ('-date', )


class OrderStatistics(models.Model):
    date = models.DateField(verbose_name='日期')
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', null=True, blank=True, on_delete=models.SET_NULL)
    ord_num = models.PositiveIntegerField(verbose_name='普通订单数量', default=0)
    repl_num = models.PositiveIntegerField(verbose_name='积分换购订单数量', default=0)
    qrpay_num = models.PositiveIntegerField(verbose_name='扫码支付订单数量', default=0)

    class Meta:
        verbose_name = verbose_name_plural = '每日订单统计'
        ordering = ('-date', )


class TurnoversStatistics(models.Model):
    date = models.DateField(verbose_name='日期')
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', null=True, blank=True, on_delete=models.SET_NULL)
    ord_turnovers = models.DecimalField(verbose_name='普通订单总销售额', decimal_places=2, max_digits=15)
    qrpay_turnovers = models.DecimalField(verbose_name='扫码支付订单总销售额', decimal_places=2, max_digits=15, default=0)
    turnovers = models.DecimalField(verbose_name='总销售额', decimal_places=2, max_digits=15)

    class Meta:
        verbose_name = verbose_name_plural = '每日销售额统计'
        ordering = ('-date', )