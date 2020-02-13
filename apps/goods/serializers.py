import simplejson as json
from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from rest_framework.reverse import reverse
from django.db.models import Q
from qapi.utils import generate_fields

from qcache.contrib.drf import version_based_cache


from apps.config.models import BoolConfig
from apps.qfile.models import File
from apps.qfile.serializers import FileSerializer
from apps.shop.serializers import ShopSerializer
from apps.shop.models import Shop
from apps.group_buy.models import GroupBuyInfo
from apps.group_buy.serializers import GroupBuyInfoSeriazlizers

from apps.utils.obj_related_field import ObjectHyperlinkedRelatedField
from apps.utils.object_related_field import ObjectHyperlinkedRelatedField as obj
from apps.utils.lbs import lbs

from .models import GoodsCategory, Images, Goods, OrdGoods, GoodType, Banner, HotWord, Attach, ReplGoods, ReplGoodsType
from .utils import compute_postage, format_date, get_delivery_data_num


@version_based_cache
class GoodsCategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = GoodsCategory
        fields = generate_fields(GoodsCategory)


@version_based_cache
class GoodsCategorySimplifiedSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = GoodsCategory
        fields = ["id", "name"]


@version_based_cache
class HotWordSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = HotWord
        fields = generate_fields(HotWord)


class CartField(serializers.Serializer):
    goodsid = serializers.IntegerField(label='商品id')
    gtypeid = serializers.IntegerField(label='规格id')


class CartSerializer(serializers.Serializer):
    items_list = CartField(many=True)
    is_pt = serializers.BooleanField(label='是否是拼团', default=False)
    address = serializers.CharField(label='配送地址', required=False, allow_null=True)

    def save(self, **kwargs):
        items_list = self.validated_data.get('items_list', {})
        address = self.validated_data.get('address')
        is_pt = self.validated_data.get('is_pt')
        user = self.context.get('request').user
        discount = 1
        if getattr(user, 'level', None) and BoolConfig.get_bool('wallet_switch') and not is_pt:
            discount = getattr(user, 'level', None).discount
        res = []
        if address:
            address = lbs.get_longitude_and_latitude(address)
        for item in items_list:
            data = {}
            goods = Goods.objects.filter(pk=item.get('goodsid'), status__in=[Goods.IS_SELL, Goods.PREVIEW]).first()
            gtype = GoodType.objects.filter(pk=item.get('gtypeid'), is_sell=True).first()
            if not goods or not gtype or gtype not in goods.ord_goods.gtypes.all():
                continue
            data = {
                'goodid': goods.id,
                'gtypeid': gtype.id,
                'goods_name': goods.name,
                'gtype_name': gtype.content,
                'shop': getattr(goods.shop, 'id', None),
                'shop_name': getattr(goods.shop, 'name', ''),
                'shop_address': getattr(goods.shop, 'address', ''),
                'estimate_time': goods.ord_goods.estimate_time,
                'delivery_method': goods.delivery_method,
                'market_price': gtype.market_price,
                'original_price': gtype.price,
                'price': Decimal(gtype.price * discount).quantize(Decimal('0.00')) if not is_pt else gtype.ladder_[
                    0].get('price'),
                'stock': gtype.stock,
                'discount': discount,
                'buy_limit': gtype.buy_limit,
                'postage': compute_postage(goods, address),
                'image': FileSerializer(instance=goods.banner.first().image, context=self.context).data.get('file')
            }
            if getattr(goods.shop, 'entrust', None):  # 店铺被委托时返回被委托的店铺信息
                data.update({
                    'entrust_shop_name': getattr(goods.shop.entrust, 'name', ''),
                    'entrust_shop_address': getattr(goods.shop.entrust, 'address', ''),
                })
            res.append(data)
        return res


@version_based_cache
class ValidateReplgoods(serializers.Serializer):
    goodsid = serializers.IntegerField(label='换购商品id')
    gtypeid = serializers.IntegerField(label='规格id')

    def validate(self, attrs):
        goodsid = attrs.get('goodsid')
        gtypeid = attrs.get('gtypeid')
        goods = Goods.objects.filter(pk=goodsid).first()
        gtype = ReplGoodsType.objects.filter(pk=gtypeid).first()
        if not goods or not gtype:
            raise serializers.ValidationError('没有该商品或规格')
        if gtype not in goods.repl_goods.gtypes.all():
            raise serializers.ValidationError('该商品没有这个规格')
        attrs['goods'] = goods
        attrs['gtype'] = gtype
        return attrs

    def save(self, **kwargs):

        goods = self.validated_data.get('goods')
        gtype = self.validated_data.get('gtype')
        data = {
            'goodid': goods.id,
            'gtypeid': gtype.id,
            'goods_name': goods.name,
            'gtype_name': gtype.content,
            'shop': getattr(goods.shop, 'id', None),
            'shop_name': getattr(goods.shop, 'name', ''),
            'shop_address': getattr(goods.shop, 'address', ''),
            'estimate_time': goods.repl_goods.estimate_time,
            'delivery_method': goods.delivery_method,
            'price': gtype.price,
            'stock': gtype.stock,
            'image': FileSerializer(instance=goods.banner.first().image, context=self.context).data.get(
                'file')
        }
        if getattr(goods.shop, 'entrust', None):  # 店铺被委托时返回被委托的店铺信息
            data.update({
                'entrust_shop_name': getattr(goods.shop.entrust, 'name', ''),
                'entrust_shop_address': getattr(goods.shop.entrust, 'address', ''),
            })
        return data


@version_based_cache
class ImagesSerializer(serializers.HyperlinkedModelSerializer):
    image = obj(allow_null=True, label='图片', queryset=File.objects.all(), required=False,
                view_name='file-detail', serializer_class=FileSerializer)

    class Meta:
        model = Images
        fields = generate_fields(Images, add=[])


class LadderField(serializers.Serializer):
    index = serializers.IntegerField(label='阶梯', required=True, allow_null=False, min_value=0)
    price = serializers.DecimalField(label='价格', required=True, allow_null=False, max_digits=19, decimal_places=2,
                                     min_value=0)


@version_based_cache
class ReplGoodsTypeSerializer(serializers.HyperlinkedModelSerializer):
    icon = obj(allow_null=True, label='封面图', queryset=File.objects.all(), required=False,
               view_name='file-detail', serializer_class=FileSerializer)

    class Meta:
        model = ReplGoodsType
        fields = generate_fields(ReplGoodsType, remove=['original_limit', 'change_limit', ])


@version_based_cache
class GoodsTypeSerializer(serializers.HyperlinkedModelSerializer):
    icon = obj(allow_null=True, label='封面图', queryset=File.objects.all(), required=False,
               view_name='file-detail', serializer_class=FileSerializer)
    ladder_list = serializers.ListField(label='阶梯', child=LadderField(), allow_null=True, required=False)

    class Meta:
        model = GoodType
        fields = generate_fields(GoodType, add=['ladder_list'], remove=['original_limit', 'ladder'])

    def validate(self, attrs):
        if attrs.get('ladder_list'):
            attrs['ladder'] = json.dumps(attrs['ladder_list'], use_decimal=True)
        attrs.pop('ladder_list')
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.ladder:
            ret['ladder_list'] = json.loads(instance.ladder, use_decimal=True)
        else:
            ret['ladder_list'] = None
        return ret


@version_based_cache
class GoodsTypeSimplifiedSerializer(serializers.HyperlinkedModelSerializer):
    icon = obj(allow_null=True, label='封面图', queryset=File.objects.all(), required=False,
               view_name='file-detail', serializer_class=FileSerializer)
    ladder_list = serializers.ListField(label='阶梯', child=LadderField(), allow_null=True, required=False)

    class Meta:
        model = GoodType
        fields = ["id", "market_price", "price", "is_sell", "ladder_list"]

    def validate(self, attrs):
        if attrs.get('ladder_list'):
            attrs['ladder'] = json.dumps(attrs['ladder_list'], use_decimal=True)
        attrs.pop('ladder_list')
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.ladder:
            ret['ladder_list'] = json.loads(instance.ladder, use_decimal=True)
        else:
            ret['ladder_list'] = None
        return ret


@version_based_cache
class AttachSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Attach
        fields = generate_fields(Attach)


@version_based_cache
class OrdGoodsSerializer(serializers.HyperlinkedModelSerializer):
    gtypes = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        label='商品规格',
        many=True,
        queryset=GoodType.objects.all(),
        view_name='goodtype-detail',
        serializer_class=GoodsTypeSerializer,
        is_save=True
    )

    class Meta:
        model = OrdGoods
        fields = generate_fields(OrdGoods, add=['estimate_time', 'price_range', 'market_price_range', 'max_rebate'])
        extra_kwargs = {
            'price_range': {'read_only': True},
            'market_price_range': {'read_only': True},
            'max_rebate': {'read_only': True},
        }

@version_based_cache
class OrdGoodsSimplifiedSerializer(serializers.HyperlinkedModelSerializer):
    gtypes = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        label='商品规格',
        many=True,
        queryset=GoodType.objects.all(),
        view_name='goodtype-detail',
        serializer_class=GoodsTypeSimplifiedSerializer,
        is_save=True
    )

    class Meta:
        model = OrdGoods
        fields = ["id", "gtypes"]


@version_based_cache
class ReplGoodsSerializer(serializers.HyperlinkedModelSerializer):
    gtypes = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        label='积分商品规格',
        many=True,
        queryset=ReplGoodsType.objects.all(),
        view_name='replgoodstype-detail',
        serializer_class=ReplGoodsTypeSerializer,
        is_save=True
    )

    class Meta:
        model = ReplGoods
        fields = generate_fields(ReplGoods, add=['price_range'])
        extra_kwargs = {
            'price_range': {'read_only': True},
        }


@version_based_cache
class GoodsSerializer(serializers.HyperlinkedModelSerializer):
    banner = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        label='详情页轮播图', required=False,
        allow_null=True,
        many=True,
        queryset=Images.objects.all(),
        view_name='images-detail',
        serializer_class=ImagesSerializer,
        is_save=True
    )
    detail = ObjectHyperlinkedRelatedField(
        allow_empty=False, label='商品详情图',
        many=True,
        allow_null=True,
        required=False,
        queryset=Images.objects.all(),
        view_name='images-detail',
        serializer_class=ImagesSerializer,
        is_save=True
    )

    ord_goods = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        allow_null=True,
        label='普通商品',
        queryset=OrdGoods.objects.all(),
        view_name='ordgoods-detail',
        serializer_class=OrdGoodsSerializer,
        is_save=True
    )

    repl_goods = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        allow_null=True,
        label='积分商品',
        queryset=ReplGoods.objects.all(),
        view_name='replgoods-detail',
        serializer_class=ReplGoodsSerializer,
        is_save=True
    )

    groupbuy_info = ObjectHyperlinkedRelatedField(
        allow_empty=False, required=False, allow_null=True, label='拼团信息',
        queryset=GroupBuyInfo.objects.all(), view_name='groupbuyinfo-detail',
        serializer_class=GroupBuyInfoSeriazlizers, is_save=True
    )

    image = obj(allow_null=True, label='封面图', queryset=File.objects.all(), required=False,
                view_name='file-detail', serializer_class=FileSerializer)
    video = obj(allow_null=True, label='视频介绍', queryset=File.objects.all(), required=False,
                view_name='file-detail', serializer_class=FileSerializer)

    poster = obj(allow_null=True, label='海报图', queryset=File.objects.all(), required=False,
                 view_name='file-detail', serializer_class=FileSerializer)

    category = obj(allow_null=True, label='商品分类', queryset=GoodsCategory.objects.all(), required=False,
                   view_name='goodscategory-detail', serializer_class=GoodsCategorySerializer)

    shop = obj(allow_null=True, label='所属商店', queryset=Shop.objects.all(), required=False,
               view_name='shop-detail', serializer_class=ShopSerializer)
    create_poster = serializers.SerializerMethodField()

    attach = ObjectHyperlinkedRelatedField(
        label='自定义信息',
        many=True,
        allow_null=True,
        required=False,
        queryset=Attach.objects.all(),
        view_name='attach-detail',
        serializer_class=AttachSerializer,
        is_save=True
    )
    status = serializers.ChoiceField(label='商品状态', required=True, allow_null=False, choices=(
        ('is_sell', '在售'), ('preview', '预览'), ('not_enough', '库存不足'), ('not_sell', '下架')
    ))

    delivery_method = serializers.ListField(allow_empty=True, child=serializers.ChoiceField(
        choices=Goods.METHOD, label='Delivery method'), label='配送方式', required=False)

    class Meta:
        model = Goods
        fields = generate_fields(Goods, add=['create_poster'])

    def validate(self, attrs):
        if attrs.get('groupbuy') and not attrs.get('groupbuy_info'):
            raise serializers.ValidationError('请为拼团商品设置拼团信息')
        if not attrs.get('fictitious', False) and not attrs.get('delivery_method'):
            raise serializers.ValidationError('请选择配送方式')
        return attrs

    def validate_delivery_method(self, value):
        if 'own' in value and 'express' in value:
            raise serializers.ValidationError('配送方式不能同时设置快递和自配送')
        return value

    def validate_status(self, value):
        status = None
        for k, v in Goods.status_dict.items():
            if v == value:
                status = k
                break
        if status == None:
            raise serializers.ValidationError('商品状态错误')
        return status

    def get_create_poster(self, instance):
        return reverse('goods-poster', (instance.id,), request=self.context.get('request'))

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res['status'] = Goods.status_dict.get(res['status'])
        return res


@version_based_cache
class BannerSerializer(serializers.HyperlinkedModelSerializer):
    image = obj(allow_null=True, label='封面图', queryset=File.objects.all(), required=False,
                view_name='file-detail', serializer_class=FileSerializer)
    goods = obj(allow_null=True, label='商品', queryset=Goods.objects.all(), required=False,
                view_name='goods-detail', serializer_class=GoodsSerializer)

    class Meta:
        model = Banner
        fields = generate_fields(Banner, add=[])


@version_based_cache
class SearchSerializer(serializers.Serializer):
    keyword = serializers.CharField(label='关键字', required=True, allow_null=False)
    lat = serializers.FloatField(label='纬度', allow_null=True, required=False)
    lng = serializers.FloatField(label='经度', allow_null=True, required=False)

    def save(self, **kwargs):
        keyword = self.validated_data.get('keyword')
        lat = self.validated_data.get('lat')
        lng = self.validated_data.get('lng')
        from_location = {'lat': lat, 'lng': lng} if lat and lng else None
        shops = Shop.get_shop_list(from_location)
        result = []
        if not shops:
            return result
        for shop in shops:
            goods = Goods.objects.exclude(Q(is_template=True) | Q(category__is_active=False)).filter(
                status=Goods.IS_SELL, shop__id=shop.get('id')). \
                filter(
                Q(name__icontains=keyword) | Q(category__name__icontains=keyword) | Q(goods_brief__icontains=keyword))
            if goods:
                shop['goods'] = GoodsSerializer(goods[:3], many=True, context=self.context).data
                result.append(shop)
        return result


@version_based_cache
class GoodsListSerializer(serializers.HyperlinkedModelSerializer):
    ord_goods = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        allow_null=True,
        label='普通商品',
        queryset=OrdGoods.objects.all(),
        view_name='ordgoods-detail',
        serializer_class=OrdGoodsSerializer,
        is_save=True
    )
    repl_goods = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        allow_null=True,
        label='积分商品',
        queryset=ReplGoods.objects.all(),
        view_name='replgoods-detail',
        serializer_class=ReplGoodsSerializer,
        is_save=True
    )
    groupbuy_info = ObjectHyperlinkedRelatedField(
        allow_empty=False, required=False, allow_null=True, label='拼团信息',
        queryset=GroupBuyInfo.objects.all(), view_name='groupbuyinfo-detail',
        serializer_class=GroupBuyInfoSeriazlizers, is_save=True
    )
    category = obj(allow_null=True, label='商品分类', queryset=GoodsCategory.objects.all(), required=False,
                   view_name='goodscategory-detail', serializer_class=GoodsCategorySerializer)
    banner = serializers.SerializerMethodField()

    class Meta:
        model = Goods
        fields = generate_fields(Goods, add=[],
                                 remove=['image', 'video', 'poster', 'is_template',
                                         'delivery_method', 'shop', 'attach', 'detail'])

    def get_banner(self, instance):
        banner = instance.banner.first()
        if banner:
            return [ImagesSerializer(instance=banner, context=self.context).data]
        return None

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res['status'] = Goods.status_dict.get(res['status'])
        return res


@version_based_cache
class GoodsListNewSerializer(serializers.HyperlinkedModelSerializer):
    ord_goods = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        allow_null=True,
        label='普通商品',
        queryset=OrdGoods.objects.all(),
        view_name='ordgoods-detail',
        serializer_class=OrdGoodsSimplifiedSerializer,
        is_save=True
    )
    repl_goods = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        allow_null=True,
        label='积分商品',
        queryset=ReplGoods.objects.all(),
        view_name='replgoods-detail',
        serializer_class=ReplGoodsSerializer,
        is_save=True
    )
    groupbuy_info = ObjectHyperlinkedRelatedField(
        allow_empty=False,
        required=False,
        allow_null=True, label='拼团信息',
        queryset=GroupBuyInfo.objects.all(),
        view_name='groupbuyinfo-detail',
        serializer_class=GroupBuyInfoSeriazlizers,
        is_save=True
    )
    category = obj(
        allow_null=True,
        label='商品分类',
        queryset=GoodsCategory.objects.all(),
        required=False,
        view_name='goodscategory-detail',
        serializer_class=GoodsCategorySimplifiedSerializer
    )

    banner = serializers.SerializerMethodField()

    def get_banner(self, instance):
        banner = instance.banner.first()
        if banner:
            return [ImagesSerializer(instance=banner, context=self.context).data]
        return None

    class Meta:
        model = Goods
        fields = generate_fields(
            Goods,
            add=[],
            remove=['image', 'video', 'poster', 'is_template', 'delivery_method', 'shop', 'attach', 'detail']
        )

    def to_representation(self, instance):
        res = super().to_representation(instance)
        res['status'] = Goods.status_dict.get(res['status'])
        return res

class SearchGoodsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Goods
        fields = ('id', 'name', 'url')
