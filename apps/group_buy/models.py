import time
from random import Random
import simplejson as json
from django.utils import timezone
from django.db import models
from qcache.models import VersionedMixin
# Create your models here.


def generate_ptgroup_sn(user):
    random_ins = Random()
    return f'PT{time.strftime("%m%d%H%M%S")}{user.id%1000:0>4}{random_ins.randint(10, 99)}'


class GroupBuyInfo(VersionedMixin, models.Model):
    PEOPLE = 'people'     # 按参团人数算
    GOODS = 'goods'        # 按购买数量算
    MODE = ((PEOPLE, '参团人数'), (GOODS, '购买数量'))

    period = models.PositiveSmallIntegerField(verbose_name='拼团倒计时')
    integral = models.PositiveSmallIntegerField(verbose_name='奖励积分', default=0)
    mode = models.CharField(max_length=30, choices=MODE, verbose_name='成团方式')
    ladder = models.TextField(verbose_name='拼团阶梯', null=False)

    class Meta:
        verbose_name = verbose_name_plural = '商品拼团信息'

    @property
    def ladder_(self):
        ladder = json.loads(self.ladder)
        ladder = sorted(ladder, key=lambda x: x.get('index'))
        return ladder


class PtGroup(VersionedMixin, models.Model):
    PEOPLE = 'people'     # 按参团人数算
    GOODS = 'goods'        # 按购买数量算
    MODE = ((PEOPLE, '参团人数'), (GOODS, '购买数量'))

    BUILD = 'build'    # 拼团中
    DONE = 'done'      # 已成团
    FAIL = 'fail'      # 已取消
    STATUS = ((BUILD, '拼团中'), (DONE, '已成团'), (FAIL, '已取消'))

    ptgroup_no = models.CharField(max_length=30, null=True, blank=True, unique=True, verbose_name="拼团号")
    ptgoods = models.ForeignKey('goods.Goods', verbose_name='拼团商品', related_name='team_goods', null=True, blank=True,
                              on_delete=models.SET_NULL)
    goods_name = models.CharField(max_length=128, verbose_name='商品名称', null=True)
    shop = models.ForeignKey('shop.Shop', verbose_name='所属商店', related_name='shop_pt',  null=True, blank=True,
                             on_delete=models.SET_NULL)
    user = models.ForeignKey('wxapp.WxUser', verbose_name='拼团发起人', related_name='teams', null=True, blank=True,
                             on_delete=models.SET_NULL)
    partake = models.ManyToManyField('wxapp.WxUser', related_name='partake_team', verbose_name='参团人')
    mode = models.CharField(max_length=30, choices=MODE, verbose_name='成团方式')
    status = models.CharField(max_length=30, choices=STATUS, verbose_name='拼团状态', default=BUILD)
    robot = models.PositiveSmallIntegerField(verbose_name='后台添加的机器人', default=0)
    robot_goods = models.PositiveSmallIntegerField(verbose_name='后台添加的机器人购买数量', default=0)
    add_time = models.DateTimeField(verbose_name='拼团发起时间', auto_now_add=True)
    end_time = models.DateTimeField(verbose_name='拼团结束时间')

    order = models.ManyToManyField('trade.Orders', related_name='pt_group', verbose_name='拼团的订单')

    class Meta:
        verbose_name = verbose_name_plural = '拼团'

    def __str__(self):
        return f"拼团号:{self.ptgroup_no}"

    @classmethod
    def create(cls, user, ptgoods, shop):
        kwargs = locals()
        kwargs.pop('cls', None)
        kwargs.update({'ptgroup_no': generate_ptgroup_sn(user),
                       'goods_name': ptgoods.name,
                       'mode': ptgoods.groupbuy_info.mode,
                       'end_time': timezone.now() + timezone.timedelta(hours=ptgoods.groupbuy_info.period)})
        instance = cls(**kwargs)
        instance.save()
        return instance
