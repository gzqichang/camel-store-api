from rest_framework import serializers

from qcache.contrib.drf import version_based_cache

from . import models


class TagSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Tag
        fields = ['label', 'url', 'id']

@version_based_cache
class PeopleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.People
        fields = ['name', 'url', 'id']

@version_based_cache
class GoodsSerializer(serializers.HyperlinkedModelSerializer):
    tags = TagSerializer(many=True)
    maker = PeopleSerializer()

    class Meta:
        model = models.Goods
        fields = ['name', 'price', 'maker', 'tags', 'url', 'id']
