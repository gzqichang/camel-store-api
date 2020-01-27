from django.db.models.functions import Concat
from django_filters import rest_framework as filters
from .models import Shop


class ShopFilter(filters.FilterSet):

    address = filters.CharFilter(label='门店地址', method='address_filter')

    def address_filter(self, queryset, name, value):
        return queryset.annotate(_addr=Concat('province', 'city', 'district', 'detail')).filter(_addr__contains=value)

    class Meta:
        model = Shop
        fields = {
            'name': ['contains'],
            'address': [],
            'status': ['exact'],
        }