from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from qcache.models import VersionedMixin

from apps.utils.disable_for_loaddata import disable_for_loaddata

# Create your models here.


class HomeBanner(VersionedMixin, models.Model):

    JUMP_TYPE = (('goods', '商品详情'), ('goods_type', '商品类型'), ('category', '商品分类'))

    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', blank=True, null=True, on_delete=models.CASCADE)
    image = models.ForeignKey('qfile.File', verbose_name='轮播图', null=True, on_delete=models.SET_NULL)
    jump_type = models.CharField(verbose_name='跳转类型', max_length=128, choices=JUMP_TYPE, null=False)
    goods = models.ForeignKey('goods.Goods', verbose_name='跳转商品', null=True, blank=True, on_delete=models.CASCADE)
    goods_type = models.CharField(verbose_name='商品类型', max_length=128, null=True, blank=True)
    category = models.ForeignKey('goods.GoodsCategory', verbose_name='跳转分类', null=True, blank=True, on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField(verbose_name='排序', default=0)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '首页轮播图'
        ordering = ('index', )

    def __str__(self):
        return '首页轮播图'


class Shortcut(VersionedMixin, models.Model):
    JUMP_TYPE = (('goods_type', '商品类型'), ('category', '商品分类'))

    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', blank=True, null=True, on_delete=models.CASCADE)
    image = models.ForeignKey('qfile.File', verbose_name='快速入口图标', null=True, on_delete=models.SET_NULL)
    label = models.CharField(verbose_name='快速入口名称', max_length=128, null=False)
    jump_type = models.CharField(verbose_name='跳转类型', max_length=128, choices=JUMP_TYPE, null=False)
    goods_type = models.CharField(verbose_name='商品类型', max_length=128, null=True, blank=True)
    category = models.ForeignKey('goods.GoodsCategory', verbose_name='跳转分类', null=True, blank=True, on_delete=models.CASCADE)
    index = models.PositiveSmallIntegerField(verbose_name='排序', default=0)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '快捷入口'
        ordering = ('index', )

    def __str__(self):
        return self.label


class Module(VersionedMixin, models.Model):

    shop = models.ForeignKey('shop.Shop', verbose_name='所属店铺', blank=True, null=True, on_delete=models.CASCADE)
    label = models.CharField(verbose_name='模块名称', max_length=128, null=False)
    module = models.CharField(verbose_name='模块', max_length=128, null=False)
    active = models.BooleanField(verbose_name='是否启用', default=True)
    index = models.PositiveSmallIntegerField(verbose_name='排序', default=0)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '首页模块'
        ordering = ('index', )


@receiver(post_save, sender='shop.Shop')      #创建新店铺同时创建新店的首页模块设置
@disable_for_loaddata
def shop_save(sender, **kwargs):
    instance = kwargs.get('instance')
    created = kwargs.get('created')
    if created:
        Module.objects.get_or_create(shop=instance, label='拼团商品推荐', module='grouping',
                                     defaults={'active': True, 'index': 0})
        Module.objects.get_or_create(shop=instance, label='周期购商品推荐', module='periodic',
                                     defaults={'active': True, 'index': 1})
        Module.objects.get_or_create(shop=instance, label='热门商品推荐', module='recommendation',
                                     defaults={'active': True, 'index': 2})
        Module.objects.get_or_create(shop=instance, label='积分商品推荐', module='credit',
                                     defaults={'active': True, 'index': 3})
