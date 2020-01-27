from rest_framework import serializers
from qapi.utils import generate_fields
from qcache.contrib.drf import version_based_cache

from apps.utils.object_related_field import ObjectHyperlinkedRelatedField as obj
from apps.qfile.models import File
from apps.qfile.serializers import FileSerializer
from apps.goods.serializers import GoodsCategorySerializer
from apps.goods.models import GoodsCategory

from .models import HomeBanner, Shortcut, Module

@version_based_cache
class HomeBannerSerializers(serializers.HyperlinkedModelSerializer):
    image = obj(allow_null=True, label='类别图', queryset=File.objects.all(), required=False,
                view_name='file-detail', serializer_class=FileSerializer)
    category = obj(allow_null=True, label='跳转分类', queryset=GoodsCategory.objects.all(), required=False,
                   view_name='goodscategory-detail', serializer_class=GoodsCategorySerializer)
    goods_info = serializers.SerializerMethodField()

    class Meta:
        model = HomeBanner
        fields = generate_fields(HomeBanner, add=['goods_info'], remove=['add_time'])

    def get_goods_info(self, instance):
        if instance.goods:
            return {"goods_name": instance.goods.name}
        return None


@version_based_cache
class ShortcutSerializers(serializers.HyperlinkedModelSerializer):
    image = obj(allow_null=True, label='类别图', queryset=File.objects.all(), required=False,
                view_name='file-detail', serializer_class=FileSerializer)
    category = obj(allow_null=True, label='跳转分类', queryset=GoodsCategory.objects.all(), required=False,
                   view_name='goodscategory-detail', serializer_class=GoodsCategorySerializer)

    class Meta:
        model = Shortcut
        fields = generate_fields(Shortcut, remove=['add_time'])


@version_based_cache
class ModuleSerializers(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Module
        fields = generate_fields(Module, remove=['add_time'])
        extra_kwargs = {
            'label': {'read_only': True},
            'module': {'read_only': True},
            'shop': {'read_only': True},
        }
