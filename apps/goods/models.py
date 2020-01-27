import simplejson as json
from django.utils import timezone
from django.db import models
from django.db.models import Min
from django.db.models.signals import post_save, pre_save, post_init
from django.dispatch import receiver
from django.contrib.postgres.fields import JSONField, ArrayField

from qcache.models import VersionedMixin

from .utils import format_date


# Create your models here.


class GoodsCategory(VersionedMixin, models.Model):
    name = models.CharField(default='', max_length=30, verbose_name='类别名', help_text='类别名')
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', blank=True, null=True, on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField(verbose_name='优先级', default=0)
    is_active = models.BooleanField(verbose_name='是否启用', default=True)

    class Meta:
        verbose_name = verbose_name_plural = '商品类别'
        ordering = ('-is_active', 'index')

    def __str__(self):
        return self.name


class Images(VersionedMixin, models.Model):
    image = models.ForeignKey('qfile.File', verbose_name='图片', blank=True, null=True,
                              on_delete=models.SET_NULL)
    index = models.PositiveSmallIntegerField(verbose_name='顺序', default=0)

    class Meta:
        verbose_name = verbose_name_plural = '商品图片'
        ordering = ('index',)

    def __str__(self):
        if self.image:
            return self.image.get_file_url
        return ''


class Goods(VersionedMixin, models.Model):
    IS_SELL = 0
    PREVIEW = 1
    NOT_ENOUGH = 2
    NOT_SELL = 3

    STATUS = ((IS_SELL, '在售'), (PREVIEW, '预览'), (NOT_ENOUGH, '库存不足'), (NOT_SELL, '下架'))

    status_dict = {IS_SELL: 'is_sell', PREVIEW: 'preview', NOT_ENOUGH: 'not_enough', NOT_SELL: 'not_sell'}

    OWN = 'own'
    EXPRESS = 'express'
    BUYER = 'buyer'
    METHOD = ((OWN, '商家自配送'), (EXPRESS, '快递配送'), (BUYER, '用户自提'))

    FREE = 'free'
    DISTANCE = 'distance'
    POSTAGE = ((FREE, '免邮'), (DISTANCE, '按距离计算'))

    ORD = 'ord'
    REPLACE = 'replace'

    MODEL_TYPE = ((ORD, '普通商品'), (REPLACE, '积分换购'))

    name = models.CharField(max_length=100, verbose_name='商品名', help_text='商品名')
    category = models.ForeignKey(GoodsCategory, verbose_name='商品类别', null=True, on_delete=models.SET_NULL)
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', blank=True, null=True, on_delete=models.SET_NULL)
    goods_brief = models.TextField(max_length=256, verbose_name='商品简短描述')
    image = models.ForeignKey('qfile.File', verbose_name='封面图', null=True, related_name='image',
                              on_delete=models.SET_NULL)
    video = models.ForeignKey('qfile.File', verbose_name='介绍视频', null=True, related_name='video',
                              on_delete=models.SET_NULL)
    poster = models.ForeignKey('qfile.File', verbose_name='海报模板', null=True, related_name='poster',
                               on_delete=models.SET_NULL, )
    status = models.IntegerField('商品状态', choices=STATUS, default=0)
    index = models.IntegerField('优先级', default=0)
    is_template = models.BooleanField('是否是模板', default=False)

    model_type = models.CharField(verbose_name='商品类型', max_length=128, choices=MODEL_TYPE, default=ORD)

    banner = models.ManyToManyField(Images, verbose_name='详情页轮播图', related_name='banners_goods')
    detail = models.ManyToManyField(Images, verbose_name='商品详情图', related_name='details_goods')
    ord_goods = models.OneToOneField('goods.OrdGoods', verbose_name='普通商品', null=True, blank=True,
                                     on_delete=models.SET_NULL)
    repl_goods = models.OneToOneField('goods.ReplGoods', verbose_name='积分商品', null=True, blank=True,
                                     on_delete=models.SET_NULL)
    delivery_method = ArrayField(
        base_field=models.CharField(max_length=128, choices=METHOD), default=list, verbose_name='配送方式'
    )
    postage_setup = models.CharField(verbose_name='运费设置', max_length=128, choices=POSTAGE, default=FREE)
    postage = JSONField(verbose_name='运费', null=True, blank=True)
    attach = models.ManyToManyField('goods.Attach', verbose_name='自定义信息', related_name='attach_goods', blank=True)
    add_time = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')

    #活动
    groupbuy = models.BooleanField(verbose_name='是否拼团', default=False)
    groupbuy_info = models.OneToOneField('group_buy.GroupBuyInfo', related_name='groupbuy_goods', null=True, blank=True,
                                         verbose_name='拼团信息', on_delete=models.SET_NULL)
    fictitious = models.BooleanField(verbose_name='虚拟商品', default=False)
    recommendation = models.BooleanField(verbose_name='热门商品', default=False)

    class Meta:
        verbose_name = verbose_name_plural = '商品'
        ordering = ('status', 'index', 'id')

        permissions = (
            ('create_template', "创建商品模板"),
        )

    def __str__(self):
        return self.name

    @property
    def postage_type(self):
        if self.postage_setup == self.DISTANCE and self.postage:
            return sorted(self.postage, key=lambda x: x.get('start', 0))
        return [{}]


class OrdGoods(VersionedMixin, models.Model):
    estimate_time = JSONField(verbose_name='预计时间', null=True, blank=True)
    gtypes = models.ManyToManyField('goods.GoodType', verbose_name='普通商品规格')

    class Meta:
        verbose_name = verbose_name_plural = '普通商品'

    @property
    def price_range(self):
        gtypes = self.gtypes.all()
        if gtypes:
            price = [i[0] for i in gtypes.values_list('price')]
            p_max, p_min = max(price), min(price)
            if p_max == p_min:
                return f'{p_min}'
            return f'{p_min}-{p_max}'
        else:
            return ''

    @property
    def market_price_range(self):
        gtypes = getattr(self, 'gtypes').all()
        if gtypes:
            price = [i[0] for i in gtypes.values_list('market_price')]
            p_max, p_min = max(price), min(price)
            if p_max == p_min:
                return f'{p_min}'
            return f'{p_min}-{p_max}'
        else:
            return ''

    @property
    def max_rebate(self):
        gtypes = getattr(self, 'gtypes').all()
        rebate_list = [i.rebate for i in gtypes]
        if rebate_list:
            return max(rebate_list)
        return 0.0


class ReplGoods(VersionedMixin, models.Model):
    estimate_time = JSONField(verbose_name='预计时间', null=True, blank=True)
    gtypes = models.ManyToManyField('goods.ReplGoodsType', verbose_name='积分商品规格')

    class Meta:
        verbose_name = verbose_name_plural = '积分商品'

    @property
    def price_range(self):
        gtypes = self.gtypes.all()
        if gtypes:
            price = [i[0] for i in gtypes.values_list('price')]
            p_max, p_min = max(price), min(price)
            if p_max == p_min:
                return f'{p_min}'
            return f'{p_min}-{p_max}'
        else:
            return ''



class GoodType(VersionedMixin, models.Model):
    content = models.CharField(max_length=100, verbose_name='规格', help_text='规格')
    market_price = models.DecimalField(default=0, verbose_name="市场价格", max_digits=15, decimal_places=2)
    price = models.DecimalField(verbose_name='价格', max_digits=15, decimal_places=2)
    stock = models.PositiveIntegerField(verbose_name='库存', default=10)
    is_sell = models.BooleanField(verbose_name='是否在售', default=True)
    index = models.PositiveSmallIntegerField(verbose_name='优先级', default=0)
    buy_limit = models.PositiveSmallIntegerField(verbose_name='限购', null=True, blank=True)
    rebate = models.PositiveIntegerField(verbose_name='返利金额', default=0)
    bonus = models.DecimalField(verbose_name='分销金额', max_digits=15, decimal_places=2, default=0)
    change_limit = models.DateTimeField(verbose_name='改变限购时间', default=timezone.now)
    ladder = models.TextField(verbose_name='阶梯', null=True, blank=True)
    icon = models.ForeignKey('qfile.File', verbose_name='图标', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = verbose_name_plural = '商品规格'
        ordering = ('-is_sell', 'index',)

        permissions = (
            ('change_rebate_bonus', "修改返利分销金额"),

        )

    def __str__(self):
        return self.content

    @property
    def ladder_(self):
        if self.ladder:
            ladder = json.loads(self.ladder, use_decimal=True)
            ladder = sorted(ladder, key=lambda x: x.get('index'))
            return ladder
        return []


@receiver(post_init, sender=GoodType)
def goodstype_init(instance, **kwargs):
    instance.origin_limit = instance.buy_limit


@receiver(pre_save, sender=GoodType)
def goodstype_save(instance, **kwargs):
    if instance.origin_limit != instance.buy_limit:
        instance.change_limit = timezone.now()


class ReplGoodsType(VersionedMixin, models.Model):
    content = models.CharField(max_length=100, verbose_name='规格', help_text='规格')
    market_price = models.DecimalField(verbose_name="市场价格", max_digits=15, decimal_places=2, default=0)
    price = models.DecimalField(verbose_name='价格', max_digits=15, decimal_places=2, default=0)
    credit = models.PositiveIntegerField(verbose_name='积分')
    stock = models.PositiveIntegerField(verbose_name='库存', default=10)
    is_sell = models.BooleanField(verbose_name='是否在售', default=True)
    index = models.PositiveSmallIntegerField(verbose_name='优先级', default=0)
    buy_limit = models.PositiveSmallIntegerField(verbose_name='限购', null=True, blank=True)
    change_limit = models.DateTimeField(verbose_name='改变限购时间', default=timezone.now)
    icon = models.ForeignKey('qfile.File', verbose_name='图标', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = verbose_name_plural = '商品规格'
        ordering = ('-is_sell', 'index',)

    def __str__(self):
        return self.content


@receiver(post_init, sender=ReplGoodsType)
def replgoodstype_init(instance, **kwargs):
    instance.origin_limit = instance.buy_limit


@receiver(pre_save, sender=ReplGoodsType)
def replgoodstype_save(instance, **kwargs):
    if instance.origin_limit != instance.buy_limit:
        instance.change_limit = timezone.now()


class Banner(VersionedMixin, models.Model):
    goods = models.ForeignKey(Goods, verbose_name='商品', related_name='home_banner', null=True, on_delete=models.CASCADE)
    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', blank=True, null=True, on_delete=models.CASCADE)
    image = models.ForeignKey('qfile.File', verbose_name='轮播图', blank=True, null=True,
                              on_delete=models.SET_NULL)

    index = models.IntegerField(default=0, verbose_name="轮播顺序")
    is_active = models.BooleanField(verbose_name='是否启用', default=True)

    class Meta:
        ordering = ('index',)
        verbose_name = verbose_name_plural = '首页轮播图片'

    def __str__(self):
        if self.image:
            return self.image.get_file_url
        return ''


class HotWord(VersionedMixin, models.Model):
    word = models.CharField(verbose_name='热搜词', unique=True, max_length=128)
    index = models.PositiveSmallIntegerField(verbose_name='优先级', default=0)

    class Meta:
        verbose_name = verbose_name_plural = '热搜词'
        ordering = ('index',)

    def __str__(self):
        return self.word


class Attach(VersionedMixin, models.Model):
    label = models.CharField(verbose_name='字段名', max_length=128)
    attach_type = models.CharField(verbose_name='类型', max_length=128)
    is_required = models.BooleanField(verbose_name='是否必填', default=False)
    help_text = models.CharField(verbose_name='提示说明', max_length=128, null=True, blank=True)
    index = models.PositiveSmallIntegerField(verbose_name='排序', default=1)
    option = JSONField(verbose_name='选项', null=True)
    length = models.PositiveSmallIntegerField(verbose_name='限定长度', null=True)
    max_value = models.FloatField(verbose_name='最大值', null=True)
    min_value = models.FloatField(verbose_name='最小值', null=True)

    class Meta:
        verbose_name = verbose_name_plural = '商品自定义字段'
        ordering = ('index', )

    def __str__(self):
        return self.label


@receiver(post_save, sender=Goods)
def goods_save(sender, **kwargs):
    instance = kwargs.get('instance')
    if instance.status != Goods.IS_SELL:
        banner = instance.home_banner.all()  # 首页轮播海报
        if banner:
            banner.update(is_active=False)
