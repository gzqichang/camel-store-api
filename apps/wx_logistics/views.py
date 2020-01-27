from rest_framework.decorators import action
from rest_framework import (
    views,
    mixins,
    status,
    viewsets,
    generics,
    response,
    exceptions,
    permissions,
)

from quser.permissions import CURDPermissionsOrReadOnly

from . import serializers, filters
from .models import DeliveryAccount, DeliveryPrinter, Sender, DeliveryRecords
from .logistics import wx_logistics, AccountAction, PrinterAction


class DeliveryAccountViewSet(mixins.ListModelMixin,
                             mixins.CreateModelMixin,
                             mixins.DestroyModelMixin,
                             viewsets.GenericViewSet,
                             ):
    queryset = DeliveryAccount.objects.all().order_by('id')
    serializer_class = serializers.DeliveryAccountSerializer
    permission_classes = (CURDPermissionsOrReadOnly, )
    filterset_class = filters.DeliveryAccountFilter

    def list(self, request, *args, **kwargs):
        current_account = self.filter_queryset(self.get_queryset())
        current_account_set = list(map(lambda x: f'{x.biz_id}{x.delivery_id}',
                                       current_account))

        if not current_account.exists():
            return response.Response([])

        try:
            all_account = wx_logistics.get_all_account()
        except (Exception,) as e:
            raise exceptions.APIException(e)
        else:
            res = list(filter(
                lambda x: f"{x['biz_id']}{x['delivery_id']}" in current_account_set,
                all_account.get('list', []),
            ))

        return response.Response(res)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = {
            'biz_id': serializer.validated_data['biz_id'],
            'delivery_id': serializer.validated_data['delivery_id'],
            'password': serializer.validated_data['password'],
            'remark_content': serializer.validated_data['remark_content'],
        }

        self.handle_wx_actions(AccountAction.Bind.value, data)

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        data = {
            'biz_id': instance.biz_id,
            'delivery_id': instance.delivery_id,
            'password': instance.password,
            'remark_content': '',
        }

        self.handle_wx_actions(AccountAction.Unbind.value, data)

        return super().destroy(request, *args, **kwargs)

    def handle_wx_actions(self, action, data):
        try:
            wx_logistics.bind_account(
                action=action,
                biz_id=data['biz_id'],
                delivery_id=data['delivery_id'],
                password=data['password'],
                remark_content=data['remark_content'],
            )
        except (Exception,) as e:
            raise exceptions.APIException(e)
        else:
            pass

    @action(methods=['post'], detail=True)
    def status(self, request, pk):
        instance = self.get_object()
        is_active = request.data.get('is_active', True)

        if isinstance(instance, DeliveryAccount):
            instance.is_active = is_active
            instance.save()
            return self.serializer_class(instance, context={'request': request})

        return response.Response(
            '修改失败',
            status=status.HTTP_400_BAD_REQUEST,
        )


class AllDeliveryView(views.APIView):
    def get(self, request, *args, **kwargs):
        try:
            all_delivery = wx_logistics.get_all_delivery()
        except (Exception,) as e:
            raise exceptions.APIException(e)
        else:
            return response.Response(all_delivery)


class DeliveryOrderView(generics.GenericAPIView):
    serializer_class = serializers.DeliveryOrderSerializer
    permission_classes = (permissions.AllowAny, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        openid = serializer.validated_data['openid']
        delivery_id = serializer.validated_data['delivery_id']
        waybill_id = serializer.validated_data['waybill_id']

        try:
            res = wx_logistics.get_order(
                order_id=order_id,
                openid=openid,
                delivery_id=delivery_id,
                waybill_id=waybill_id,
            )
        except (Exception, ) as e:
            raise exceptions.APIException(e)
        else:
            pass

        return response.Response(res)


class CancelOrderView(generics.GenericAPIView):
    serializer_class = serializers.DeliveryOrderSerializer
    permission_classes = (permissions.IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        openid = serializer.validated_data['openid']
        delivery_id = serializer.validated_data['delivery_id']
        waybill_id = serializer.validated_data['waybill_id']

        try:
            wx_logistics.cancel_order(
                order_id=order_id,
                openid=openid,
                delivery_id=delivery_id,
                waybill_id=waybill_id,
            )
        except (Exception, ) as e:
            raise exceptions.APIException(e)
        else:
            pass

        return response.Response('物流运单已取消')


class DeliveryPathView(generics.GenericAPIView):
    serializer_class = serializers.DeliveryOrderSerializer
    permission_classes = (permissions.AllowAny, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data['order_id']
        openid = serializer.validated_data['openid']
        delivery_id = serializer.validated_data['delivery_id']
        waybill_id = serializer.validated_data['waybill_id']

        try:
            res = wx_logistics.get_path(
                order_id=order_id,
                openid=openid,
                delivery_id=delivery_id,
                waybill_id=waybill_id,
            )
        except (Exception, ) as e:
            raise exceptions.APIException(e)
        else:
            pass

        return response.Response(res)


class QuotaView(generics.GenericAPIView):
    serializer_class = serializers.QuotaSerializer
    permission_classes = (permissions.AllowAny, )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        biz_id = serializer.validated_data['biz_id']
        delivery_id = serializer.validated_data['delivery_id']

        try:
            res = wx_logistics.get_quota(
                biz_id=biz_id,
                delivery_id=delivery_id,
            )
        except (Exception, ) as e:
            raise exceptions.APIException(e)
        else:
            pass

        return response.Response(res)


class DeliveryPrinterViewSet(mixins.ListModelMixin,
                             mixins.CreateModelMixin,
                             mixins.DestroyModelMixin,
                             viewsets.GenericViewSet,
                             ):
    queryset = DeliveryPrinter.objects.all().order_by('id')
    serializer_class = serializers.DeliveryPrinterSerializer
    permission_classes = (CURDPermissionsOrReadOnly, )
    filterset_class = filters.DeliveryPrinterFilter

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = {
            'user': serializer.validated_data['user'],
            'tags': serializer.validated_data['tags'],
        }

        self.handle_wx_actions(PrinterAction.Bind.value, data)

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        data = {
            'user': instance.user,
            'tags': instance.tags,
        }

        self.handle_wx_actions(PrinterAction.Unbind.value, data)

        return super().destroy(request, *args, **kwargs)

    def handle_wx_actions(self, action, data):
        try:
            wx_logistics.update_printer(
                openid=data['user'].wx_app_openid,
                action=action,
                tagid_list=data['tags'],
            )
        except (Exception,) as e:
            raise exceptions.APIException(e)
        else:
            pass


class SenderViewSet(viewsets.ModelViewSet):
    queryset = Sender.objects.all().order_by('id')
    serializer_class = serializers.SenderSerializer
    permission_classes = (CURDPermissionsOrReadOnly,)
    filterset_class = filters.SenderFilter

    @action(methods=['post'], detail=True)
    def status(self, request, pk=None):
        instance = self.get_object()
        is_active = request.data.get('is_active', True)

        if isinstance(instance, Sender):
            instance.is_active = is_active
            instance.save()
            return response.Response('修改成功')

        return response.Response(
            '修改失败',
            status=status.HTTP_400_BAD_REQUEST,
        )


class AddOrderView(generics.GenericAPIView):
    serializer_class = serializers.AddOrderSerializer
    permission_classes = (permissions.IsAdminUser, )

    def update_deliveryaddress(self, receiver, order):
        """  发货时可能修改收件人地址，同步更新订单 """
        delivery_address = order.delivery_address
        delivery_address.address_info = f"{receiver.get('province')}{receiver.get('city')}{receiver.get('area')}{receiver.get('address')}"
        delivery_address.sign_name = receiver.get('name')
        delivery_address.mobile_phone = receiver.get('mobile')
        delivery_address.save()

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        data = serializer.save()
        try:
            from pprint import pprint
            pprint(data)
            res = wx_logistics.add_order(**data)
            instance = DeliveryRecords.objects.create(
                shop=validated_data["order"].shop,
                order=validated_data["order"],
                wx_order_id=res.get("order_id"),
                delivery_id=validated_data["delivery_id"],
                waybill_id=res.get("waybill_id"),
                waybill_data=res.get("waybill_data")
            )
            instance.items.add(*validated_data['items'])
            for i in validated_data['items']:
                i.express_num = res.get("waybill_id", '')
                i.express_company = validated_data.get("delivery_name", '')
                i.save()
            self.update_deliveryaddress(validated_data['receiver'], validated_data['order'])
        except (Exception,) as e:
            raise exceptions.APIException(e)
        return response.Response(res)