from django_filters import rest_framework as filters
from django.db.models import Q
from .models import UserAddress, Orders, Items


class AddressFilter(filters.FilterSet):
    class Meta:
        model = UserAddress
        fields = {
            'is_default': ['exact'],
        }


class OrdersFilter(filters.FilterSet):
    order_sn = filters.CharFilter(field_name='order_sn', lookup_expr='contains')
    user = filters.CharFilter(field_name='user__nickname', lookup_expr='contains')
    user_id = filters.NumberFilter(label='用户id', field_name='user__id', lookup_expr='exact')
    add_time = filters.DateFromToRangeFilter(field_name='add_time')
    pay_time = filters.DateFromToRangeFilter(field_name='pay_time')
    next_send = filters.DateFromToRangeFilter(field_name='next_send')

    shop = filters.NumberFilter(label='所属店铺', method='shop__filter')
    goods_name = filters.CharFilter(label='商品名称', method='goods_name_filter')
    gtype_name = filters.CharFilter(label='规格名称', method='gtype_name_filter')

    def goods_name_filter(self, queryset, name, value):
        return queryset.filter(goods_backup__goods_name__icontains=value).distinct()

    def gtype_name_filter(self, queryset, name, value):
        return queryset.filter(goods_backup__gtype_name__icontains=value).distinct()



    def shop__filter(self, queryset, name, value):
        return queryset.filter(Q(shop__id=value)|Q(entrust_shop__id=value))

    class Meta:
        model = Orders
        fields = {
            'order_sn': [],
            'user': [],
            'user_id': ['exact'],
            'add_time': [],
            'pay_time': [],
            'status': ['exact'],
            'goods_name': [],
            'gtype_name': [],
            'shop': ['exact'],
            'model_type': ['exact'],
            'next_send': [],
        }


class ItemsFilter(filters.FilterSet):
    order_sn = filters.CharFilter(label='订单号', field_name='order__order_sn', lookup_expr='contains')
    user = filters.CharFilter(label='用户', field_name='order__user__nickname', lookup_expr='contains')
    goods_name = filters.CharFilter(label='商品名', field_name='goods_backup__goods_name', lookup_expr='contains')
    gtype_name = filters.CharFilter(label='规格名', field_name='goods_backup__gtype_name', lookup_expr='contains')
    add_time = filters.DateFromToRangeFilter(label='创建时间', field_name='order__add_time')
    order__shop = filters.NumberFilter(label='所属店铺', method='order_shop__filter')

    def order_shop__filter(self, queryset, name, value):
        return queryset.filter(Q(order__shop__id=value)|Q(order__entrust_shop__id=value))

    class Meta:
        model = Items
        fields = {
            'order_sn': [],
            'user': [],
            'send_type': ['exact'],
            'order__shop': ['exact'],
            'order__model_type': ['exact'],
            'goods_name': [],
            'gtype_name': [],
            'add_time': [],
        }