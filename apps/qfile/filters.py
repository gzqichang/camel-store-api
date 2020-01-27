from django_filters import rest_framework as filters
from .models import File


class FileFilter(filters.FilterSet):

    class Meta:
        model = File
        fields = {
            'file_type': ['exact'],
            'tag': ['exact'],
        }
