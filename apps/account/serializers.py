from rest_framework import serializers
from rest_framework.reverse import reverse
from wxapp.models import WxUser, WxSession
from wxapp.https import wx_config
from wxapp.WXBizDataCrypt import WXBizDataCrypt
from apps.config.models import RechargeType
from qapi.utils import generate_full_uri, secret_string
from apps.qfile.serializers import FileSerializer
from apps.trade.models import Orders
from .models import WxUserInfo, UserRelation, WxUserAccountLog, Withdraw, WithdrawOperationLog, RechargeRecord, WxUserCreditLog


class WxUserInfoSerializer(serializers.ModelSerializer):
    """ 小程序用户的其他信息 """

    class Meta:
        model = WxUserInfo
        exclude = ('user',)


class WxUserSerializer(serializers.HyperlinkedModelSerializer):
    """ 微信用户数据"""
    auth_info = serializers.SerializerMethodField()
    qrcode_url = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    referral_count = serializers.IntegerField(source='relations.count', read_only=True)
    referrer = serializers.SerializerMethodField()
    has_rebate_right = serializers.SerializerMethodField()
    has_bonus_right = serializers.SerializerMethodField()
    order_count = serializers.SerializerMethodField()

    raw_data = serializers.CharField(label='rawData', write_only=True)
    signature = serializers.CharField(label='signature', write_only=True)
    encrypted_data = serializers.CharField(label='encryptedData', write_only=True)
    iv = serializers.CharField(label='iv', write_only=True)
    session = serializers.CharField(label='session', write_only=True)
    scene = serializers.CharField(label='关注场景值', write_only=True)
    phone = serializers.CharField(label='手机号码', write_only=True)

    readonly_fields = ('nickname', 'avatar_url', 'gender', 'wx_app_openid')

    class Meta:
        model = WxUser
        fields = (
            'url', 'id', 'nickname', 'avatar_url', 'gender', 'country', 'province', 'city', 'auth_info',
            'referral_count',
            'qrcode_url', 'level', 'raw_data', 'signature', 'encrypted_data', 'iv', 'session', 'scene', 'phone',
            'referrer',
            'date_joined', 'testers', 'rebate_right', 'bonus_right', 'has_rebate_right', 'has_bonus_right',
            'order_count',
            'upload_perm')

    def get_auth_info(self, instance):
        serializer = WxUserInfoSerializer(getattr(instance, 'info', None), context=self.context)
        return serializer.data

    def get_qrcode_url(self, instance):
        return generate_full_uri(request=self.context.get('request'), suffix=instance.wxa_qrcode)

    def get_level(self, instance):
        level = getattr(instance, 'level', None)
        if level:
            return {
                'title': level.title,
                'icon': FileSerializer(level.icon, context=self.context).data.get('file') if level.icon else ''
            }
        return None

    def get_has_rebate_right(self, instance):
        return instance.has_rebate_right

    def get_has_bonus_right(self, instance):
        return instance.has_bonus_right

    def get_order_count(self, instance):
        return {
            'ord_order_count': instance.orders.filter(model_type='ord', is_pt=False).count(),
        }

    def get_referrer(self, instance):
        info = getattr(instance, 'info', None)
        referrer_relation = getattr(instance, 'referrer_relations', False)
        ret = {
            'nickname': '', 'id': '', 'relate_time': '', 'avatar_url': '',
        }
        if referrer_relation:
            referrer = referrer_relation.user
            ret['relate_time'] = referrer_relation.create_time.strftime('%Y-%m-%d')
            ret['nickname'] = referrer.nickname
            ret['id'] = referrer.id
            ret['avatar_url'] = referrer.avatar_url
        return ret

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        auth_info = ret['auth_info']
        for key, value in auth_info.items():
            if key == 'id':
                continue
            ret[key] = value
        del ret['auth_info']

        account = getattr(instance, 'account', None)
        if account:
            ret['total_asset'] = account.total_asset
            ret['asset'] = account.asset
            ret['recharge'] = account.recharge
            ret['credit'] = account.credit
        else:
            ret['total_asset'] = 0.0
            ret['asset'] = 0.0
            ret['recharge'] = 0.0
            ret['credit'] = 0
        return ret

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        if not getattr(user, 'is_wechat', False):
            raise serializers.ValidationError('仅微信用户可以更改信息')

        if not WxUser.check_signature(user.session.session_key, attrs.get('raw_data'), attrs.get('signature')):
            raise serializers.ValidationError('用户信息签名与微信服务器返回不一致')
        return attrs

    def save(self, **kwargs):
        encrypted_data = self.validated_data['encrypted_data']
        iv = self.validated_data['iv']
        user = self.instance
        user.save_from_encrypted_data(encrypted_data, iv)

        # 创建用户时, 如果有场景值带进来, 则保存场景值
        scene = self.validated_data.get('scene')
        if scene and not getattr(user, 'referrer_relations', False):
            referrer = WxUser.objects.filter(wx_app_openid=scene).first()
            is_valid = UserRelation.check_relation(referrer, user)
            if referrer and is_valid:
                WxUserInfo.update_scene(user, scene)
                # 创建用户关系
                UserRelation.create_relation(referrer, user)
            elif referrer and not is_valid:
                # 如果推荐人和用户不能互成帮手, 则当做是长按图片扫码小程序码进来的用户
                WxUserInfo.update_scene(user, '1048 from a referral ')
            else:
                WxUserInfo.update_scene(user, scene)

        # 保存手机号
        phone = self.validated_data.pop('phone', None)
        if phone:
            WxUserInfo.update_field(user, 'phone', phone)
        return user


class WxUserSavePhoneSerializer(serializers.ModelSerializer):
    """
        小程序用户直接从微信接口获取手机号码
    """
    encrypted_data = serializers.CharField(label='encryptedData', required=True, write_only=True)
    iv = serializers.CharField(label='iv', required=True, write_only=True)

    class Meta:
        model = WxUser
        fields = ('encrypted_data', 'iv')

    def save(self, **kwargs):
        encrypted_data = self.validated_data.get('encrypted_data')
        iv = self.validated_data.get('iv')
        request = self.context.get('request')
        pc = WXBizDataCrypt(wx_config.get('WXAPP_APPID'), request.user.session.session_key)
        phone_info = pc.decrypt(encrypted_data, iv)
        phone = phone_info.get('phoneNumber')
        if phone:
            WxUserInfo.update_field(request.user, 'phone', phone)
        return phone_info


class UserRelationSerializer(serializers.ModelSerializer):
    referral = WxUserSerializer(read_only=True)

    class Meta:
        model = UserRelation
        exclude = ()


class WxUserAccountLogSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    referral_name = serializers.SerializerMethodField()
    referral_avatar_url = serializers.SerializerMethodField()
    asset = serializers.SerializerMethodField()
    detail = serializers.SerializerMethodField()

    class Meta:
        model = WxUserAccountLog
        fields = ('user_info', 'asset', 'a_type', 'referral_name', 'remark', 'number', 'cost', 'add_time', 'note', 'detail',
                  'referral_avatar_url')

    def get_user_info(self, instance):
        if instance.user:
            return {
                'id': instance.user.id,
                'nickname': getattr(instance.user, 'nickname', ''),
                'avatar_url': getattr(instance.user, 'avatar_url', ''),
            }
        return {}

    def get_referral_name(self, instance):
        return getattr(instance.referral, 'nickname', '')

    def get_referral_avatar_url(self, instance):
        return getattr(instance.referral, 'avatar_url', '')

    #收支记录金额
    def get_asset(self, instance):
        if instance.a_type in instance.add_type:
            return '+' + str(instance.asset + instance.balance)
        if instance.a_type in instance.subtract_type:
            return '-' + str(instance.asset + instance.balance)
        return instance.asset + instance.balance

    def get_detail(self, instance):
        if not instance.number:
            return None
        if instance.a_type in [instance.BONUS, instance.USE, instance.USE_RETURN]:
            order = Orders.objects.filter(order_sn=instance.number).first()
            if order:
                return {'link': reverse('orders-detail', (order.id,), request=self.context.get('request')),
                        'model_type': order.model_type,
                        'is_pt': True if order.status == Orders.GROUPBUY else False}
        return None


class WxUserCreditLogSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    credit = serializers.SerializerMethodField()
    detail = serializers.SerializerMethodField()

    class Meta:
        model = WxUserCreditLog
        fields = ('user_info', 'log_type', 'credit',  'remark', 'add_time', 'note', 'number', 'detail')

    def get_user_info(self, instance):
        if instance.user:
            return {
                'id': instance.user.id,
                'nickname': getattr(instance.user, 'nickname', ''),
                'avatar_url': getattr(instance.user, 'avatar_url', ''),
            }
        return {}

    #收支记录金额
    def get_credit(self, instance):
        if instance.log_type in instance.add_type:
            return '+' + str(instance.credit)
        if instance.log_type in instance.subtract_type:
            return '-' + str(instance.credit)
        return instance.credit

    def get_detail(self, instance):
        if not instance.number:
            return None
        if instance.log_type in [instance.REPLACEMENT, instance.SHATE]:
            order = Orders.objects.filter(order_sn=instance.number).first()
            if order:
                return {'link': reverse('orders-detail', (order.id,), request=self.context.get('request')),
                        'model_type': order.model_type}
        return None


class WithdrawSerializer(serializers.HyperlinkedModelSerializer):
    user_info = serializers.SerializerMethodField()
    operation_log = serializers.SerializerMethodField()

    class Meta:
        model = Withdraw
        fields = ('url', 'id', 'user_info', 'wx_code', 'withdraw_no',
                  'amount', 'add_time', 'status', 'remark', 'operation_log')

    def get_user_info(self, instance):
        if instance.wxuser:
            return {
                'id': instance.wxuser.id,
                'nickname': getattr(instance.wxuser, 'nickname', ''),
                'avatar_url': getattr(instance.wxuser, 'avatar_url', ''),
            }
        return {}

    def get_operation_log(self, instance):
        queryset = WithdrawOperationLog.objects.filter(withdraw_no=instance.withdraw_no)
        if queryset:
            return WithdrawOperationLogSerializer(instance=queryset, many=True, context=self.context).data
        return None


class WithdrawCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Withdraw
        fields = ('amount', 'wx_code')

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        amount = attrs.get('amount')
        wx_code = attrs.get('wx_code', '')
        if not getattr(user, 'is_wechat', False):
            raise serializers.ValidationError('只有微信用户才可以提现')
        if amount <= 0:
            raise serializers.ValidationError('请输入正确的提现金额')
        if amount > user.account.asset:
            raise serializers.ValidationError('您的佣金总额不足，无法提现')
        if not wx_code:
            raise serializers.ValidationError('请输入微信号')
        return attrs

    def save(self, **kwargs):
        request = self.context.get('request')
        user = request.user
        instance = Withdraw.create(user, **self.validated_data)
        return WithdrawSerializer(instance, context=self.context).data


class WithdrawOperationLogSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()

    class Meta:
        model = WithdrawOperationLog
        fields = ['admin_name', 'admin', 'withdraw_no', 'add_time', 'operation']

    def get_admin_name(self, instance):
        return instance.admin.username


class RechargeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RechargeRecord
        fields = ('amount',)

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user
        amount = attrs.get('amount')
        if not getattr(user, 'is_wechat', False):
            raise serializers.ValidationError('不会是微信用户')
        if not RechargeType.objects.filter(amount=amount):
            raise serializers.ValidationError('充值金额选择错误')
        return attrs

    def save(self, **kwargs):
        request = self.context.get('request')
        user = request.user
        amount = self.validated_data.get('amount')
        real_pay = RechargeType.objects.get(amount=amount).real_pay
        instance = RechargeRecord.create(user, amount, real_pay)
        return instance


class RechargeRecordSerializer(serializers.HyperlinkedModelSerializer):
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = RechargeRecord
        fields = ('user_info', 'amount', 'real_pay', 'trade_no', 'create_time', 'status', 'rchg_no')

    def get_user_info(self, instance):
        if instance.wxuser:
            return {
                'id': instance.wxuser.id,
                'nickname': getattr(instance.wxuser, 'nickname', ''),
                'avatar_url': getattr(instance.wxuser, 'avatar_url', ''),
            }
        return {}


