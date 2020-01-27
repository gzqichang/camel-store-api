import time
import simplejson as json
from decimal import Decimal
from random import Random
from django.utils import timezone
from django.db import models, transaction
from django.db.models import Sum
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.postgres.fields import JSONField
from apps.goods.models import Goods
from apps.account.models import WxUserAccountLog
# from apps.config.models import Config
from wxapp.models import WxUser
from apps.config.models import Marketing, BoolConfig
from apps.utils.lbs import lbs
from apps.goods.utils import gtype_sell, validate_can_sell, format_date
from apps.utils.disable_for_loaddata import disable_for_loaddata


def generate_order_sn(user):
    # 当前时间+userid+随机数
    random_ins = Random()
    order_sn = "{}{}{}".format(time.strftime("%Y%m%d%H%M%S"), user.id, random_ins.randint(10, 99))
    return order_sn


class UserAddress(models.Model):
    """
    用户收货地址
    """
    user = models.ForeignKey('wxapp.WxUser', verbose_name="用户", null=True, related_name='address',
                             on_delete=models.SET_NULL)
    name = models.CharField(max_length=100, default="", verbose_name="签收人")
    phone = models.CharField(max_length=20, default="", verbose_name="电话")
    region = models.CharField(max_length=100, default="", verbose_name="地区")
    location_detail = models.CharField(max_length=100, default="", verbose_name="详细地址")
    postcode = models.CharField(max_length=6, null=True, blank=True, verbose_name='邮编')
    is_default = models.BooleanField(verbose_name="是否默认地址", default=False)
    add_time = models.DateTimeField(auto_now_add=True, verbose_name="添加时间")
    lat = models.FloatField(verbose_name='纬度', null=True, blank=True)
    lng = models.FloatField(verbose_name='经度', null=True, blank=True)

    class Meta:
        verbose_name = "收货地址"
        verbose_name_plural = verbose_name
        ordering = ('-is_default',)

    def __str__(self):
        return self.location_detail

    @property
    def get_region(self):
        return self.region.replace(',', '')

    @property
    def address(self):
        return self.region.replace(',', '') + self.location_detail

    @property
    def location(self):
        if self.lat and self.lng:
            return {'lat': self.lat, 'lng': self.lng}
        location = lbs.get_longitude_and_latitude(address=self.address)
        try:
            self.lat = location.get('lat')
            self.lng = location.get('lng')
            self.save(update_fields=['lat', 'lng'])
        except AttributeError:
            print(location)
        return location

    @classmethod
    def get_address_by_locations(cls, lat, lng, user):
        '''
        根据一个坐标返回用户最近的收货地址
        :param lat: 经度
        :param lng: 纬度
        :param user: 用户
        :return:
        '''
        address_location = []
        address = cls.objects.filter(user=user)
        for a in address:
            location = a.location
            address_location.append("{},{}".format(location.get('lat'), location.get('lng')))
        from_location = f"{lat},{lng}"
        address_list = lbs.one_to_many_distance(from_location=from_location, to_location=address_location)
        if address_location and isinstance(address_location, list):
            return address[address_list[0].get('index')]
        return False


@receiver(pre_save, sender=UserAddress)
@disable_for_loaddata
def address_save(sender, instance, **kwargs):
    # 地址save前，更新地址的坐标
    update_fields = kwargs.get('update_fields')
    if update_fields != {'lat', 'lng'}:  # 如果某次save就是特定的更新坐标的操作，就不再调用lbs
        location = lbs.get_longitude_and_latitude(address=instance.address)
        try:
            instance.lat = location.get('lat')
            instance.lng = location.get('lng')
        except AttributeError:
            print(location)


class Express(models.Model):
    name = models.CharField(verbose_name='快递公司名称', max_length=128, unique=True)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '快递公司'

    def __str__(self):
        return self.name

    @classmethod
    def get_tuple(cls):
        expresses = cls.objects.all()

        express_list = []
        for express in expresses:
            express_list.append((express.name, express.name))
        return tuple(express_list)


class DeliveryAddress(models.Model):
    address_info = models.CharField(max_length=100, default="", verbose_name="收货地址")
    sign_name = models.CharField(max_length=20, default="", verbose_name="签收人")
    mobile_phone = models.CharField(max_length=20, default="", verbose_name="联系电话")
    postcode = models.CharField(max_length=6, null=True, blank=True, verbose_name='邮编')

    class Meta:
        verbose_name = verbose_name_plural = '配送地址'

    def __str__(self):
        return self.address_info

    @classmethod
    def create(cls, address):
        return cls.objects.create(address_info=address.address, sign_name=address.name, mobile_phone=address.phone,
                                  postcode=address.postcode)


class Invoice(models.Model):
    # 发票信息
    invoice_type = models.CharField(max_length=128, verbose_name='抬头类型', null=True, blank=True)
    title = models.CharField(max_length=128, verbose_name='抬头名称', null=True, blank=True)
    taxNumber = models.CharField(max_length=128, verbose_name='抬头税号', null=True, blank=True)
    companyAddress = models.CharField(max_length=128, verbose_name='单位地址', null=True, blank=True)
    telephone = models.CharField(max_length=128, verbose_name='手机号码', null=True, blank=True)
    bankName = models.CharField(max_length=128, verbose_name='银行名称', null=True, blank=True)
    bankAccount = models.CharField(max_length=128, verbose_name='银行账号', null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '发票信息'

    def __str__(self):
        return self.invoice_type


class Items(models.Model):
    # 子订单
    PAYING = "paying"
    SENDING = 'sending'
    RECEIVING = 'receiving'
    ARRIVE = 'arrive'
    OVER = 'over'
    CLOSE = 'close'

    STATUS = (
        (PAYING, "待付款"),
        (SENDING, "待发货/备货中"),
        (RECEIVING, "待收货/待取件"),
        (ARRIVE, '送达/提件'),
        (OVER, "已收货"),
        (CLOSE, '已关闭')
    )
    """
              paying  sending  receiving   arrive      over   close
    快递公司：  待付款   待发货     待收货         /      已收货    已关闭

   自配送：     待付款   待发货     待收货       已送达    已收货     已关闭

    自提       待付款    备货中      待取件      以提件     已收货    已关闭  

    """

    order = models.ForeignKey('trade.Orders', verbose_name='所属订单', related_name='items', on_delete=models.CASCADE)
    goods_backup = models.ForeignKey('trade.GoodsBackup', verbose_name='商品信息', on_delete=models.CASCADE)
    cycle = models.PositiveSmallIntegerField(verbose_name='期数', null=True, blank=True)
    send_date = models.DateField(verbose_name='配送日期', null=True, blank=True)
    send_start = models.TimeField(verbose_name='配送日开始配送时间', null=True, blank=True)
    send_end = models.TimeField(verbose_name='配送日结束配送时间', null=True, blank=True)
    send_type = models.CharField(verbose_name='配送状态', max_length=128, choices=STATUS, default=SENDING)
    express_num = models.CharField(max_length=50, verbose_name='快递单号', null=True, blank=True)
    express_company = models.CharField(max_length=30, verbose_name='快递公司', null=True, blank=True)
    send_time = models.DateTimeField(verbose_name='发货时间', null=True, blank=True)
    receive_time = models.DateTimeField(null=True, blank=True, verbose_name='收货时间')
    flag_time = models.DateTimeField(verbose_name='时间标志', db_index=True, null=True, blank=True)  # 时间标志，用于自动收货

    class Meta:
        verbose_name = verbose_name_plural = '子订单'
        ordering = ('id',)

    def __str__(self):
        return f"所属订单：{self.order.order_sn}"

    @property
    def order_sn(self):
        return self.order.order_sn

    @classmethod
    def create(cls, order, goods_backup, cycle=None, send_date=None, send_start=None, send_end=None, send_type=PAYING):
        kwargs = locals()
        kwargs.pop('cls', None)
        instance = cls(**kwargs)
        instance.save()
        return instance


class OrdGoodsBackUp(models.Model):
    estimate_time =JSONField(verbose_name='预计时间', null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '普通商品特定信息'


class ReplGoodsBackUp(models.Model):
    credit = models.PositiveIntegerField(verbose_name='积分', default=0)
    estimate_time =JSONField(verbose_name='预计时间', null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = '换购商品特定信息'


class GoodsBackup(models.Model):
    # 商品快照

    OWN = 'own'
    EXPRESS = 'express'
    BUYER = 'buyer'

    METHOD = ((OWN, '商家自配送'), (EXPRESS, '快递配送'), (BUYER, '用户自提'))

    order = models.ForeignKey('trade.Orders', verbose_name='所属订单', related_name='goods_backup',
                              on_delete=models.CASCADE)
    goods = models.ForeignKey('goods.Goods', verbose_name='商品', null=True, on_delete=models.SET_NULL)
    gtype_id = models.PositiveIntegerField(verbose_name='规格的id', null=True)
    goods_name = models.CharField(max_length=100, verbose_name="商品名")
    g_image = models.CharField(max_length=100, verbose_name='商品封面图路径', null=True, blank=True)
    gtype_name = models.CharField(max_length=100, verbose_name="规格")
    price = models.DecimalField(verbose_name="单价", max_digits=15, decimal_places=2)
    original_price = models.DecimalField(verbose_name='原价', default=0.0, max_digits=15, decimal_places=2)  # 会员折扣时记录原价
    market_price = models.DecimalField(verbose_name='市场价', default=0.0, max_digits=15, decimal_places=2)
    num = models.PositiveIntegerField(verbose_name="数量", default=1)
    attach = models.TextField(verbose_name='自定义字段', null=True)
    # 分销返利
    share_user_id = models.CharField(null=True, blank=True, verbose_name='分享用户的ID', max_length=128)
    g_rebate = models.PositiveIntegerField(verbose_name='返利金额', null=True)
    g_bonus = models.DecimalField(verbose_name='分销金额', max_digits=15, decimal_places=2, null=True)
    delivery_method = models.CharField(verbose_name='配送方式', choices=METHOD, max_length=128)
    ord_goods_info = models.OneToOneField(OrdGoodsBackUp, verbose_name='普通商品信息', null=True, blank=True,
                                          on_delete=models.SET_NULL)
    repl_goods_info = models.OneToOneField(ReplGoodsBackUp, verbose_name='积分换购商品信息', null=True, blank=True,
                                          on_delete=models.SET_NULL)

    class Meta:
        verbose_name = verbose_name_plural = '订单商品信息'

    def __str__(self):
        return self.goods_name

    @classmethod
    def create(cls, order, goods, gtype, start_send_date=None, num=1, discount=1, delivery_method=None, is_pt=False,
               attach=None, share_user_id=None):
        ord_goods = goods.ord_goods
        repl_goods = goods.repl_goods
        ord_goods_info = None
        repl_goods_info = None
        if ord_goods:
            ord_goods_info = OrdGoodsBackUp.objects.create(estimate_time=ord_goods.estimate_time)

        if repl_goods:
            repl_goods_info = ReplGoodsBackUp.objects.create(
                credit=gtype.credit,
                estimate_time=repl_goods.estimate_time
            )

        g_image = getattr(goods.banner.first().image, 'file', '')

        if not delivery_method:
            delivery_method = cls.EXPRESS  # 默认快递配送
        kwargs = {'order': order,
                  'goods': goods,
                  'gtype_id': gtype.id,
                  'goods_name': goods.name,
                  'g_image': getattr(g_image, 'name', ''),
                  'gtype_name': gtype.content,
                  'num': num,
                  'attach': attach,
                  'delivery_method': delivery_method,
                  'share_user_id': share_user_id if order.user.id != share_user_id else None,
                  'ord_goods_info': ord_goods_info,
                  'repl_goods_info': repl_goods_info,
                  }
        if goods.model_type == goods.ORD:
            # 拼团不参与返利和会员折扣
            kwargs.update({'g_rebate': gtype.rebate if not is_pt else 0, 'g_bonus': gtype.bonus if not is_pt else 0})

        if goods.model_type == goods.REPLACE:
            kwargs.update({'price': gtype.price})
        else:
            kwargs.update({
                'price': (gtype.price * discount).quantize(Decimal('0.00')) if not is_pt else Decimal(
                    gtype.ladder_[0].get('price')).quantize(Decimal('0.00')),
                'original_price': gtype.price,
                'market_price': gtype.market_price,
            })
        instance = cls.objects.create(**kwargs)
        gtype_sell(gtype, num)
        validate_can_sell(goods)
        return instance


class Orders(models.Model):
    PAYING = "paying"
    CLOSE = "close"
    DONE = "done"
    RECEIVING = "receiving"
    HAS_PAID = "has paid"
    SERVING = "serving"
    GROUPBUY = 'groupbuy'

    STATUS = (
        (PAYING, "待付款"),
        (HAS_PAID, "待发货"),
        (RECEIVING, "待收货"),
        (SERVING, "服务中"),
        (DONE, "交易成功"),
        (CLOSE, "交易关闭"),
        (GROUPBUY, "拼团中"),
    )

    ORD = 'ord'
    REPL = 'repl'

    MODEL_TYPE = ((ORD, '普通订单'), (REPL, '积分换购订单'))

    user = models.ForeignKey('wxapp.WxUser', verbose_name="微信用户", null=True, related_name='orders',
                             on_delete=models.SET_NULL)
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', blank=True, null=True, related_name='orders',
                             on_delete=models.SET_NULL)
    order_sn = models.CharField(max_length=30, null=True, blank=True, unique=True, verbose_name="订单号")
    trade_no = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="微信交易号")

    remark = models.TextField(verbose_name="备注", null=True, blank=True)
    status = models.CharField(verbose_name="订单状态", choices=STATUS, default=PAYING, db_index=True, max_length=30)
    model_type = models.CharField(verbose_name='订单类型', max_length=128, choices=MODEL_TYPE, default=ORD)

    order_amount = models.DecimalField(default=0.0, verbose_name="订单金额", max_digits=15, decimal_places=2)
    postage_total = models.DecimalField(default=0.0, max_digits=15, decimal_places=2, verbose_name='总邮费')
    real_amount = models.DecimalField(verbose_name="实付金额", null=True, blank=True, max_digits=15, decimal_places=2)
    asset_pay = models.DecimalField(verbose_name="使用收益支付的金额", max_digits=15, decimal_places=2, default=0)
    recharge_pay = models.DecimalField(verbose_name="使用充值支付的金额", max_digits=15, decimal_places=2, default=0)
    credit = models.PositiveIntegerField(verbose_name='使用积分', default=0)
    discount = models.DecimalField(verbose_name='折扣', max_digits=15, decimal_places=2, default=1)
    pay_time = models.DateTimeField(null=True, blank=True, verbose_name="支付时间")
    flag_time = models.DateTimeField(verbose_name='时间标志', db_index=True, null=True, blank=True)  # 时间标志，用于自动取消订单
    next_send = models.DateTimeField(verbose_name='下次配送时间', null=True, blank=True)
    invoice = models.OneToOneField(Invoice, verbose_name='发票信息', null=True, on_delete=models.SET_NULL)
    delivery_address = models.OneToOneField(DeliveryAddress, verbose_name='配送地址信息', null=True,
                                            on_delete=models.SET_NULL)
    send_time = models.DateTimeField(null=True, blank=True, verbose_name="发货时间")
    receive_time = models.DateTimeField(null=True, blank=True, verbose_name="收货时间")
    add_time = models.DateTimeField(verbose_name='订单创建时间', auto_now_add=True)

    is_pt = models.BooleanField(verbose_name='拼团订单', default=False)
    fictitious = models.BooleanField(verbose_name='虚拟商品订单', default=False, blank=True)

    machine_code = models.CharField(verbose_name='支付终端号', max_length=20, blank=True, null=True)
    entrust_shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', related_name='entrusted_orders',
                                     blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = verbose_name_plural = '订单'
        ordering = ('-add_time',)

    def __str__(self):
        return self.order_sn

    @classmethod
    def all_order_by_status(cls):
        return cls.objects.filter(is_pt=False).extra(
            select={'has_paid': "status='has paid'",
                    'paying': "status='paying'",
                    'receiving': "status='receiving'",
                    'done': "status='done'",
                    'close':  "status='close'",}
        ).order_by('-has_paid', '-paying', '-receiving',  '-done', '-close', '-add_time')

    @classmethod
    def create(cls, user, shop, remark, model_type, discount, invoice, delivery_address, is_pt=False, fictitious=False,
               machine_code=None, credit=0):
        kwargs = locals()
        kwargs.pop('cls', None)

        if is_pt:
            flag_time = timezone.now() + timezone.timedelta(minutes=3)
        else:
            flag_time = timezone.now() + timezone.timedelta(minutes=30)

        entrust_shop = shop.entrust if shop.entrust else None

        kwargs.update({'order_sn': generate_order_sn(user),
                       'flag_time': flag_time,
                       'entrust_shop': entrust_shop})
        instance = cls(**kwargs)
        instance.save()
        return instance


class BuyerCode(models.Model):
    buyer_no = models.CharField(verbose_name='自提号', max_length=10)
    buyer_code = models.CharField(verbose_name='自提码', max_length=10)
    item = models.OneToOneField(Items, verbose_name='所属子订单', related_name='delivery_code', on_delete=models.CASCADE)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '自提码'

    @classmethod
    def create(cls, item):
        num = Items.objects.filter(send_time__date=timezone.now().date()).count()
        buyer_no = f'{num + 1:0>4}'
        buyer_code = Random().randint(1000, 9999)
        cls.objects.create(buyer_no=buyer_no, buyer_code=str(buyer_code), item=item)


class ExportDelivery(models.Model):
    order = models.OneToOneField(
        Orders,
        verbose_name='所属订单',
        related_name='export_delivery',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    export_count = models.IntegerField('导出次数')

    class Meta:
        verbose_name = verbose_name_plural = '订单导出记录'
