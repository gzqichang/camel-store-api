from django_filters import rest_framework as filters
from .models import DeliveryAccount, DeliveryPrinter, Sender


class DeliveryAccountFilter(filters.FilterSet):
    class Meta:
        model = DeliveryAccount
        fields = {
            'shop': ['exact'],
            'is_active': ['exact'],
        }


class DeliveryPrinterFilter(filters.FilterSet):
    class Meta:
        model = DeliveryPrinter
        fields = {
            'shop': ['exact'],
        }


class SenderFilter(filters.FilterSet):
    class Meta:
        model = Sender
        fields = {
            'shop': ['exact'],
            'is_active': ['exact'],
        }
