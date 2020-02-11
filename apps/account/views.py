from decimal import Decimal
from django.db.models import Count, Sum
from django.conf import settings
from rest_framework import viewsets, mixins, decorators
from rest_framework.response import Response
from rest_framework.views import APIView, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.reverse import reverse
from wxapp.models import WxUser
from wxapp.permissions import OnlyWxUser
from wx_pay.unified import WxPayOrderClient
from qapi.mixins import RelationMethod
from apps.config.models import BoolConfig

from .serializers import WxUserSerializer, WxUserSavePhoneSerializer, WxUserAccountLogSerializer, \
    WithdrawSerializer, WithdrawCreateSerializer, WithdrawOperationLogSerializer, RechargeCreateSerializer, \
    RechargeRecordSerializer, WxUserCreditLogSerializer
from .models import WxUserAccountLog, Withdraw, WithdrawOperationLog, RechargeRecord, WxUserCreditLog
from .filters import WxUserFilter, WxUserAccountLogFilter, WithdrawFilter, RechargeRecordFilter, WxUserCreditLogFilter

# Create your views here.


class WxUserInfoViewSet(viewsets.ReadOnlyModelViewSet, mixins.CreateModelMixin, RelationMethod):
    """
        get: admin 获取微信用户列表
             微信用户获取自己的信息
        post: 保存更新微信用户的信息
        get: /api/wxuserinfo/referrals/?order=xxxx 获取微信用户的帮手
             默认按照时间用户的加入时间倒序排序
        get:/api/wxuserinfo/<pk>/referrals_list/ 获取该微信用户的帮手
    """
    serializer_class = WxUserSerializer
    queryset = WxUser.objects.all().order_by('-date_joined')
    permission_classes = (IsAuthenticated,)
    filterset_class = WxUserFilter

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        if getattr(user, 'is_wechat', False):
            return queryset.filter(id=user.id)
        if user.is_staff:
            return queryset.exclude(nickname='')
        return queryset.none()

    def list(self, request, *args, **kwargs):
        if getattr(request.user, 'is_wechat', False):
            return Response(self.get_serializer(request.user).data)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """ 重写, 前端只需要 post """
        if getattr(request.user, 'is_wechat', False):
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(dict(code=403, message='仅限创建微信用户信息'), status=status.HTTP_403_FORBIDDEN)

    @decorators.action(methods=['GET', ], detail=False)
    def referrals(self, request, *args, **kwargs):
        user = request.user
        if getattr(request.user, 'is_wechat', False):
            res = []
            for r in request.user.relations.all():
                res.append({'avatar_url': r.referral.avatar_url, 'nickname': r.referral.nickname,
                            'create_time': r.create_time})
            return Response(res)
        return Response(dict(code=403, message='仅限微信用户使用此接口'), status=status.HTTP_403_FORBIDDEN)

    @decorators.action(methods=['GET', 'POST'], detail=False, permission_classes=(OnlyWxUser,))
    def phone(self, request, *args, **kwargs):
        if request.method == 'GET':
            info = getattr(request.user, 'info', None)
            has_phone = False
            phone = ''
            if info:
                phone = info.phone
                has_phone = bool(phone)
            return Response(dict(has_phone=has_phone, phone=phone))
        elif request.method == 'POST':
            serializer = WxUserSavePhoneSerializer(data=request.data, context=dict(request=request))
            serializer.is_valid(raise_exception=True)
            phone_info = serializer.save()
            return Response(phone_info)
        else:
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @decorators.action(methods=['GET', ], detail=True)
    def referrals_list(self, request, *args, **kwargs):
        instance = self.get_object()
        referral_ids = instance.relations.all().values_list('referral')
        referrals = self.queryset.filter(pk__in=referral_ids) \
            .annotate(referral_count=Count('relations'))
        serializer = self.get_serializer(referrals, many=True)
        return Response(serializer.data)

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[IsAdminUser, ])
    def testers(self, request, *args, **kwargs):
        '''
        修改是否为测试人员\n
        post:
        {\n
            testers: true (or false  false为否  true为是)
        }
        '''
        instance = self.get_object()
        testers = request.data.get('testers', 'false')
        if testers == 'true':
            instance.testers = True
        elif testers == 'false':
            instance.testers = False
        instance.save()
        return Response('修改完成')

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[IsAdminUser])
    def upload_perm(self, request, *args, **kwargs):
        instance = self.get_object()
        upload_perm = request.data.get('upload_perm', 'false')
        if upload_perm == 'true':
            instance.upload_perm = True
        elif upload_perm == 'false':
            instance.upload_perm = False
        instance.save()
        return Response('修改完成')

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[IsAdminUser, ])
    def rebate_right(self, request, *args, **kwargs):
        '''
        修改是否有推广返利的权利\n
        post:
        {\n
            rebate_right: true (or false  false为否  true为是)
        }
        '''
        instance = self.get_object()
        rebate_right = request.data.get('rebate_right', 'false')
        instance.rebate_right = rebate_right
        instance.save()
        return Response('修改完成')

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[IsAdminUser, ])
    def bonus_right(self, request, *args, **kwargs):
        '''
        修改是否有分销返佣的权利\n
        post:
        {\n
            bonus_right: true (or false  false为否  true为是)
        }
        '''
        instance = self.get_object()
        bonus_right = request.data.get('bonus_right', 'false')
        instance.bonus_right = bonus_right
        instance.save()
        return Response('修改完成')

    @decorators.action(methods=['GET', ], detail=True)
    def account_logs(self, request, *args, **kwargs):
        return self.detail_route_view(request, 'account_logs', WxUserAccountLogSerializer, filter_class=None)

    @decorators.action(methods=['GET', ], detail=True)
    def credit_logs(self, request, *args, **kwargs):
        return self.detail_route_view(request, 'credit_logs', WxUserCreditLogSerializer, filter_class=None)

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[IsAdminUser, ])
    def change_account(self, request, *args, **kwargs):
        '''
        post:
        {\n
            account: wallet (or credit)
            operation: add (or subtract)
            amount: "100" or (100)
        }
        '''
        admin_user = request.user
        if not admin_user.has_perm('account.change_account'):
            return Response('您没有修改权限', status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        amount = request.data.get('amount', 0)
        operation = request.data.get('operation', None)
        if Decimal(amount) < 0 or not operation:
            return Response('请输入正确的数值', status=status.HTTP_400_BAD_REQUEST)
        if request.data.get('account') == 'wallet':
            amount = Decimal(amount).quantize(Decimal('0.00'))
            if operation == 'add':
                WxUserAccountLog.record(instance, WxUserAccountLog.GIFT, balance=amount, remark='店铺赠送')
            elif operation == 'subtract':
                if amount > instance.account.asset + instance.account.recharge:
                    return Response('扣减金额大于用户钱包余额', status=status.HTTP_400_BAD_REQUEST)
                WxUserAccountLog.record(instance, WxUserAccountLog.DEDUCTION, remark='店铺扣减',
                    balance=amount if amount < instance.account.recharge else instance.account.recharge,
                    asset=0 if amount < instance.account.recharge else amount-instance.account.recharge)
        elif request.data.get('account') == 'credit':
            amount = int(amount)
            if operation == 'add':
                WxUserCreditLog.record(instance, WxUserCreditLog.GIFT, credit=amount, remark='店铺赠送')
            elif operation == 'subtract':
                if amount > instance.account.credit:
                    return Response('扣减积分大于用户积分', status=status.HTTP_400_BAD_REQUEST)
                WxUserCreditLog.record(instance, WxUserCreditLog.DEDUCTION, credit=amount, remark='店铺扣减')
        return Response('修改完成')


class AccountLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = WxUserAccountLogSerializer
    queryset = WxUserAccountLog.objects.all()
    permission_classes = (IsAdminUser,)
    filterset_class = WxUserAccountLogFilter

    # 微信用户只能看到自己的账户记录，管理员只看所有的状态为返利的记录
    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            filter_list = []
            if BoolConfig.get_bool('rebate_switch'):
                filter_list.append(WxUserAccountLog.ASSET)
            if BoolConfig.get_bool('bonus_switch'):
                filter_list.append(WxUserAccountLog.BONUS)
            return WxUserAccountLog.objects.filter(a_type__in=filter_list)
        return WxUserAccountLog.objects.none()


class WxUserCreditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = WxUserCreditLogSerializer
    queryset = WxUserCreditLog.objects.all()
    permission_classes = (IsAuthenticated,)
    filterset_class = WxUserCreditLogFilter

    def get_queryset(self):
        if getattr(self.request.user, 'is_wechat', False):
            return WxUserCreditLog.objects.filter(user=self.request.user)
        if getattr(self.request.user, 'is_staff', False):
            return WxUserCreditLog.objects.all()
        return WxUserCreditLog.objects.none()


class WithdrawCreate(APIView):
    """
    post:
    {\n
        "amount": 22.5
        "wx_code": 'afeafeafe'
    }
    """
    serializer_class = WithdrawCreateSerializer
    permission_classes = (OnlyWxUser,)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(instance)


class WithdrawViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = WithdrawSerializer
    queryset = Withdraw.objects.all()
    permission_classes = (IsAuthenticated,)
    filterset_class = WithdrawFilter

    def get_queryset(self):
        if getattr(self.request.user, 'is_wechat', False):
            return Withdraw.objects.filter(user=self.request.user)
        if getattr(self.request.user, 'is_staff', False):
            return Withdraw.objects.all()
        return Withdraw.objects.none()

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[IsAdminUser, ])
    def operation(self, request, *args, **kwargs):
        """
        Post:
        {\n
            status:  1 或 2 (1 提现完成， 2 拒绝提现)
            remark:  '备注'
        }
        """
        instance = self.get_object()
        if instance.status != instance.SUBMIT:
            return Response('提现状态异常', status=status.HTTP_400_BAD_REQUEST)
        status_ = request.data.get('status', '')
        if status_ and status_ == 1:
            instance.succ(admin=request.user)
            return Response('提现完成')
        if status_ and status_ == 2:
            instance.fail(admin=request.user, remark=request.data.get('remark', ''))
            return Response('提现以拒绝')


class WithdrawOperationLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = WithdrawOperationLogSerializer
    permission_classes = [IsAdminUser, ]
    queryset = WithdrawOperationLog.objects.all()


class Recharge(APIView):
    serializer_class = RechargeCreateSerializer
    permission_classes = (OnlyWxUser,)

    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        extra_data = {"openid": user.wx_app_openid}
        order = WxPayOrderClient().create(
            channel="wx_lite",  # 小程序发起支付的标识
            out_trade_no=instance.rchg_no,
            total_fee=int(instance.real_pay * 100),  # money 单位为分
            client_ip=request.META['REMOTE_ADDR'],
            fee_type="CNY",
            attach="recharge",
            body='优惠充值',
            notify_url=reverse('paycallback', request=request),
            **extra_data
        )
        return Response(order)


class RechargeRecordViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = RechargeRecordSerializer
    permission_classes = (IsAdminUser,)
    queryset = RechargeRecord.objects.all()
    filterset_class = RechargeRecordFilter