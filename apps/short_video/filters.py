from django_filters import rest_framework as filters
from .models import ShortVideo


class ShortVideoFilter(filters.FilterSet):
    title = filters.CharFilter(field_name='title', lookup_expr='icontains')
    nickname = filters.CharFilter(field_name='user__nickname', lookup_expr='icontains')
    create_time = filters.DateFromToRangeFilter(field_name='create_time')

    class Meta:
        model = ShortVideo
        fields = {
            'title': ['exact'],
            'nickname': ['exact'],
            'create_time': []
        }
