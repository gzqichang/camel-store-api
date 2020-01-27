import json
from django.conf import settings
from rest_framework import serializers
from qcache.contrib.drf import version_based_cache

from qapi.utils import generate_fields, generate_full_uri

from .models import Shop


@version_based_cache
@version_based_cache
class Coordinates(serializers.Serializer):
    lat = serializers.FloatField(label='纬度')
    lng = serializers.FloatField(label='经度')


@version_based_cache
class ShopSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Shop
        fields = generate_fields(Shop, add=['admin'], remove=[])
        extra_kwargs = {
            'admin': {'required': False}
        }

    def validate_entrust(self, value):
        if value:
            if value.status == Shop.CLOSE:
                raise serializers.ValidationError('被委托的店铺正在休息中，无法委托。')
            if value.entrust:
                raise serializers.ValidationError(f'门店{value.name}不能被选为委托店铺。')
        return value

