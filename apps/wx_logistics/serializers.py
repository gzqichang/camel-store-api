from rest_framework import serializers

from qapi.utils import generate_fields
from apps.utils.file_uri import file_uri
from .models import DeliveryPrinter, DeliveryAccount, Sender, DeliveryRecords


class DeliveryAccountSerializer(serializers.ModelSerializer):
    remark_content = serializers.CharField(
        label='备注内容',
        write_only=True,
        required=False,
        default='',
    )

    class Meta:
        model = DeliveryAccount
        fields = generate_fields(model, add=['remark_content'])


class DeliveryOrderSerializer(serializers.Serializer):
    order_id = serializers.CharField(label='订单ID')
    openid = serializers.CharField(label='用户openid', required=False, default=None)
    delivery_id = serializers.CharField(label='快递公司ID')
    waybill_id = serializers.CharField(label='运单ID')


class QuotaSerializer(serializers.Serializer):
    delivery_id = serializers.CharField(label='快递公司ID')
    biz_id = serializers.CharField(label='快递公司客户编码')


class DeliveryPrinterSerializer(serializers.ModelSerializer):
    nickname = serializers.SerializerMethodField()
    tag_list = serializers.SerializerMethodField()
    tagid_list = serializers.ListField(
        label='打印员面单打印权限',
        write_only=True,
        required=False,
        default=[],
    )

    def get_tag_list(self, instance):
        return instance.tags.split(',')

    def get_nickname(self, instance):
        return instance.user.nickname

    class Meta:
        model = DeliveryPrinter
        fields = generate_fields(
            model, add=['tagid_list', 'tag_list', 'nickname'], remove=['tags'])

    def validate(self, attrs):
        shop = attrs.get('shop')
        tagid_list = attrs.pop('tagid_list', [])

        if shop and shop.id not in tagid_list:
            tagid_list.append(shop.id)

        attrs['tags'] = ','.join(list(map(str, tagid_list)))

        return attrs


class SenderSerializer(serializers.HyperlinkedModelSerializer):
    shop_name = serializers.SerializerMethodField()

    def get_shop_name(self, instance):
        return instance.shop.name

    class Meta:
        model = Sender
        fields = generate_fields(model, add=['shop_name'])


class AddOrderSerializer(serializers.ModelSerializer):

    sender = serializers.PrimaryKeyRelatedField(label='发货人信息', queryset=Sender.objects.all(), required=True, allow_null=False)
    service_name = serializers.CharField(label='服务类型', max_length=20, required=True, allow_null=False)
    service_type = serializers.IntegerField(label='服务类型id')
    biz_id = serializers.CharField(label='客户(现付)编码', max_length=20, required=True, allow_null=False)
    count = serializers.IntegerField(label='数量')
    space_x = serializers.IntegerField(label='包裹长度')
    space_y = serializers.IntegerField(label='包裹宽度')
    space_z = serializers.IntegerField(label='包裹高度')
    weight = serializers.FloatField(label='总重量')
    custom_remark = serializers.CharField(label='备注', style={'base_template': 'textarea.html'}, required=False, allow_null=True)
    expect_time = serializers.IntegerField(label='预约收件时间', required=False, allow_null=True)
    receiver = serializers.JSONField(label='收件人信息')
    delivery_name = serializers.CharField(label='快递公司名称', max_length=50, required=True, allow_null=False)

    class Meta:
        model = DeliveryRecords
        fields = ('items', 'order', 'delivery_id', 'sender', 'service_name', 'service_type', 'count', 'space_x',
                  'space_y', 'space_z', 'weight', 'custom_remark', 'expect_time', 'biz_id', 'receiver', 'delivery_name')

    def validate_receiver(self, data):
        if not data.get('address', None) or not data.get('area', None) or not data.get('city', None) or not data.get('province', None):
            raise serializers.ValidationError('请完整输入收件人详细地址')
        if not data.get('mobile', None):
            raise serializers.ValidationError('请输入收件人手机号')

        if not data.get('name', None):
            raise serializers.ValidationError('请输入收件人姓名')
        return data

    def validate(self, attrs):
        items = attrs['items']
        for i in items:
            if i.order != attrs['order']:
                raise serializers.ValidationError('发货商品不属于同一订单')
        if attrs["delivery_id"] == 'SF' and not attrs.get('expect_time', None):
            raise serializers.ValidationError('顺丰快递预约取件时间必填')

        return attrs

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass

    def cargo(self, validated_data):
        detail_list = [{"count": i.goods_backup.num,
                        "name": f"{i.goods_backup.goods_name}-{i.goods_backup.gtype_name}*{i.goods_backup.num}"} for i
                       in validated_data['items']]
        return {"count": validated_data["count"],
                "weight": validated_data["weight"],
                "space_x": validated_data["space_x"],
                "space_y": validated_data["space_y"],
                "space_z": validated_data["space_z"],
                "detail_list": detail_list}

    def receiver_info(self, validated_data):
        receiver = validated_data['receiver']
        receiver.update({"country": "中国"})
        return receiver

    def sender_info(self, sender):
        sender_ = {"name": sender.name,
                  "company": sender.company,
                  "post_code": sender.post_code,
                  "country": sender.country,
                  "province": sender.province,
                  "city": sender.city,
                  "area": sender.area,
                  "address": sender.address,
                  }
        if sender.tel:
            sender_.update({"mobile": sender.tel})
        if sender.mobile:
            sender_.update({"mobile": sender.mobile})
        return sender_

    def goods_info(self, items):
        goods_info = {
            "goods_count": sum([i.goods_backup.num for i in items]),
            "goods_name": items[0].goods_backup.goods_name,
            "img_url": file_uri(self.context.get('request'), items[0].goods_backup.g_image),
            "wxa_path": f"pages/util/index?oid={items[0].order.id}"
        }
        return goods_info

    def save(self, **kwargs):
        validated_data = self.validated_data
        items = validated_data['items']
        order = validated_data['order']
        sender = validated_data['sender']
        validated_data["wx_order_id"] = f"{order.order_sn}{items[0].id}"   # 物流单需要一个唯一的订单号，采用订单加子订单第一个的id组成
        data = {
            "add_source": 0,
            "biz_id": validated_data["biz_id"],
            "cargo": self.cargo(validated_data),
            "delivery_id": validated_data["delivery_id"],
            "insured": {"insured_value": 0, "use_insured": 0},
            "openid": order.user.wx_app_openid,
            "order_id": validated_data["wx_order_id"],
            "receiver": self.receiver_info(validated_data),
            "sender": self.sender_info(sender),
            "service": {"service_name": validated_data["service_name"], "service_type": validated_data["service_type"]},
            "shop": self.goods_info(items),
            "custom_remark": validated_data.get("custom_remark", ''),
            "tagid": order.shop.id,
        }
        if validated_data["delivery_id"] == 'SF':
            data['expect_time'] = validated_data['expect_time']
        return data



