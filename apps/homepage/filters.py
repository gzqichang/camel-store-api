from django_filters import rest_framework as filters
from .models import HomeBanner, Shortcut, Module


class HomeBannerFilter(filters.FilterSet):

    class Meta:
        model = HomeBanner
        fields = {
            'shop': ['exact'],
        }


class ShortcutFilter(filters.FilterSet):

    class Meta:
        model = Shortcut
        fields = {
            'shop': ['exact'],
        }


class ModuleFilter(filters.FilterSet):

    class Meta:
        model = Module
        fields = {
            'shop': ['exact'],
        }

