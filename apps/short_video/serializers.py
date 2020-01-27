import json
from rest_framework import serializers
from rest_framework.serializers import PrimaryKeyRelatedField
from rest_framework.reverse import reverse
from qcache.contrib.drf import version_based_cache

from apps.goods.models import Goods
from apps.goods.serializers import GoodsListNewSerializer, ImagesSerializer
from .models import ShortVideo, BlockWxUser

@version_based_cache
class UploadVideoSerializer(serializers.ModelSerializer):

    goods = serializers.CharField(label='商品ID列表', required=False, allow_null=True, write_only=True)

    class Meta:
        model = ShortVideo
        fields = ('user', 'title', 'video', 'goods')
        extra_kwargs = {
            'user': {'read_only': True},

        }
    def validate(self, attrs):
        goods = attrs.get('goods', None)
        if goods:
            goods_ = PrimaryKeyRelatedField(label='短视频推荐商品', many=True,
                                            queryset=Goods.objects.all())
            goods = goods_.to_internal_value(json.loads(goods))
        else:
            goods = []
        if len(goods) > 5:
            raise serializers.ValidationError('最多选五件商品')
        attrs['goods'] = goods
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user
        validated_data['user'] = user
        video = validated_data['video']
        validated_data['size'] = int(video.size / 1024 / 1024)
        return super().create(validated_data)

@version_based_cache
class ShortVideoSerializer(serializers.ModelSerializer):

    user_info = serializers.SerializerMethodField()
    goods = serializers.SerializerMethodField()

    class Meta:
        model = ShortVideo
        fields = ('id', 'user', 'user_info', 'title', 'browse', 'video', 'is_open', 'size', 'goods', 'create_time')
        extra_kwargs = {
            'user': {'read_only': True},
            'browse': {'read_only': True},
            'video': {'read_only': True},
            'size': {'read_only': True},
            'goods': {'read_only': True},
            'create_time': {'read_only': True},
        }

    def get_user_info(self, instance):
        res = {
            'id': instance.user.id,
            'nickname': instance.user.nickname,
            'avatar_url': instance.user.avatar_url,
        }
        return res

    def get_goods(self, instance):
        request = self.context.get('request')
        if getattr(request.user, 'is_staff', False):
            return None
        goods_info = []
        for goods in instance.goods.all():
            price_range = getattr(goods, f'{goods.model_type}_goods').price_range
            info = {
                'url': reverse('goods-detail', (goods.id, ), request=self.context.get('request')),
                'id': goods.id,
                'name': goods.name,
                'goods_brief': goods.goods_brief,
                'status': Goods.status_dict.get(goods.status),
                'model_type': goods.model_type,
                'price_range': price_range,
                'banner': ImagesSerializer(instance=goods.banner.first(), context=self.context).data
            }
            goods_info.append(info)
        return goods_info
