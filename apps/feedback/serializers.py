from rest_framework import serializers
from rest_framework.reverse import reverse
from qapi.utils import generate_fields
from .models import FeedBack, FeedbackOperationLog


class FeedbackOperationLogSerializer(serializers.ModelSerializer):

    admin_name = serializers.SerializerMethodField()

    class Meta:
        model = FeedbackOperationLog
        fields = ('admin_name', 'add_time', 'operation')

    def get_admin_name(self, instance):
        if instance.admin:
            return instance.admin.username
        return None


class FeedBackSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    update_status = serializers.SerializerMethodField()
    goods_info = serializers.SerializerMethodField()
    order_info = serializers.SerializerMethodField()
    operation_log = serializers.SerializerMethodField()

    class Meta:
        model = FeedBack
        fields = generate_fields(FeedBack, add=['user_info', 'update_status', 'goods_info',  'order_info', 'operation_log'])

        extra_kwargs = {
            'solve': {'read_only': True},
            'update_time': {'read_only': True},
            'add_time': {'read_only': True},
        }

    def get_update_status(self, instance):
        return reverse('feedback-solve', (instance.id,), request=self.context.get('request'))

    def get_user_info(self, instance):
        if instance.user:
            return {
                'nickname': instance.user.nickname,
                'avatar_url': instance.user.avatar_url
            }
        return {}

    def get_goods_info(self, instance):
        if instance.goods:
            return {
                'goods_name': instance.goods.name,
                'model_type': instance.goods.model_type,
            }
        return {}

    def get_order_info(self, instance):
        if instance.order:
            return {
                'order_sn': instance.order.order_sn,
                'model_type': instance.order.model_type,
            }
        return {}

    def get_operation_log(self, instance):
        if instance.operation_log.all():
            return FeedbackOperationLogSerializer(instance=instance.operation_log.all(), many=True, context=self.context).data
        return None