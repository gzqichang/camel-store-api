# -*- coding: utf-8 -*-
import django_filters
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import GoodsCategory, Goods, Banner


class GoodsCategoryFilter(filters.FilterSet):

    class Meta:
        model = GoodsCategory
        fields = {
            'shop': ['exact'],
        }


class GoodsFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='contains')
    search = django_filters.CharFilter(label='搜索', method='search_filter')
    date_time = filters.DateFromToRangeFilter(field_name='add_time')
    status = filters.ChoiceFilter(label='商品状态', method='status_filter', choices=(
        ('is_sell', '在售'), ('preview', '预览'), ('not_enough', '库存不足'), ('not_sell', '下架')
    ))

    def search_filter(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value)|Q(category__name__icontains=value)|Q(goods_brief__icontains=value))

    def status_filter(self, queryset, name, value):
        status = list(Goods.status_dict.keys())[list(Goods.status_dict.values()).index(value)]
        return queryset.filter(status=status)

    class Meta:
        model = Goods
        fields = {
            'name': [],
            'category': ['exact'],
            'shop': ['exact'],
            'status': ['exact'],
            'search': ['exact'],
            'date_time': [],
            'is_template': ['exact'],
            'model_type': ['exact'],
            'groupbuy': ['exact'],
            'recommendation': ['exact'],
            'fictitious': ['exact'],
        }


class BannerFilter(filters.FilterSet):

    class Meta:
        model = Banner
        fields = {
            'shop': ['exact'],
        }
