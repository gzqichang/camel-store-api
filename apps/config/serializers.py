import os
from django.conf import settings
from rest_framework import serializers

from qcache.contrib.drf import version_based_cache

from apps.qfile.models import File
from apps.qfile.serializers import FileSerializer
from qapi.utils import generate_fields
from apps.utils.object_related_field import ObjectHyperlinkedRelatedField as obj
from .models import FaqContent, Marketing, Notice, Level, RechargeType, StoreLogo, WeChatConfig

@version_based_cache
class FaqContentSerializers(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = FaqContent
        fields = generate_fields(FaqContent)


@version_based_cache
class MarketingSerializers(serializers.Serializer):
    rebate = serializers.DecimalField(label='推广返利门槛', max_digits=None, decimal_places=2, min_value=0,
                                      required=True, initial=0)
    bonus = serializers.DecimalField(label='分销返佣门槛', max_digits=None, decimal_places=2, min_value=0,
                                      required=True, initial=0)

    def save(self, **kwargs):
        rebate = str(self.validated_data.get('rebate'))
        bonus = str(self.validated_data.get('bonus'))
        Marketing.objects.update_or_create(name='rebate', defaults={'content': rebate})
        Marketing.objects.update_or_create(name='bonus', defaults={'content': bonus})
        return {'rebate': rebate, 'bonus': bonus}


@version_based_cache
class NoticeSerializers(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Notice
        fields = generate_fields(Notice)
        extra_kwargs = {
            'create_time': {'read_only': True},
            'update_time': {'read_only': True},
        }

@version_based_cache
class LevelSerializers(serializers.HyperlinkedModelSerializer):
    icon_info = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = generate_fields(Level, add=['icon_info'])

    def get_icon_info(self, instance):
        if instance.icon:
            return FileSerializer(instance=instance.icon, context=self.context).data.get('file')
        return ''

    def validate(self, attrs):
        discount = attrs.get('discount')
        if discount < 0 or discount > 100:
            raise serializers.ValidationError('折扣设置错误，请输入0~100的数值(单位：%)')
        return attrs


@version_based_cache
class RechargeTypeSerializers(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = RechargeType
        fields = generate_fields(RechargeType)

    def validate(self, attrs):
        amount = attrs.get('amount')
        real_pay = attrs.get('real_pay')

        if amount < real_pay:
            raise serializers.ValidationError('充值金额不应小于实付金额')
        return attrs


@version_based_cache
class StoreLogoSerializers(serializers.Serializer):

    square_logo = obj(allow_null=True, label='正方形logo', queryset=File.objects.all(), required=False,
                 view_name='file-detail', serializer_class=FileSerializer)
    rectangle_logo = obj(allow_null=True, label='长方形logo', queryset=File.objects.all(), required=False,
                 view_name='file-detail', serializer_class=FileSerializer)

    def save(self, **kwargs):
        square_logo = self.validated_data.get('square_logo')
        rectangle_logo = self.validated_data.get('rectangle_logo')
        StoreLogo.objects.update_or_create(label='square_logo', defaults={'image': square_logo})
        StoreLogo.objects.update_or_create(label='rectangle_logo', defaults={'image': rectangle_logo})

        return {
            'square_logo': FileSerializer(instance=square_logo, context=self.context).data,
            'rectangle_logo': FileSerializer(instance=rectangle_logo, context=self.context).data,
        }


@version_based_cache
class StorePosterSerializers(serializers.Serializer):

    store_poster = obj(allow_null=True, label='分享海报', queryset=File.objects.all(), required=False,
                 view_name='file-detail', serializer_class=FileSerializer)

    def save(self, **kwargs):
        store_poster = self.validated_data.get('store_poster')

        StoreLogo.objects.update_or_create(label='store_poster', defaults={'image': store_poster})

        return {
            'store_poster': FileSerializer(instance=store_poster, context=self.context).data.get('file'),
        }


@version_based_cache
class WeChatConfigSerializers(serializers.Serializer):
    wx_lite_secret = serializers.CharField(label='小程序密钥', required=False)
    wx_pay_api_key = serializers.CharField(label='商户key', required=False)
    wx_pay_mch_id = serializers.CharField(label='商户号', required=False)
    wx_pay_mch_cert = serializers.FileField(label='商户证书', required=False)
    wx_pay_mch_key = serializers.FileField(label='商户证书私钥', required=False)

    def validate(self, attrs):
        if 'wx_pay_mch_cert' in attrs:
            attrs['wx_pay_mch_cert'] = attrs.get('wx_pay_mch_cert').read().decode()
        if 'wx_pay_mch_key' in attrs:
            attrs['wx_pay_mch_key'] = attrs.get('wx_pay_mch_key').read().decode()
        return attrs

    def save(self, **kwargs):
        for key, value in self.validated_data.items():
            WeChatConfig.set(key=key, value=value)
        WeChatConfig.environ()
        print(os.environ.get('wx_lite_secret'), os.environ.get('wx_pay_api_key'))
        return self.validated_data
