
from rest_framework import serializers
from rest_framework.reverse import reverse
from qapi.utils import generate_fields
from apps.utils.file_uri import file_uri
from apps.shop.models import Shop
from apps.goods.models import GoodType

from apps.group_buy.serializers import PtGroupSimpleSeriazlizers

from .models import UserAddress, Express, Orders, Invoice, Items, GoodsBackup, OrdGoodsBackUp, \
     DeliveryAddress, ReplGoodsBackUp, BuyerCode


class UserAddressSerializers(serializers.HyperlinkedModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    can_use = serializers.SerializerMethodField()

    class Meta:
        model = UserAddress
        fields = generate_fields(UserAddress, add=['can_use'], remove=['lat', 'lng'])
        # exclude = ('user',)

    def create(self, validated_data):
        if validated_data['is_default'] == True:
            user = validated_data['user']
            user.address.all().update(is_default=False)
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        if validated_data['is_default'] == True:
            user = validated_data['user']
            user.address.all().update(is_default=False)
        instance = super().update(instance, validated_data)
        return instance

    def get_can_use(self, instance):
        request = self.context.get('request')
        shop_id = request.query_params.get('shop', None)
        shop_id = int(shop_id) if shop_id else None
        shop = Shop.objects.filter(id=shop_id).first()
        if shop:
            return shop.is_range(instance.location)
        return False

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        user = self.validated_data.get('user')
        address = user.address.all()
        if not address.filter(is_default=True):
            a = address.order_by('-add_time').first()
            a.is_default = True
            a.save(update_fields=['is_default'])
            return instance
        return instance


class ExpressSerializers(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Express
        fields = generate_fields(Express, remove=['add_time'])

    def validate(self, attrs):
        name = attrs.get('name')
        if bool(Express.objects.filter(name=name)):
            raise serializers.ValidationError('该快递公司以存在')
        return attrs


class AdjustAmountSerializers(serializers.ModelSerializer):
    class Meta:
        model = Orders
        fields = ('real_amount',)

    def validate(self, attrs):
        real_amount = attrs.get('real_amount', None)
        if not real_amount:
            raise serializers.ValidationError('请输入调整后的价格')
        if real_amount < 0:
            raise serializers.ValidationError('实付金额应该大于0')
        return attrs

    def save(self, **kwargs):
        return self.validated_data.get('real_amount')


class DeliveryAddressSerializers(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = generate_fields(DeliveryAddress)


class InvoiceSerializers(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = generate_fields(Invoice, remove=['url'])


class OrdGoodsBackUpSerializers(serializers.ModelSerializer):
    class Meta:
        model = OrdGoodsBackUp
        fields = generate_fields(OrdGoodsBackUp, remove=['url', 'id'])


class ReplGoodsBackUpSerializers(serializers.ModelSerializer):
    class Meta:
        model = ReplGoodsBackUp
        fields = generate_fields(ReplGoodsBackUp, remove=['url', 'id'])


class GoodsBackupSerializers(serializers.ModelSerializer):
    ord_goods_info = OrdGoodsBackUpSerializers(read_only=True)
    repl_goods_info = ReplGoodsBackUpSerializers(read_only=True)
    image = serializers.SerializerMethodField()
    goods_url = serializers.HyperlinkedRelatedField(
        view_name='goods-detail',
        source='goods',
        read_only=True,
    )

    class Meta:
        model = GoodsBackup
        fields = generate_fields(GoodsBackup, add=['image', 'goods_url'], remove=['g_image', 'g_rebate', 'g_bonus', 'share_user_id',
                                                                     'order', 'gtype_id', 'url'])

    def get_image(self, instance):
        if instance.g_image:
            return file_uri(self.context.get('request'), instance.g_image)
        if getattr(instance, 'goods'):
            return file_uri(self.context.get('request'), instance.goods.image.file)
        return ''


class ItemsSerializers(serializers.HyperlinkedModelSerializer):
    order_sn = serializers.SerializerMethodField()
    add_time = serializers.SerializerMethodField()
    order_id = serializers.SerializerMethodField()
    zh_send_type = serializers.SerializerMethodField()
    goods_backup = GoodsBackupSerializers(read_only=True)
    send = serializers.SerializerMethodField()
    arrive = serializers.SerializerMethodField()
    confirm = serializers.SerializerMethodField()
    delivery_info = serializers.SerializerMethodField()
    logistics = serializers.SerializerMethodField()

    class Meta:
        model = Items
        fields = generate_fields(Items, add=['order_sn',  'add_time', 'order_id', 'zh_send_type', 'send', 'arrive', 'confirm',
                                         'delivery_info', 'logistics'], remove=['order', 'flag_time'])
        extra_kwargs = {
            'cycle': {'read_only': True},
            'send_date': {'read_only': True},
            'send_start': {'read_only': True},
            'send_end': {'read_only': True},
            'send_type': {'read_only': True},
            'send_time': {'read_only': True},
            'receive_time': {'read_only': True},
        }

    def get_order_sn(self, instance):
        return getattr(instance.order, 'order_sn', '')

    def get_add_time(self, instance):
        return getattr(instance.order, 'add_time', '')

    def get_order_id(self, instance):
        return getattr(instance.order, 'id', None)

    def get_zh_send_type(self, instance):
        status_map = {
            'own': {'paying': '待付款', 'sending': '待发货', 'receiving': '已发货', 'arrive': '已送达', 'over': '已收货',
                    'close': '已关闭'},
            'express': {'paying': '待付款', 'sending': '待发货', 'receiving': '已发货', 'over': '已收货', 'close': '已关闭'},
            'buyer': {'paying': '待付款', 'sending': '备货中', 'receiving': '待取件', 'arrive': '已取件', 'over': '已收货',
                      'close': '已关闭'}
        }
        return status_map[instance.goods_backup.delivery_method].get(instance.send_type)

    def get_send(self, instance):
        if not instance.send_type == instance.SENDING:
            return None
        if instance.order.model_type in [Orders.ORD, Orders.REPL]:
            return reverse('items-send', (instance.id,), request=self.context.get('request'))
        return None

    def get_arrive(self, instance):
        if instance.goods_backup.delivery_method == 'express':
            return None
        if instance.send_type == instance.RECEIVING:
            return reverse('items-arrive', (instance.id,), request=self.context.get('request'))
        return None

    def get_confirm(self, instance):
        if instance.order.model_type in [Orders.ORD, Orders.REPL]:  # 普通订单的确认收货在在订单处进行，不在子订单
            return None
        if instance.goods_backup.delivery_method == 'express':
            if instance.send_type == instance.RECEIVING:
                return reverse('items-confirm', (instance.id,), request=self.context.get('request'))
        if instance.send_type == instance.ARRIVE:
            return reverse('items-confirm', (instance.id,), request=self.context.get('request'))
        return None

    def get_delivery_info(self, instance):
        if instance.goods_backup.delivery_method == GoodsBackup.BUYER:
            buyercode = BuyerCode.objects.filter(item=instance).first()
            if buyercode:
                return {'buyer_no': buyercode.buyer_no, 'buyer_code': buyercode.buyer_code}
        return None

    def get_logistics(self, instance):
        if instance.express_company and instance.express_num:
            return reverse('items-logistics', (instance.id,), request=self.context.get('request'))
        return None


class OrdersSerializers(serializers.HyperlinkedModelSerializer):
    user_info = serializers.SerializerMethodField()
    goods_backup = GoodsBackupSerializers(many=True, read_only=True)
    items = ItemsSerializers(many=True, read_only=True)
    wallet_pay = serializers.SerializerMethodField()
    shop_info = serializers.SerializerMethodField()
    cancel = serializers.SerializerMethodField()
    confirm = serializers.SerializerMethodField()
    adjust = serializers.SerializerMethodField()
    invoice = InvoiceSerializers(read_only=True)
    delivery_address = DeliveryAddressSerializers(read_only=True)
    groupbuy = serializers.SerializerMethodField()
    entrust_shop_info = serializers.SerializerMethodField()

    class Meta:
        model = Orders
        fields = generate_fields(Orders,
                                 add=['user_info', 'items', 'goods_backup', 'wallet_pay', 'shop_info',
                                      'cancel', 'confirm', 'adjust', 'groupbuy', 'entrust_shop_info'],
                                 remove=['user', 'asset_pay', 'recharge_pay', 'flag_time'])
        extra_kwargs = {
            'user': {'read_only': True},
            'shop': {'read_only': True},
            'order_sn': {'read_only': True},
            'trade_no': {'read_only': True},
            'remark': {'read_only': True},
            'status': {'read_only': True},
            'model_type': {'read_only': True},
            'order_amount': {'read_only': True},
            'real_amount': {'read_only': True},
            'postage_total': {'read_only': True},
            'discount': {'read_only': True},
            'pay_time': {'read_only': True},
            'delivery_method': {'read_only': True},
            'next_send': {'read_only': True},
            'receive_time': {'read_only': True},
            'add_time': {'read_only': True},
        }

    def get_wallet_pay(self, instance):
        return instance.asset_pay + instance.recharge_pay

    def get_user_info(self, instance):
        if instance.user:
            return {
                'id': instance.user.id,
                'nickname': getattr(instance.user, 'nickname', ''),
                'avatar_url': getattr(instance.user, 'avatar_url', ''),
            }
        return {}

    def get_shop_info(self, instance):
        if instance.shop:
            return {'name': instance.shop.name, 'address': instance.shop.address}
        return {}

    def get_entrust_shop_info(self, instance):
        if instance.entrust_shop:
            return {'name': instance.entrust_shop.name, 'address': instance.entrust_shop.address}
        return None

    def get_cancel(self, instance):
        if instance.status == Orders.PAYING:
            return reverse('orders-cancel', (instance.id,), request=self.context.get('request'))
        return None

    def get_confirm(self, instance):
        if instance.status == Orders.RECEIVING:
            return reverse('orders-confirm', (instance.id,), request=self.context.get('request'))
        return None

    def get_adjust(self, instance):
        if instance.status == Orders.PAYING:
            return reverse('orders-adjust', (instance.id,), request=self.context.get('request'))
        return None

    def get_groupbuy(self, instance):
        if instance.status == instance.GROUPBUY:
            groupbuy = instance.pt_group.all().order_by('-add_time')
            return PtGroupSimpleSeriazlizers(groupbuy, many=True, context=self.context).data
        return None

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.status == instance.GROUPBUY and ret['groupbuy']:
            goods_backup = instance.goods_backup.first()
            gtype = None
            if instance.model_type == instance.ORD:
                gtype = GoodType.objects.filter(id=goods_backup.gtype_id).first()
            price_ladder = getattr(gtype, 'ladder_', None)
            for i in ret['groupbuy']:
                i.update({"price_ladder": price_ladder})
        return ret


class ExportBatchDeliverySerializer(serializers.Serializer):
    delivery = serializers.CharField()
    orders = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )


class QueryBatchDeliverySerializer(serializers.Serializer):
    orders = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
