"""

下单接口用到的serializers

"""
import simplejson as json
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.serializers import PrimaryKeyRelatedField
from apps.goods.models import Goods, GoodType, ReplGoodsType
from apps.config.models import BoolConfig
from apps.account.models import WxUserCreditLog
from apps.goods.utils import compute_postage
from apps.goods.utils import get_delivery_data_num
from apps.group_buy.models import PtGroup
from .models import UserAddress, Orders, Invoice, Items, GoodsBackup, DeliveryAddress
from .serializers import OrdersSerializers, InvoiceSerializers
from .utils import compute_amount


class GoodsItemField(serializers.Serializer):
    goods = PrimaryKeyRelatedField(allow_null=False, label='商品id', queryset=Goods.objects.all(), required=True)
    gtype = PrimaryKeyRelatedField(allow_null=False, label='商品规格id', queryset=GoodType.objects.all(), required=True)
    num = serializers.IntegerField(label='数量', required=True)
    delivery_method = serializers.ChoiceField(choices=GoodsBackup.METHOD, label='配送方式', allow_null=True)
    share_user_id = serializers.CharField(label='分享用户id', required=False, allow_null=True)
    attach = serializers.CharField(label='自定义字段', allow_null=True, required=False)

    class Meta:
        extra_kwargs = {
            'goods': {'required': True, 'allow_null': False},
            'gtype': {'required': True, 'allow_null': False},
            'num': {'required': True, 'min_value': 1},
        }


class CartBuySerializers(serializers.ModelSerializer):
    goodsitems = serializers.ListSerializer(label='所购商品列表', child=GoodsItemField(), required=True, allow_empty=False)
    address = PrimaryKeyRelatedField(allow_null=True, label='收货地址', queryset=UserAddress.objects.all(), required=True)
    use_wallet = serializers.BooleanField(label='使用会员钱包', default=False)
    invoice = InvoiceSerializers(write_only=True, allow_null=True)
    is_pt = serializers.BooleanField(label='是否拼团', default=False)
    groupbuy = PrimaryKeyRelatedField(allow_null=True, label='拼团', queryset=PtGroup.objects.all(), required=False)

    class Meta:
        model = Orders
        fields = ('goodsitems', 'address', 'remark', 'use_wallet', 'shop', 'invoice', 'is_pt', 'groupbuy',  'fictitious')

        extra_kwargs = {
            'goodsitem': {'required': True},
            'address': {'required': True},
            'remark': {'required': False, 'allow_null': True},
            'shop': {'required': True},
        }

    def validate(self, attrs):
        if BoolConfig.get_value('open_buy') == 'false':
            raise serializers.ValidationError('正在备货，尚未开放购买，请谅解')
        request = self.context.get('request')
        address = attrs.get('address')
        shop = attrs.get('shop', None)
        if shop and shop.status != shop.OPEN:
            raise serializers.ValidationError('该店已经暂时未营业，请选择其他店')
        if address and request.user != address.user:
            raise serializers.ValidationError('收货地址设置错误')
        goodsitems = attrs.get('goodsitems')
        if attrs.get('fictitious', False) and len(goodsitems) != 1:
            raise serializers.ValidationError('虚拟商品只能单件购买，无法与其他商品一同下单')
        for item in goodsitems:
            goods = item.get('goods')
            gtype = item.get('gtype')
            num = item.get('num')
            if attrs.get('fictitious', False) and not goods.fictitious:
                raise serializers.ValidationError(f'{goods.name}不是虚拟商品')

            if not goods.fictitious and (
                    not item.get('delivery_method') or item.get('delivery_method') not in goods.delivery_method):
                raise serializers.ValidationError('配送方式选择有误')

            if shop and goods.shop != shop:
                raise serializers.ValidationError(f'本店没有{goods.name}这个商品')
            if goods.model_type != goods.ORD:
                raise serializers.ValidationError(f'商品{goods.name}是订阅商品！')
            if gtype not in goods.ord_goods.gtypes.all():
                raise serializers.ValidationError(f'商品{goods.name}没有{gtype.content}这个规格')
            if goods.status in [Goods.NOT_SELL, Goods.NOT_ENOUGH]:
                raise serializers.ValidationError(f'商品{goods.name}已下架')
            if not gtype.is_sell:
                raise serializers.ValidationError(f'{gtype.content}暂不可选，请选择其他类型')
            if gtype.stock < num:
                raise serializers.ValidationError(f'{gtype.content}库存不足，请重新选择商品数量')

            if gtype.buy_limit is not None:    # 判断限购
                orders = Orders.objects.exclude(status=Orders.CLOSE). \
                    filter(user=request.user, model_type=Orders.ORD,  goods_backup__gtype_id=gtype.id,
                           add_time__gte=gtype.change_limit)
                has_buy_num = 0
                for order in orders:
                    has_buy = order.goods_backup.filter(gtype_id=gtype.id).aggregate(total=Sum('num'))
                    has_buy_num += has_buy.get('total') if has_buy.get('total') else 0

                if num + has_buy_num > gtype.buy_limit:
                    can_buy_num = gtype.buy_limit - has_buy_num if (gtype.buy_limit - has_buy_num) >= 0 else 0
                    raise serializers.ValidationError(
                        f'{gtype.content}限购{gtype.buy_limit}件, 已购{has_buy_num}件，还可购{can_buy_num}件')
        if attrs['is_pt']:
            self.validate_pt(goodsitems, attrs['groupbuy'])
        return attrs

    def validate_pt(self, goodsitems, groupbuy):
        print(len(goodsitems))
        if len(goodsitems) > 1:
            raise serializers.ValidationError('拼团请选择一种商品')
        goods = goodsitems[0]
        if not goods.get('goods').groupbuy:
            raise serializers.ValidationError('该商品不是拼团商品')
        if not goods.get('gtype').ladder_:
            raise serializers.ValidationError('商品状态异常，请稍后购买会联系客服')
        if groupbuy:
            request = self.context.get('request')
            if request.user in groupbuy.partake.all():
                raise serializers.ValidationError('您已参与本拼团队伍')
            if goods.get('goods') != groupbuy.ptgoods:       #是否是同一件商品
                raise serializers.ValidationError('无法加入该团')
            if groupbuy.status != groupbuy.BUILD:
                raise serializers.ValidationError('该团可能已经结算，请参与其他的团')

    def save(self, **kwargs):
        request = self.context.get('request')
        user = request.user
        address = self.validated_data.pop('address')
        remark = self.validated_data.get('remark')
        invoice = Invoice.objects.create(**self.validated_data.pop('invoice'))
        delivery_address = None
        if address:
            delivery_address = DeliveryAddress.create(address)
        shop = self.validated_data.get('shop')
        goodsitems = self.validated_data.pop('goodsitems')
        use_wallet = self.validated_data.pop('use_wallet')
        is_pt = self.validated_data.get('is_pt')
        groupbuy = self.validated_data.get('groupbuy')
        fictitious = self.validated_data.get('fictitious', False)

        level = getattr(user, 'level', None)
        discount = 1
        if level and BoolConfig.get_bool('wallet_switch') and not is_pt:
            discount = level.discount

        order = Orders.create(user, shop, remark, Orders.ORD, discount, invoice, delivery_address, is_pt, fictitious)
        order_amount_total = 0
        postage_total = 0
        for item in goodsitems:
            goods = item.pop('goods')
            gtype = item.pop('gtype')
            goodsbackup = GoodsBackup.create(order, goods, gtype, discount=discount, is_pt=is_pt, **item)
            Items.create(order, goodsbackup)
            order_amount = goodsbackup.price * goodsbackup.num
            postage_total += compute_postage(goods, getattr(address, 'location', None), item.get('delivery_method'))
            order_amount_total += order_amount
        order = compute_amount(order, order_amount_total, postage_total, use_wallet)
        if groupbuy:
            groupbuy.order.add(order)
        return OrdersSerializers(order, context=self.context).data


class ReplaceGoodsSerializers(serializers.ModelSerializer):
    goods = PrimaryKeyRelatedField(allow_null=False, label='商品', queryset=Goods.objects.all(), required=True)
    gtype = PrimaryKeyRelatedField(allow_null=False, label='商品规格id', queryset=ReplGoodsType.objects.all(), required=True)
    address = PrimaryKeyRelatedField(allow_null=True, label='收货地址', queryset=UserAddress.objects.all(), required=True)
    num = serializers.IntegerField(label='数量', required=True)
    use_wallet = serializers.BooleanField(label='使用会员钱包', default=False)
    delivery_method = serializers.ChoiceField(choices=GoodsBackup.METHOD, label='配送方式', allow_null=True)
    attach = serializers.CharField(label='自定义字段', allow_null=True, required=False)

    class Meta:
        model = Orders
        fields = ('goods', 'gtype', 'address', 'remark', 'shop', 'num', 'use_wallet',
                  'delivery_method', 'attach', 'fictitious')
        extra_kwargs = {
            'address': {'required': True},
            'remark': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        request = self.context.get('request')
        address = attrs.get('address')
        goods = attrs.get('goods')
        gtype = attrs.get('gtype')
        num = attrs.get('num')
        shop = attrs.get('shop', None)
        if shop and shop.status != shop.OPEN:
            raise serializers.ValidationError('该店已经暂时未营业，请选择其他店')
        if attrs.get('fictitious', False) and not goods.fictitious:
            raise serializers.ValidationError(f'{goods.name}不是虚拟商品')
        if address and request.user != address.user:
            raise serializers.ValidationError('收货地址设置错误')
        if gtype.stock < num:
            raise serializers.ValidationError(f'{gtype.content}库存不足，请重新选择商品数量')

        if request.user.account.credit < num * gtype.credit:
            raise serializers.ValidationError(f'您的积分不足')

        if shop and goods.shop != shop:
            raise serializers.ValidationError(f'本店没有{goods.name}这个商品')
        if goods.model_type != goods.REPLACE:
            raise serializers.ValidationError(f'商品{goods.name}是不是积分换购商品！')
        if gtype not in goods.repl_goods.gtypes.all():
            raise serializers.ValidationError(f'商品{goods.name}没有{gtype.content}这个规格')
        if goods.status in [Goods.NOT_SELL, Goods.NOT_ENOUGH]:
            raise serializers.ValidationError(f'商品{goods.name}已下架')
        if not gtype.is_sell:
            raise serializers.ValidationError(f'{gtype.content}暂不可选，请选择其他类型')

        if not goods.fictitious and (
                not attrs.get('delivery_method') or attrs.get('delivery_method') not in goods.delivery_method):
            raise serializers.ValidationError('配送方式选择有误')

        if gtype.buy_limit is not None:  # 判断限购
            orders = Orders.objects.exclude(status=Orders.CLOSE). \
                filter(user=request.user, model_type=Orders.REPL, goods_backup__gtype_id=gtype.id,
                       add_time__gte=gtype.change_limit)
            has_buy_num = 0
            for order in orders:
                has_buy = order.goods_backup.filter(gtype_id=gtype.id).aggregate(total=Sum('num'))
                has_buy_num += has_buy.get('total') if has_buy.get('total') else 0

            if num + has_buy_num > gtype.buy_limit:
                can_buy_num = gtype.buy_limit - has_buy_num if (gtype.buy_limit - has_buy_num) >= 0 else 0
                raise serializers.ValidationError(
                    f'{gtype.content}限购{gtype.buy_limit}件, 已购{has_buy_num}件，还可购{can_buy_num}件')

        return attrs

    def save(self, **kwargs):
        request = self.context.get('request')
        user = request.user
        goods = self.validated_data.get('goods')
        gtype = self.validated_data.get('gtype')
        num = self.validated_data.get('num')
        address = self.validated_data.get('address')
        remark = self.validated_data.get('remark')
        attach = self.validated_data.get('attach')
        fictitious = self.validated_data.get('fictitious', False)
        use_wallet = self.validated_data.pop('use_wallet')
        delivery_method = self.validated_data.get('delivery_method', False)

        delivery_address = None
        if address:
            delivery_address = DeliveryAddress.create(address)
        credit = num * gtype.credit

        shop = self.validated_data.get('shop')
        order = Orders.create(user, shop, remark, Orders.REPL, discount=1, invoice=None, delivery_address=delivery_address,
                              is_pt=False, fictitious=fictitious, credit=credit)
        if gtype.price > 0:
            order_amount_total = gtype.price * num
            order = compute_amount(order, order_amount_total, 0, use_wallet)
            if not order.real_amount > 0:
                order.status = Orders.HAS_PAID
                order.pay_time = timezone.now()
                order.save()
        else:
            order.order_amount = order.real_amount = 0
            order.status = Orders.HAS_PAID
            order.pay_time = timezone.now()
            order.save()

        goodsbackup = GoodsBackup.create(order, goods, gtype, num=num, delivery_method=delivery_method, attach=attach)
        Items.create(order, goodsbackup, send_type=Items.SENDING)
        WxUserCreditLog.record(user, WxUserCreditLog.REPLACEMENT, credit=gtype.credit * num,
                               remark='商品积分换购', note=goods.name, number=order.order_sn)
        return OrdersSerializers(order, context=self.context).data


class QrPaySerSerializers(serializers.ModelSerializer):
    money = serializers.DecimalField(label='支付金额', max_digits=None, decimal_places=2, min_value=0, required=True)
    use_wallet = serializers.BooleanField(label='使用会员钱包', default=False)

    class Meta:
        model = Orders
        fields = ('shop', 'money', 'use_wallet', 'machine_code')
        extra_kwargs = {
            'machine_code': {'required': True, 'allow_null': False},
        }

    def validate(self, attrs):
        machine_code = attrs.get('machine_code')
        if not machine_code:
            return attrs
        client = Client(settings.YLY_CLIENT_ID, settings.YLY_CLIENT_SECRET)
        res = client.status.get_status(settings.YLY_ACCESS_TOKEN, machine_code)
        status = res.get('body', {})
        if status.get('display', '离线') == '离线':
            raise serializers.ValidationError('线下收款器可能存在故障，请联系店铺员工')
        return attrs

    def save(self, **kwargs):
        request = self.context.get('request')
        user = request.user
        shop = self.validated_data.get('shop')
        use_wallet = self.validated_data.get('use_wallet')
        money = self.validated_data.get('money')
        machine_code = self.validated_data.get('machine_code')
        order = Orders.create(user, shop, remark=None, model_type=Orders.QRPAY, discount=1, invoice=None,
                              delivery_address=None, machine_code=machine_code)
        order = compute_amount(order, money, 0, use_wallet)
        return OrdersSerializers(order, context=self.context).data