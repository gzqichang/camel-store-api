import django_filters
from django_filters import rest_framework as filters
from .models import FeedBack


class FeedbackFilter(filters.FilterSet):

    nickname = filters.CharFilter(field_name='user__nickname', lookup_expr='icontains')
    phone = filters.CharFilter(field_name='phone', lookup_expr='icontains')
    content = filters.CharFilter(field_name='content', lookup_expr='icontains')

    add_time = filters.DateFromToRangeFilter(field_name='add_time')

    class Meta:
        model = FeedBack
        fields = {
            'nickname': [],
            'phone': [],
            'content': [],
            'shop': ['exact'],
            'solve': ['exact'],
            'add_time': [],
        }