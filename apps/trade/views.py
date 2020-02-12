from decimal import Decimal
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView, status
from rest_framework.response import Response
from rest_framework import viewsets, mixins, decorators, generics
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.conf import settings
from quser.permissions import CURDPermissions, CURDPermissionsOrReadOnly

from wx_pay.unified import WxPayOrderClient
from wx_pay.query import WxPayQueryClient
from wx_pay.utils import dict_to_xml
from wxapp.permissions import OnlyWxUser
from apps.account.models import RechargeRecord
from apps.utils.logistics import logistics
from apps.utils.company import company
from apps.utils.parser import TextTypeXMLParser

from .models import UserAddress, Express, generate_order_sn, Orders, Items, \
    DeliveryAddress, GoodsBackup, ExportDelivery
from .serializers import UserAddressSerializers, ExpressSerializers, AdjustAmountSerializers, OrdersSerializers, \
    ItemsSerializers, DeliveryAddressSerializers, ExportBatchDeliverySerializer, QueryBatchDeliverySerializer
from .buy_serializers import CartBuySerializers, ReplaceGoodsSerializers
from .filters import AddressFilter, OrdersFilter, ItemsFilter
from .utils import item_send, item_confirm_receipt, order_cancel, order_pay, arrive, order_done, parseAddress
from .gen_batch_xlsx import gen_batch_xlsx


class UserAddressViewSet(viewsets.ModelViewSet):
    serializer_class = UserAddressSerializers
    queryset = UserAddress.objects.all()
    permission_classes = (OnlyWxUser,)
    filterset_class = AddressFilter

    def get_queryset(self):
        self.queryset = UserAddress.objects.filter(user=self.request.user)
        return self.queryset


#普通商品下单
class CartBuyView(APIView):
    """
    post:
    {\n
        "goodsitems": [
                  {
                    "goods": 1,
                    "gtype": 1,
                    "num": 1,
                    "delivery_method": "express",   配送方式
                    "share_user_id": '分享用户的user_id',
                    "attach": null
                  },
                  {
                    "goods": 2,
                    "gtype": 3,
                    "num": 2,
                    "delivery_method": "express",  配送方式
                    "share_user_id": '分享用户的user_id',
                    "attach": null
                  },
            ]
        "address": 1,
        "remark": "备注",
        "use_wallet": true,
        "shop": 1,
        "invoice": {
            "invoice_type": "",
            "title": "",
            "taxNumber": "",
            "companyAddress": "",
            "telephone": "",
            "bankName": "",
            "bankAccount": ""
        },
        "is_pt": true,    # 是否是参团的订单，
        "groupbuy": 1   # 团的id，
        "fictitious": false,     是否是虚拟商品的订单
    }
    """
    serializer_class = CartBuySerializers
    permission_classes = (OnlyWxUser,)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(instance)


class Wechatpay(APIView):
    '''
    {\n
        "order_sn": "1241241241",
        "type": "order"  or suborder
    }
    '''
    permission_classes = (OnlyWxUser,)

    def post(self, request, *args, **kwargs):
        user = request.user
        openid = request.data.get("openid", user.wx_app_openid)
        order_sn = request.data.get("order_sn", "")
        order_type = request.data.get("type", "order")
        if not openid or not order_sn:
            return Response("请求参数错误", status.HTTP_400_BAD_REQUEST)
        extra_data = {"openid": openid, }
        instance = None
        attach = 'buy_order'
        instance = Orders.objects.get(order_sn=order_sn, status=Orders.PAYING)
        if not instance:
            return Response('订单异常', status.HTTP_400_BAD_REQUEST)
        res = {'status': 200}
        if instance.real_amount == Decimal('0'):  # 订单实付金额为0(即钱包余额足够支付订单)时，直接支付，不需要再使用微信支付。
            order_pay(instance)
            order = {}
            res.update({'info': order})
            return Response(res)
        order = WxPayOrderClient().create(
            channel="wx_lite",  # 小程序发起支付的标识
            out_trade_no=order_sn,
            total_fee=int(instance.real_amount * 100),  # money 单位为分
            client_ip=request.META['REMOTE_ADDR'],
            fee_type="CNY",
            attach=attach,
            body=getattr(settings, 'SHOP_NAME'),
            notify_url=reverse('paycallback', request=request),
            **extra_data
        )
        res.update({'info': order})
        return Response(res)


# 支付结果通知路由
class PayCallback(APIView):
    parser_classes = (TextTypeXMLParser,)
    permission_classes = []

    def post(self, request, *args, **kwargs):
        def clear_data(data):
            for key in ('total_fee', 'settlement_total_fee', 'cash_fee', 'coupon_fee', 'coupon_count'):
                if key in data:
                    data[key] = int(data[key])

        data = request.data
        appid = data.get("appid")
        transaction_id = data.get("transaction_id")
        out_trade_no = data.get("out_trade_no")
        attach = data.get("attach")

        result = WxPayQueryClient().query(appid, transaction_id, out_trade_no)
        clear_data(result)
        if result.get("trade_state") == "SUCCESS":
            if attach == 'buy_order':
                instance = Orders.objects.get(order_sn=out_trade_no)
                order_pay(instance, transaction_id)
            elif attach == 'recharge':
                instance = RechargeRecord.objects.get(rchg_no=out_trade_no, )
                instance.recharge(trade_no=transaction_id)
        # print('支付完成')
        return HttpResponse(dict_to_xml({"return_code": "SUCCESS"}), content_type='application/xml')


# 主动拉取支付结果
class PullPayResult(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        pay_type = request.query_params.get('pay_type', None)
        order_sn = request.query_params.get('order_sn', None)

        if pay_type == 'buy_order':
            instance = get_object_or_404(Orders, order_sn=order_sn, status=Orders.PAYING)
        elif pay_type == 'recharge':
            instance = get_object_or_404(RechargeRecord, rchg_no=order_sn, status=RechargeRecord.UNPAID)
        else:
            return Response('Invalide pay type.', status=status.HTTP_400_BAD_REQUEST)

        if not order_sn:
            return Response('order_sn can not be None.', status=status.HTTP_400_BAD_REQUEST)

        def clear_data(data):
            for key in ('total_fee', 'settlement_total_fee', 'cash_fee', 'coupon_fee', 'coupon_count'):
                if key in data:
                    data[key] = int(data[key])

        appid = settings.WX_PAY_WXA_APP_ID
        transaction_id = instance.trade_no
        out_trade_no = order_sn

        result = WxPayQueryClient().query(appid, transaction_id, out_trade_no)
        clear_data(result)
        state = result.get("trade_state")
        if state == "SUCCESS":
            if pay_type == 'buy_order':
                order_pay(instance, transaction_id)
            elif pay_type == 'recharge':
                instance.recharge(trade_no=result['transaction_id'])
            return Response('pulled', status=status.HTTP_200_OK)

        return Response(f'pulled, trade_state{state}', status=status.HTTP_424_FAILED_DEPENDENCY)

# 轮询取消超时未付款订单路由
class CancelOrder(APIView):
    permission_classes = []
    throttle_scope = 'cancel_order'

    def get(self, request, *args, **kwargs):
        orders = Orders.objects.filter(status=Orders.PAYING, flag_time__lte=timezone.now())
        if not orders:
            return Response('success', status=status.HTTP_200_OK)
        for order in orders:
            order_cancel(order)
        return Response('success', status=status.HTTP_200_OK)


# 轮询自动收货路由
class ConfirmReceipt(APIView):
    permission_classes = []
    throttle_scope = 'confirm_receipt'

    def get(self, request, *args, **kwargs):
        # items = GoodsItems.objects.filter(status=GoodsItems.RECEIVING, flag_time__lte=datetime.now())
        orders = Orders.objects.filter(model_type__in=[Orders.ORD, Orders.REPL], status=Orders.RECEIVING, flag_time__lte=timezone.now())
        items = Items.objects.filter(send_type=Items.RECEIVING, flag_time__lte=timezone.now())
        if not orders and not items:
            return Response('success', status=status.HTTP_200_OK)
        for order in orders:
            order_done(order)
        for item in items:
            item_confirm_receipt(item)
        return Response('success', status=status.HTTP_200_OK)


class ExpressViewSet(viewsets.ModelViewSet):
    queryset = Express.objects.get_queryset().order_by('id')
    serializer_class = ExpressSerializers
    permission_classes = [CURDPermissions, ]

    @decorators.action(methods=['GET', ], detail=False, permission_classes=[])
    def express_list(self, request, *args, **kwargs):
        return Response(company)


#积分换购下单
class ReplaceGoodsView(APIView):
    """
   post:
    {\n
    	"goods": 1,
    	"gtype": 7,
    	"num": 1,
        "address": 1,
        "use_wallet": true,
        "remark": "备注",
    	"delivery_method": "express",  配送方式
    	"shop": 1,
    	"attach": null,
    	"fictitious": false,     是否是虚拟商品的订单
    }
    """
    serializer_class = ReplaceGoodsSerializers
    permission_classes = (OnlyWxUser,)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(instance)


class NotDeleteViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    pass


class OnlyReadViewSet(mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet):
    pass


class OrdersViewSet(OnlyReadViewSet):
    serializer_class = OrdersSerializers
    queryset = Orders.objects.all()
    permission_classes = [IsAuthenticated, ]
    filterset_class = OrdersFilter

    def get_queryset(self):

        if self.action == 'retrieve':
            # 查看详情时不分是否在拼团中
            return Orders.objects.all()
        if getattr(self.request.user, 'is_wechat', False):
            return Orders.objects.filter(user=self.request.user).exclude(status=Orders.PAYING, is_pt=True)
        if getattr(self.request.user, 'is_staff', False):
            return Orders.all_order_by_status()
        return Orders.objects.none()

    @decorators.action(methods=['GET', ], detail=False, permission_classes=[OnlyWxUser, ])
    def statistic(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset()
        groupbuy = 0
        for i in queryset.filter(status=Orders.GROUPBUY):
            groupbuy += i.pt_group.count()
        paying = queryset.filter(status=Orders.PAYING).count()
        has_paid = queryset.filter(status=Orders.HAS_PAID).count()
        serving = queryset.filter(status=Orders.SERVING).count()
        receiving = queryset.filter(status=Orders.RECEIVING).count()
        return Response({'paying': paying, 'groupbuy': groupbuy, 'has_paid': has_paid,
                         'serving': serving, 'receiving': receiving})

    # 微信用户确认收货
    @decorators.action(methods=['POST', ], detail=True, permission_classes=[OnlyWxUser, ])
    def confirm(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        if instance.status != Orders.RECEIVING or instance.model_type not in [Orders.ORD, Orders.REPL]:
            return Response('订单状态错误,请稍后重试', status=status.HTTP_400_BAD_REQUEST)
        if instance.user != user:
            return Response('非用户所购商品', status=status.HTTP_400_BAD_REQUEST)
        order_done(instance)
        return Response('已收货')

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[OnlyWxUser, ])
    def cancel(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        if instance.status != Orders.PAYING:
            return Response('订单已支付或关闭，不可取消', status=status.HTTP_400_BAD_REQUEST)
        if instance.user != user:
            return Response('请取消自己的订单', status=status.HTTP_400_BAD_REQUEST)
        order_cancel(instance)
        return Response('订单已关闭')

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[CURDPermissions, ],
                       serializer_class=AdjustAmountSerializers)
    def adjust(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != instance.PAYING:
            return Response('订单已支付或关闭, 不能修改支付金额', status=status.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        real_amount = serializer.save()
        instance.real_amount = real_amount
        instance.order_sn = generate_order_sn(instance.user)
        instance.save()
        return Response({'real_amount': instance.real_amount, 'order_sn': instance.order_sn})


class ItemsViewSet(NotDeleteViewSet):
    serializer_class = ItemsSerializers
    queryset = Items.objects.all()
    permission_classes = [IsAuthenticated, ]
    filterset_class = ItemsFilter

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff'):
            return Items.objects.all()
        if getattr(self.request.user, 'is_wechat', False):
            return Items.objects.filter(order__user=self.request.user)
        return Items.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().filter(order__is_pt=False)
        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @decorators.action(['POST'], detail=True, permission_classes=[IsAdminUser, ])
    def send(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.send_type != instance.SENDING:
            return Response('状态已改变，请刷新确认', status=status.HTTP_400_BAD_REQUEST)
        item_send(instance)
        return Response('已发货')

    @decorators.action(['POST'], detail=True, permission_classes=[IsAdminUser, ])
    def arrive(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.goods_backup.delivery_method == 'express':
            return Response('快递配送无法送达', status=status.HTTP_400_BAD_REQUEST)
        if instance.send_type != instance.RECEIVING:
            return Response('订单状态错误', status=status.HTTP_400_BAD_REQUEST)
        arrive(instance)
        return Response('本期商品已送达/已提件')

    @decorators.action(['POST'], detail=True, permission_classes=[OnlyWxUser, ])
    def confirm(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        if instance.order.user != user:
            return Response('订单错误', status=status.HTTP_400_BAD_REQUEST)
        if instance.goods_backup.delivery_method == 'express' and instance.send_type == instance.RECEIVING:
            item_confirm_receipt(instance)
            return Response('已收货')
        if instance.goods_backup.delivery_method in ['own', 'buyer'] and instance.send_type == instance.ARRIVE:
            item_confirm_receipt(instance)
            return Response('已收货')
        return Response('订单状态错误', status=status.HTTP_400_BAD_REQUEST)

    # 查看物流
    @decorators.action(methods=['GET', ], detail=True, permission_classes=[IsAuthenticated, ])
    def logistics(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.express_company or not instance.express_num:
            return Response('没有快递单号和快递公司', status=status.HTTP_400_BAD_REQUEST)
        res_status, res_info = logistics.get_Logistics_info(instance.express_company, instance.express_num)
        if res_status != 200:
            return Response(res_info, status=status.HTTP_400_BAD_REQUEST)
        res_info.update({'address': instance.order.delivery_address.address_info})
        return Response(res_info)


class DeliveryAddressViewSet(NotDeleteViewSet):
    serializer_class = DeliveryAddressSerializers
    queryset = DeliveryAddress.objects.all()
    permission_classes = [IsAdminUser, ]


class ExportBatchDeliveryView(generics.GenericAPIView):
    serializer_class = ExportBatchDeliverySerializer
    permission_classes = (IsAdminUser, )

    def get_order_data(self, order_ids):
        data = []
        orders = Orders.objects.filter(id__in=order_ids)

        if not orders.exists():
            return []

        for order in orders:
            if not (order.delivery_address and order.shop):
                continue

            receiver = order.delivery_address
            receiver_ = parseAddress(order.delivery_address.address_info)
            sender = order.shop
            remarks = order.remark
            goods_name = []

            for item in order.goods_backup.all():
                if item.delivery_method == GoodsBackup.EXPRESS:
                    goods_name.append(f'{item.goods_name}({item.gtype_name})*{item.num}')

            if goods_name:
                data.append({
                    'sender_name': sender.name,
                    'sender_province': sender.province,
                    'sender_city': sender.city,
                    'sender_area': sender.district,
                    'sender_address': sender.detail,
                    'sender_phone': sender.service_phone,

                    'receiver_name': receiver.sign_name,
                    'receiver_province': receiver_[0],
                    'receiver_city': receiver_[1],
                    'receiver_area': receiver_[2],
                    'receiver_address': receiver_[3],
                    'receiver_phone': receiver.mobile_phone,
                    'receiver_insured': '0',
                    'receiver_full_address': receiver.address_info,

                    'order_sn': order.order_sn,
                    'goods_name': ', '.join(goods_name),
                    'goods_weight': '1',
                    'goods_remarks': remarks,
                    'company_name': '',
                })

        return data

    def count_exports(self, order_ids):
        for oid in order_ids:
            order, created = ExportDelivery.objects.get_or_create(
                order_id=oid,
                defaults={'export_count': 0},
            )
            if created:
                order.export_count = 1
            else:
                order.export_count += 1
            order.save()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        orders = serializer.validated_data['orders']
        delivery = serializer.validated_data['delivery']

        order_data = self.get_order_data(orders)
        file = gen_batch_xlsx(delivery, order_data)

        self.count_exports(orders)

        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        # content_type = 'application/vnd.ms-excel'

        # response = StreamingHttpResponse(file, content_type=content_type)
        response = HttpResponse(content=file, content_type=content_type)
        response['Content-Disposition'] = 'attachment; filename=express.xlsx'
        return response


class QueryBatchDeliveryView(generics.GenericAPIView):
    serializer_class = QueryBatchDeliverySerializer
    permission_classes = (IsAdminUser, )

    def get_order_data(self, order_ids):
        data = []
        exp = ExportDelivery.objects.filter(order_id__in=order_ids)

        if not exp.exists():
            return []

        for e in exp:
            goods_name = []

            for item in e.order.goods_backup.all():
                if item.delivery_method == GoodsBackup.EXPRESS:
                    goods_name.append(f'{item.goods_name}({item.gtype_name})*{item.num}')

            data.append({
                'name': ', '.join(goods_name),
                'order': e.order.pk,
                'count': e.export_count,
            })

        return data

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        orders = serializer.validated_data['orders']

        order_data = self.get_order_data(orders)

        return Response(order_data)
