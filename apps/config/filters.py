from django_filters import rest_framework as filters
from .models import Notice


class NoticeFilter(filters.FilterSet):
    title = filters.CharFilter(field_name='title', lookup_expr='contains')
    create_time = filters.DateFromToRangeFilter(field_name='create_time')

    class Meta:
        model = Notice
        fields = {
            'title': [],
            'create_time': [],
            'is_active': ['exact'],
        }