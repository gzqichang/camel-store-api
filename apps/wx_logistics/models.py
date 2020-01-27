from django.db import models
from django.contrib.postgres import fields

from .mixins import TimeLogMixin, IsActiveMixin


SHOP = 'shop.Shop'
ORDER = 'trade.Orders'
ITEMS = 'trade.Items'
WXAPP = 'wxapp.WxUser'


class DeliveryAccount(IsActiveMixin, models.Model):
    """
    物流账号
    """
    shop = models.ForeignKey(
        SHOP,
        verbose_name='所属店铺',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    biz_id = models.CharField('快递公司客户编码', max_length=64)
    delivery_id = models.CharField('快递公司ID', max_length=64)
    password = models.CharField('快递公司客户密码', max_length=64)

    class Meta:
        verbose_name = verbose_name_plural = '物流账号'

    def __str__(self):
        return ' '.join([
            self.shop.name,
            self.delivery_id,
            self.biz_id,
        ])


class Sender(IsActiveMixin, models.Model):
    """
    发件人信息
    """
    shop = models.ForeignKey(
        SHOP,
        verbose_name='所属店铺',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField('姓名', max_length=64)
    tel = models.CharField('座机号码', max_length=64, null=True, blank=True)
    mobile = models.CharField('手机号码', max_length=64, null=True, blank=True)
    company = models.CharField('公司名称', max_length=64, null=True, blank=True)
    post_code = models.CharField('邮编', max_length=64, null=True, blank=True)
    country = models.CharField('国家', max_length=64, null=True, blank=True)
    province = models.CharField('省份', max_length=64)
    city = models.CharField('市/地区', max_length=64)
    area = models.CharField('区/县', max_length=64)
    address = models.CharField('详细地址', max_length=512)

    class Meta:
        verbose_name = verbose_name_plural = '发件人信息'

    def __str__(self):
        return ' '.join([
            self.shop.name,
            self.name,
        ])


class DeliveryRecords(TimeLogMixin, models.Model):
    """
    订单 - 运单 - 记录
    """
    related_name = 'delivery_records'

    shop = models.ForeignKey(
        SHOP,
        verbose_name='所属店铺',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    order = models.ForeignKey(
        ORDER,
        verbose_name='商品订单',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name=related_name,
    )
    items = models.ManyToManyField(
        ITEMS,
        verbose_name='子订单',
        related_name=related_name,
    )
    wx_order_id = models.CharField('微信订单ID', max_length=64)
    delivery_id = models.CharField('快递公司ID', max_length=64)
    waybill_id = models.CharField('运单ID', max_length=64)
    waybill_data = fields.JSONField('运单信息')

    class Meta:
        verbose_name = verbose_name_plural = '运单记录'

    def __str__(self):
        return self.waybill_id


class DeliveryPrinter(models.Model):
    """
    打印员
    """
    related_name = 'delivery_printers'

    shop = models.ForeignKey(
        SHOP,
        verbose_name='所属店铺',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name=related_name,
    )
    user = models.ForeignKey(
        WXAPP,
        verbose_name='打印员',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name=related_name,
    )
    tags = models.CharField('打印员权限集', max_length=128)

    class Meta:
        verbose_name = verbose_name_plural = '打印员'

    def __str__(self):
        return ' '.join([
            self.shop.name,
            self.user.nickname,
        ])
