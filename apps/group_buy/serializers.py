import simplejson as json
from rest_framework import serializers
from rest_framework.serializers import PrimaryKeyRelatedField
from qapi.utils import generate_fields
from apps.trade.models import Orders
from apps.goods.models import Goods
from .models import PtGroup, GroupBuyInfo


class LadderField(serializers.Serializer):
    index = serializers.IntegerField(label='阶梯', required=True, allow_null=False, min_value=0)
    num = serializers.IntegerField(label='数量', required=True,  allow_null=False, min_value=0)


class GroupBuyInfoSeriazlizers(serializers.ModelSerializer):
    ladder_list = serializers.ListField(label='阶梯设置', child=LadderField(), allow_null=False, required=False)

    class Meta:
        model = GroupBuyInfo
        fields = generate_fields(GroupBuyInfo, add=['ladder_list'], remove=['ladder'])

    def validate(self, attrs):
        if not attrs['ladder_list']:
            raise serializers.ValidationError('请设置阶梯')
        attrs['ladder'] = json.dumps(attrs.pop('ladder_list'))
        return attrs

    def validate_ladder_list(self, value):
        groupbuy_goods = getattr(self.instance, 'groupbuy_goods', None)
        if groupbuy_goods and groupbuy_goods.team_goods.filter(status='build'):
            if self.instance.ladder_ != sorted(value, key=lambda x: x.get('index')):
                raise serializers.ValidationError('该商品存在正在进行中的拼团，不可修改拼团阶梯信息和商品规格价格阶梯')
        return value

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['ladder_list'] = json.loads(instance.ladder)
        return ret


class OrderSimpleSeriazlizers(serializers.HyperlinkedModelSerializer):
    user_info = serializers.SerializerMethodField()
    goods_info = serializers.SerializerMethodField()

    class Meta:
        model = Orders
        fields = ('url', 'id', 'order_sn', 'model_type', 'user_info', 'goods_info')

    def get_user_info(self, instance):
        if instance.user:
            return {
                    'id': getattr(instance.user, 'id'),
                    'nickname': getattr(instance.user, 'nickname', ''),
                    'avatar_url': getattr(instance.user, 'avatar_url', '')}
        return {}

    def get_goods_info(self, instance):
        goods_backup = instance.goods_backup.first()
        if goods_backup:
            return {
                'name': goods_backup.goods_name + goods_backup.gtype_name,
                'price': goods_backup.price,
                'num': goods_backup.num,
                'order_amount': goods_backup.price * goods_backup.num,
            }
        return {}


class PtGroupSeriazlizers(serializers.HyperlinkedModelSerializer):
    '''
    管理后台拼团列表详情序列化
    '''
    owner = serializers.SerializerMethodField()
    partake_count = serializers.SerializerMethodField()
    goods_count = serializers.SerializerMethodField()
    ladder = serializers.SerializerMethodField()
    order = serializers.SerializerMethodField()

    class Meta:
        model = PtGroup
        fields = generate_fields(PtGroup, add=['ladder', 'owner', 'partake_count', 'goods_count'])
        extra_kwargs = {
            'ptgroup_no': {'read_only': True},
            'ptgoods': {'read_only': True},
            'goods_name': {'read_only': True},
            'shop': {'read_only': True},
            'partake': {'read_only': True},
            'user': {'read_only': True},
            'mode': {'read_only': True},
            'status': {'read_only': True},
            'add_time': {'read_only': True},
            'end_time': {'read_only': True},
            'order': {'read_only': True},
        }

    def validate(self, attrs):
        instance = self.instance
        if instance.status != PtGroup.BUILD:
            return attrs
        if attrs['robot'] > attrs['robot_goods']:
            raise serializers.ValidationError('机器人设置错误')
        if instance.ptgoods.model_type == 'sub' and attrs['robot'] != attrs['robot_goods']:
            raise serializers.ValidationError('机器人设置错误')
        return attrs

    def get_owner(self, instance):
        if instance.user:
            return {
                'id': instance.user.id,
                'nickname': instance.user.nickname,
                'avatar_url': instance.user.avatar_url
            }
        return {}

    def get_partake_count(self, instance):
        return instance.partake.count()

    def get_goods_count(self, instance):
        count = 0
        if instance.status == instance.BUILD:
            for order in instance.order.filter(status=Orders.GROUPBUY):  #拼团时只计算以支付的订单
                count += order.goods_backup.first().num
        else:
            for order in instance.order.exclude(status=Orders.PAYING):
                count += order.goods_backup.first().num
        return count

    def get_order(self, instance):
        order = instance.order.exclude(status=Orders.PAYING)
        return OrderSimpleSeriazlizers(instance=order, many=True, context=self.context).data

    def get_ladder(self, instance):
        ptgoods = getattr(instance, 'ptgoods', None)
        groupbuy_info = getattr(ptgoods, 'groupbuy_info', None)
        pt_ladder = getattr(groupbuy_info, 'ladder_', None)
        return pt_ladder


class PtGroupListSeriazlizers(serializers.ModelSerializer):
    '''
    小程序拼团列表页的序列化
    '''
    owner = serializers.SerializerMethodField()
    partake_count = serializers.SerializerMethodField()
    goods_count = serializers.SerializerMethodField()
    ladder = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()

    class Meta:
        model = PtGroup
        fields = generate_fields(PtGroup, add=['owner', 'partake_count', 'goods_count', 'can_join', 'ladder'],
                                 remove=['robot', 'robot_goods', 'order'])

    def get_owner(self, instance):
        if instance.user:
            return {
                'nickname': instance.user.nickname,
                'avatar_url': instance.user.avatar_url
            }
        return {}

    def get_partake_count(self, instance):
        return instance.partake.count() + instance.robot

    def get_goods_count(self, instance):
        count = 0
        for order in instance.order.filter(status=Orders.GROUPBUY):
            count += order.goods_backup.first().num
        return count + instance.robot_goods

    def get_ladder(self, instance):
        ptgoods = getattr(instance, 'ptgoods', None)
        groupbuy_info = getattr(ptgoods, 'groupbuy_info', None)
        pt_ladder = getattr(groupbuy_info, 'ladder_', None)
        return pt_ladder

    def get_can_join(self, instance):
        request = self.context.get('request')
        user = request.user
        if request.user.is_anonymous:
            return True
        if getattr(user, 'is_wechat', None) and user not in instance.partake.all():
            return True
        return False


class PtGroupSimpleSeriazlizers(serializers.ModelSerializer):
    '''
    订单中的拼团信息序列化
    '''
    owner = serializers.SerializerMethodField()
    partake_count = serializers.SerializerMethodField()
    goods_count = serializers.SerializerMethodField()
    ladder = serializers.SerializerMethodField()
    integral = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = PtGroup
        fields = generate_fields(PtGroup, add=['owner', 'partake_count', 'goods_count', 'ladder', 'integral', 'is_owner'],
                                 remove=['robot', 'robot_goods', 'order', 'ptgoods'])

    def get_owner(self, instance):
        if instance.user:
            return {
                'nickname': instance.user.nickname,
                'avatar_url': instance.user.avatar_url
            }
        return {}

    def get_partake_count(self, instance):
        return instance.partake.count() + instance.robot

    def get_goods_count(self, instance):
        count = 0
        for order in instance.order.filter(status=Orders.GROUPBUY):
            count += order.goods_backup.first().num
        return count + instance.robot_goods

    def get_ladder(self, instance):
        ptgoods = getattr(instance, 'ptgoods', None)
        groupbuy_info = getattr(ptgoods, 'groupbuy_info', None)
        pt_ladder = getattr(groupbuy_info, 'ladder_', None)
        return pt_ladder

    def get_integral(self, instance):
        ptgoods = getattr(instance, 'ptgoods', None)
        groupbuy_info = getattr(ptgoods, 'groupbuy_info', None)
        integral = getattr(groupbuy_info, 'integral', 0)
        return integral

    def get_is_owner(self, instance):
        request = self.context.get('request')
        user = request.user
        if user and user == instance.user:
            return True
        return False


class BuildPtGroups(serializers.Serializer):
    order = PrimaryKeyRelatedField(allow_null=False, label='订单id', queryset=Orders.objects.all(), required=True)

    def validate(self, attrs):
        order = attrs.get('order')
        if order.status != order.GROUPBUY or not order.pt_group.all():
            raise serializers.ValidationError('该订单已结算或未参团，请重新下单后发起拼团')
        if order.pt_group.filter(user=order.user):
            raise serializers.ValidationError('该订单已经发起过拼团，请勿再次发起拼团')
        ptgoods = order.pt_group.first().ptgoods
        attrs['ptgoods'] = ptgoods
        if not ptgoods.groupbuy or ptgoods.status != Goods.IS_SELL:
            raise serializers.ValidationError('该商品已下架或不参与拼团活动，请选择其他商品参与拼团')
        return attrs

    def save(self, **kwargs):
        order = self.validated_data.get('order')
        ptgoods = self.validated_data.get('ptgoods')
        instance = PtGroup.create(order.user, ptgoods, order.shop)
        instance.partake.add(order.user)
        instance.order.add(order)
        return PtGroupListSeriazlizers(instance, context=self.context).data