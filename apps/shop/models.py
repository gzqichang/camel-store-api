import json
import os
from urllib.parse import urljoin
from django.conf import settings
from wxapp.https import wxapp_client
from django.db import models
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from qcache.models import VersionedMixin

from apps.utils.lbs import lbs
# Create your models here.


class Shop(VersionedMixin, models.Model):
    OPEN = 'open'
    CLOSE = 'close'

    STATUS = ((OPEN, '营业中'), (CLOSE, '休息中'))

    UNLIMIT = 'unlimit'
    RADIUS = 'radius'
    GEOMETRY = 'geometry'

    name = models.CharField(verbose_name='店铺名', max_length=128, unique=True)
    province = models.CharField(verbose_name='省/直辖市', max_length=128)
    city = models.CharField(verbose_name='市', max_length=128)
    district = models.CharField(verbose_name='区', max_length=128)
    detail = models.CharField(verbose_name='详细信息', max_length=128)
    lat = models.FloatField(verbose_name='纬度', null=True, blank=True)
    lng = models.FloatField(verbose_name='经度', null=True, blank=True)
    delivery_divide = models.CharField(verbose_name='配送范围划分方式', max_length=20, default=UNLIMIT,
                            choices=((UNLIMIT, '不限制'), (RADIUS, '半径划分'), (GEOMETRY, '地图标注')))
    delivery_radius = models.PositiveIntegerField(verbose_name='配送半径', null=True, blank=True)
    delivery_range = JSONField(verbose_name='配送范围列表', null=True, blank=True)
    service_phone = models.CharField(verbose_name='客服电话', max_length=20, null=True, blank=True)
    entrust = models.ForeignKey('self', verbose_name='委托店铺', null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(verbose_name='门店状态', choices=STATUS, max_length=128, default=OPEN)


    class Meta:
        verbose_name = verbose_name_plural = '店铺'
        permissions = (
            ('view_all_shop', '查看所有的店铺'),
        )

    def __str__(self):
        return self.name

    @property
    def address(self):
        return self.province + self.city + self.district + self.detail

    # 判断点是否在多边形中
    @staticmethod
    def isPoiWithinPoly(poi, poly):
        # 输入：点，多边形顶点数组
        if not poly:
            return False

        def isRayIntersectsSegment(poi, s_poi, e_poi):  # [x,y] [lng,lat]
            # 输入：判断点，边起点，边终点，都是[lng,lat]格式数组
            if s_poi[1] == e_poi[1]:  # 排除与射线平行、重合，线段首尾端点重合的情况
                return False
            if s_poi[1] > poi[1] and e_poi[1] > poi[1]:  # 线段在射线上边
                return False
            if s_poi[1] < poi[1] and e_poi[1] < poi[1]:  # 线段在射线下边
                return False
            if s_poi[1] == poi[1] and e_poi[1] > poi[1]:  # 交点为下端点，对应spoint
                return False
            if e_poi[1] == poi[1] and s_poi[1] > poi[1]:  # 交点为下端点，对应epoint
                return False
            if s_poi[0] < poi[0] and e_poi[1] < poi[1]:  # 线段在射线左边
                return False

            xseg = e_poi[0] - (e_poi[0] - s_poi[0]) * (e_poi[1] - poi[1]) / (e_poi[1] - s_poi[1])  # 求交
            if xseg < poi[0]:  # 交点在射线起点的左侧
                return False
            return True  # 排除上述情况之后

        sinsc = 0  # 交点个数
        poly.append(poly[0])     #将第一个点再添加到最后，始最后一个坐标和第一个坐标可以构成一个线段
        for i in range(len(poly) - 1):  # [0,len-1]
            s_poi = poly[i]
            e_poi = poly[i + 1]
            if isRayIntersectsSegment(poi, s_poi, e_poi):
                sinsc += 1  # 有交点就加1
        return True if sinsc % 2 == 1 else False

    def is_range(self, point):
        if self.delivery_divide == self.UNLIMIT:
            return True
        if self.delivery_divide == self.RADIUS and self.delivery_radius:
            try:
                from_location = {'lng': float(point.get('lng')),
                         'lat': float(point.get('lat'))}
                distance = lbs.one_to_one_distance(from_location, {'lat': self.lat, 'lng': self.lng})
            except AttributeError:
                return False
            if distance * 1000 < self.delivery_radius:
                return True
        if self.delivery_divide == self.GEOMETRY and self.delivery_range:
            poly = []
            try:
                point = [float(point.get('lng')), float(point.get('lat'))]
                for i in self.delivery_range:
                    poly.append([i.get('lng'), i.get('lat')])
            except AttributeError:
                return False
            return self.isPoiWithinPoly(point, poly)
        return False

    @classmethod
    def get_all_shop_location(cls, shops):
        locations = []
        for shop in shops:
            locations.append(str(shop.lat)+','+str(shop.lng))
        return locations

    @classmethod
    def get_shop_list(cls, from_location=None):
        '''根据坐标返回正在营业的店铺信息(如果有from_location,则加上距离）
        :param from_locations: {'lat': 123, ; 'lng': 123}
        '''
        shops_has_location = []
        shop_info_list = []
        shops = cls.objects.filter(status=cls.OPEN)
        for shop in shops:
            if shop.lat and shop.lng:
                shops_has_location.append(shop)
                continue
            shop_info_list.append(
                {'name': shop.name, 'id': shop.id, 'distance': None, 'address': shop.address})

        if from_location:
            to_location = cls.get_all_shop_location(shops_has_location)
            from_location = "{},{}".format(from_location.get('lat'), from_location.get('lng'))
            distance_list = lbs.one_to_many_distance(from_location=from_location, to_location=to_location)
            for i in distance_list:
                shop = shops_has_location[i.get('index')]
                shop_info_list.append(
                    {'name': shop.name, 'id': shop.id, 'distance': i.get('distance'), 'address': shop.address})
        else:
            for shop in shops_has_location:
                shop_info_list.append(
                    {'name': shop.name, 'id': shop.id, 'distance': None, 'address': shop.address})
                    
        return shop_info_list

    @classmethod
    def get_near_shop(cls, from_location, address, shops=None):
        # 根据坐标返回距离最近的店
        '''
        :param from_locations: {'lat': 123, ; 'lng': 123}
        :param address: '北京市北京市东城区'  (省市区)
        :return:
        '''
        shops = shops if shops else cls.objects.filter(lat__isnull=False, lng__isnull=False, status=cls.OPEN)
        to_ = cls.get_all_shop_location(shops)
        from_ = "{},{}".format(from_location.get('lat'), from_location.get('lng'))
        distance_list = lbs.one_to_many_distance(from_location=from_, to_location=to_)
        if not distance_list:
            return False
        try:
            distance_list[0].get('index')
        except AttributeError:
            return False
        for i in distance_list:
            shop = shops[i.get('index')]
            # if address in shop.range_list:
            #     return shop
            if shop.is_range(from_location):
                return shop
        return False

    @classmethod
    def get_near_shop_by_address(cls, address):
        '''
        根据用户收货地址查找可配送的最近的店
        :param address: address（__clss__ = apps.trade.models.UserAddress）
        :return:
        '''
        can_send_shops = []
        address_location = address.location
        shops = cls.objects.filter(lat__isnull=False, lng__isnull=False, status=cls.OPEN)
        for shop in shops:
            # if address.get_region in shop.range_list:
            #     can_send_shops.append(shop)
            if shop.is_range(address_location):
                can_send_shops.append(shop)
        return cls.get_near_shop(from_location=address_location, address=address.get_region, shops=can_send_shops)