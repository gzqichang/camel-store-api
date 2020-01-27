from django_filters import rest_framework as filters
from .models import PtGroup


class PtGroupFilter(filters.FilterSet):
    user = filters.CharFilter(field_name='user__nickname', lookup_expr='icontains')
    ptgroup_no = filters.CharFilter(field_name='ptgroup_no', lookup_expr='icontains')
    partake = filters.CharFilter(field_name='partake__nickname', lookup_expr='icontains')
    add_time = filters.DateFromToRangeFilter(field_name='add_time')
    goods_name = filters.CharFilter(field_name='goods_name', lookup_expr='icontains')

    class Meta:
        model = PtGroup
        fields = {
            'user': [],
            'ptgroup_no': [],
            'ptgoods': ['exact'],
            'goods_name': [],
            'status': ['exact'],
            'add_time': [],
            'partake': [],
            'shop': ['exact'],
        }