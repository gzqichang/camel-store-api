import operator
import time
import string
import random
from django.utils import timezone
from decimal import Decimal
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.config.models import Level, BoolConfig
from wxapp.models import WxUser

from apps.utils.disable_for_loaddata import disable_for_loaddata


# Create your models here.

@receiver(post_save, sender='wxapp.WxUser')
@disable_for_loaddata
def user_save(sender, **kwargs):
    instance = kwargs.get('instance')
    created = kwargs.get('created')
    if created:
        WxUserInfo.auth(instance)
        WxUserAccount.create(instance)


#会员等级发生改动时，更新会员等级
@receiver(post_save, sender=Level)
@disable_for_loaddata
def level_save(sender, **kwargs):
    for account in WxUserAccount.objects.exclude(total_recharge=Decimal(0)):
        if BoolConfig.get_bool('wallet_switch'):
            level = Level.objects.filter(threshold__lte=account.total_recharge).order_by('-threshold').first()
            if level:
                UserLevel.objects.update_or_create(wxuser=account.user, defaults={'level': level})
            else:
                UserLevel.objects.filter(wxuser=account.user).delete()


class WxUserInfo(models.Model):
    user = models.OneToOneField('wxapp.WxUser', related_name='info', on_delete=models.CASCADE)
    phone = models.CharField('手机号码', max_length=20, blank=True, default='')
    real_name = models.CharField('真实姓名', max_length=20, blank=True, default='')
    scene = models.CharField('关注场景', max_length=128, blank=True, default='')

    class Meta:
        verbose_name = verbose_name_plural = '用户信息'

    def __str__(self):
        return self.real_name

    @classmethod
    def auth(cls, user, **kwargs):
        info, created = cls.objects.update_or_create(user=user, defaults=kwargs)
        return info

    @classmethod
    def update_field(cls, user, field, value):
        instance, created = cls.objects.get_or_create(user=user)
        setattr(instance, field, value)
        instance.save()
        return instance

    @classmethod
    def update_fields(cls, user, **kwargs):
        info, created = cls.objects.update_or_create(user=user, defaults=kwargs)
        return info

    @classmethod
    def update_scene(cls, user, scene):
        instance, created = cls.objects.get_or_create(user=user)
        if not instance.scene:
            cls.update_field(user, 'scene', scene)
        return instance

    @property
    def referrer(self):
        if not self.scene:
            return None
        return WxUser.objects.filter(wx_app_openid=self.scene).first()


class WxUserAccount(models.Model):
    user = models.OneToOneField('wxapp.WxUser', related_name='account', on_delete=models.CASCADE)
    asset = models.DecimalField('佣金余额', max_digits=30, decimal_places=2, default=0)
    total_asset = models.DecimalField('总计佣金', max_digits=30, decimal_places=2, default=0)
    recharge = models.DecimalField('充值余额', max_digits=30, decimal_places=2, default=0)
    total_recharge = models.DecimalField('累计充值实付金额', max_digits=30, decimal_places=2, default=0)
    credit = models.PositiveIntegerField('积分', default=0)

    class Meta:
        verbose_name = verbose_name_plural = '用户账户'

        permissions = (
            ('change_account', "赠送扣减用户账户金额和积分"),
        )

    @classmethod
    def create(cls, user, asset=0):
        instance, created = cls.objects.get_or_create(user=user, defaults={'asset': asset})
        return instance

    @classmethod
    def asset_info(cls, user):
        instance, created = cls.objects.get_or_create(user=user)
        return {
            'total_asset': instance.total_asset,
            'asset': instance.asset,
            'recharge': instance.recharge,
            'credit': instance.credit,
        }

    @classmethod
    def update_all_wallet(cls, user):
        """ 根据账户记录更新账户金额 """
        instance, created = cls.objects.get_or_create(user=user)
        accout_logs = user.account_logs.all()
        asset = 0
        recharge = 0
        total_asset = 0
        for log in accout_logs:
            action = log.operator_action
            asset = action(asset, log.asset)
            recharge = action(recharge, log.balance)
            if log.a_type == log.ASSET:  # 累计收益等于佣金收益的总和
                total_asset += log.asset
        instance.total_asset = total_asset
        instance.asset = asset
        instance.recharge = recharge
        instance.save()

    @classmethod
    def update_all_credit(cls, user):
        instance, created = cls.objects.get_or_create(user=user)
        credit_logs = user.credit_logs.all()
        credit = 0
        for log in credit_logs:
            action = log.operator_action
            credit = action(credit, log.credit)
        instance.credit = credit
        instance.save()

    def update_recharge_level(self, recharge):
        """更新累计充值金额和level会员等级"""
        self.total_recharge += recharge
        self.save()
        if BoolConfig.get_bool('wallet_switch'):
            level = Level.objects.filter(threshold__lte=self.total_recharge).order_by('-threshold').first()
            if level:
                UserLevel.objects.update_or_create(wxuser=self.user, defaults={'level': level})


class UserRelation(models.Model):
    user = models.ForeignKey('wxapp.WxUser', related_name='relations', on_delete=models.CASCADE)
    referral = models.OneToOneField('wxapp.WxUser', related_name='referrer_relations', on_delete=models.CASCADE)
    create_time = models.DateTimeField('添加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '用户关系'
        ordering = ('-create_time',)
        unique_together = ('user', 'referral')

    def __str__(self):
        return '%s: %s' % (self.user.nickname, self.referral.nickname)

    @classmethod
    def check_relation(cls, user, referral):
        """ 检查推荐关系是否成环, referral 不能是 user 的 n 级推荐人 """
        if user == referral:
            return False
        info = getattr(user, 'info', None)
        if info and info.referrer:
            return cls.check_relation(info.referrer, referral)
        return True

    @classmethod
    def create_relation(cls, user, referral):
        instance, created = cls.objects.get_or_create(user=user, referral=referral)
        return instance


class WxUserAccountLog(models.Model):
    """微信用户钱包记录"""
    ASSET = 'asset'                                # 分享返利
    BONUS = 'bonus'                                # 分销返佣
    USE = 'use'                                    # 使用抵现
    USE_RETURN = 'use_return'                      # 取消订单返还
    WITHDRAW = 'withdraw'                          # 提现
    FAIL_WITHDRAW_RETURN = 'fail_withdraw_return'  # 佣金提现失败后返还金额
    RECHARGE = 'recharge'                          # 优惠充值
    GIFT = 'gift'                                  # 店铺赠送
    DEDUCTION = 'deduction'                        # 店铺扣减

    TYPE = ((ASSET, '分享返利'), (BONUS, '分销返佣'), (USE, '抵现'), (USE_RETURN, '取消订单返还'), (WITHDRAW, '提现'),
            (FAIL_WITHDRAW_RETURN, '提现失败返还'), (RECHARGE, '充值优惠'))

    user = models.ForeignKey('wxapp.WxUser', verbose_name='用户', related_name='account_logs', on_delete=models.CASCADE)
    a_type = models.CharField('类型', max_length=32, choices=TYPE)
    asset = models.DecimalField('奖励收益', max_digits=19, decimal_places=2)
    balance = models.DecimalField('充值余额', max_digits=19, decimal_places=2, default=0)
    referral = models.ForeignKey('wxapp.WxUser', verbose_name='帮手', related_name='referral_account_logs',
                                 on_delete=models.SET_NULL, null=True, blank=True)
    number = models.CharField(verbose_name='订单编号或提现编号', null=True, blank=True, max_length=128)
    cost = models.DecimalField('消费金额', max_digits=19, decimal_places=2, null=True, blank=True)  # 记录类型为返现时，记录消费的金额的字段
    remark = models.CharField('备注', max_length=2048, blank=True, default='')
    note = models.CharField('补充', max_length=128, null=True, blank=True)  # 作为备注的补充，用于在用户收益记录的说明
    add_time = models.DateTimeField('增加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '佣金记录'
        ordering = ('-add_time',)

    def __str__(self):
        return ''

    @property
    def add_type(self):
        """ 增加金额的类型 """
        return (
            self.ASSET,
            self.BONUS,
            self.USE_RETURN,
            self.FAIL_WITHDRAW_RETURN,
            self.RECHARGE,
            self.GIFT,
        )

    @property
    def subtract_type(self):
        """ 扣去金额的类型 """
        return (
            self.USE,
            self.WITHDRAW,
            self.DEDUCTION,
        )

    @property
    def operator_action(self):
        if self.a_type in self.add_type:
            return operator.add
        else:
            return operator.sub

    @classmethod
    @transaction.atomic()
    def record(cls, user, atype, **kwargs):
        if not kwargs.get('asset', 0) > 0.00 and not kwargs.get('balance', 0) > 0.00:
            return
        params = {
            'user': user,
            'a_type': atype,
            'asset': kwargs.get('asset', 0),
            'balance': kwargs.get('balance', 0),
            'referral': kwargs.get('referral', None),
            'remark': kwargs.get('remark', ''),
            'number': kwargs.get('number', ''),
            'cost': kwargs.get('cost', None),
            'note': kwargs.get('note', None)
        }
        instance = cls.objects.create(**params)
        # 更新用户账户
        WxUserAccount.update_all_wallet(user)
        return instance


class WxUserCreditLog(models.Model):
    """微信用户积分纪录"""
    REPLACEMENT = 'replace'     # 积分换购
    REPLACEMENT_RETURN = 'replace_return'   # 积分换购失败返还
    SHATE = 'share'                 # 分享奖励
    GROUPING = 'grouping'           # 拼团成功奖励
    GIFT = 'gift'                   # 店铺赠送
    DEDUCTION = 'deduction'         # 店铺扣减

    LOG_TYPE = ((REPLACEMENT, '积分换购'), (SHATE, '分享奖励'), (GROUPING, '拼团成功奖励'), (GIFT, '店铺赠送'), (DEDUCTION, '店铺扣减'))

    user = models.ForeignKey('wxapp.WxUser', verbose_name='用户', related_name='credit_logs', on_delete=models.CASCADE)
    log_type = models.CharField(verbose_name='记录类型', max_length=128, choices=LOG_TYPE)
    credit = models.PositiveIntegerField(verbose_name='积分', default=0)
    remark = models.CharField(verbose_name='备注', max_length=2048, blank=True, default='')
    note = models.CharField(verbose_name='补充', max_length=128, null=True, blank=True)  # 作为备注的补充，用于在用户收益记录的说明
    number = models.CharField(verbose_name='订单编号或拼团编号', null=True, blank=True, max_length=128)
    add_time = models.DateTimeField('增加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '积分记录'
        ordering = ('-add_time',)

    def __str__(self):
        return '积分纪录'

    @property
    def add_type(self):
        """ 增加积分的类型 """
        return (
            self.SHATE,
            self.GROUPING,
            self.GIFT,
            self.REPLACEMENT_RETURN
        )

    @property
    def subtract_type(self):
        """ 扣去积分的类型 """
        return (
            self.REPLACEMENT,
            self.DEDUCTION,
        )

    @property
    def operator_action(self):
        if self.log_type in self.add_type:
            return operator.add
        else:
            return operator.sub

    @classmethod
    def record(cls, user, log_type, credit, **kwargs):
        if not credit > 0:
            return
        params = {
            'user': user,
            'log_type': log_type,
            'credit': credit,
            'remark': kwargs.get('remark', ''),
            'note': kwargs.get('note', None),
            'number': kwargs.get('number', None),
        }
        instance = cls.objects.create(**params)
        # 更新用户账户积分
        WxUserAccount.update_all_credit(user)
        return instance


def generate_wd_no():
    salt = ''.join(random.choice(string.digits) for _ in range(6))
    return 'WD' + "{}{}".format(time.strftime("%Y%m%d%H%M%S"), salt)


class Withdraw(models.Model):
    SUBMIT = 0
    SUCCESS = 1
    FAIL = 2

    STATUS = ((SUBMIT, '提现中'), (FAIL, '提现失败'), (SUCCESS, '提现完成'))

    wxuser = models.ForeignKey('wxapp.WxUser', verbose_name='用户', related_name='withdraw_logs',
                               on_delete=models.CASCADE)
    withdraw_no = models.CharField(verbose_name='提现单号', max_length=128, unique=True, default=generate_wd_no)
    amount = models.DecimalField('提现金额', max_digits=19, decimal_places=2)
    wx_code = models.CharField(max_length=128, verbose_name='微信号')
    add_time = models.DateTimeField(verbose_name='提现发起时间', auto_now_add=True)
    succ_time = models.DateTimeField(verbose_name='完成时间', null=True, blank=True)
    remark = models.CharField(max_length=256, null=True, blank=True, verbose_name='备注')
    status = models.IntegerField(choices=STATUS, default=SUBMIT, verbose_name='提现状态')

    class Meta:
        verbose_name = verbose_name_plural = '提现记录'
        ordering = ('status', 'add_time',)

    def __str__(self):
        return self.withdraw_no

    @classmethod
    def create(cls, user, amount, wx_code):
        instance = cls.objects.create(wxuser=user, amount=amount, wx_code=wx_code)
        WxUserAccountLog.record(user, WxUserAccountLog.WITHDRAW, asset=amount,
                                number=instance.withdraw_no, remark=f'提现{amount}元')
        return instance

    @property
    def need_pay(self):
        return self.status == self.SUBMIT

    # 成功提现
    @transaction.atomic
    def succ(self, admin):
        self.succ_time = timezone.now()
        self.status = self.SUCCESS
        self.save()
        WithdrawOperationLog.create(admin=admin, withdraw_no=self.withdraw_no, operation='提现状态改为：提现完成')

    # 提现失败
    @transaction.atomic
    def fail(self, admin, remark=None):
        if remark:
            self.remark = remark
        self.status = self.FAIL
        note = f'拒绝原因:{self.remark}' if self.remark else '拒绝原因:暂停提现服务'
        WxUserAccountLog.record(self.wxuser, WxUserAccountLog.FAIL_WITHDRAW_RETURN, asset=self.amount,
                                number=self.withdraw_no, remark=f'提现申请退还', note=note)
        self.save()
        WithdrawOperationLog.create(admin=admin, withdraw_no=self.withdraw_no, operation='提现状态改为：提现失败')


admin = get_user_model()


class WithdrawOperationLog(models.Model):
    admin = models.ForeignKey(admin, verbose_name='操作人', null=True, blank=True, on_delete=models.SET_NULL)
    withdraw_no = models.CharField(verbose_name='提现单号', max_length=128, db_index=True)
    add_time = models.DateTimeField(verbose_name='操作时间', auto_now_add=True)
    operation = models.CharField(verbose_name='操作', max_length=256)

    class Meta:
        verbose_name = verbose_name_plural = '提现操作日志'
        ordering = ('-add_time',)

    def __str__(self):
        return f'提现单号（{self.withdraw_no}）的操作记录'

    @classmethod
    def create(cls, admin, withdraw_no, operation):
        cls.objects.create(admin=admin, withdraw_no=withdraw_no, operation=operation)


class UserLevel(models.Model):
    wxuser = models.OneToOneField('wxapp.WxUser', verbose_name='用户', related_name='level', on_delete=models.CASCADE)
    level = models.ForeignKey('config.Level', verbose_name='会员等级', related_name='users', on_delete=models.CASCADE)

    class Meta:
        verbose_name = verbose_name_plural = '用户等级'

    def __str__(self):
        return f'{self.level.title}: {self.wxuser.nickname}'

    @property
    def title(self):
        return self.level.title

    @property
    def discount(self):
        # 折扣存储时是以百分号为单位，计算使用时要除以100
        return Decimal(self.level.discount) / Decimal('100')

    @property
    def icon(self):
        if self.level.icon:
            return self.level.icon
        return None

def generate_rg_no():
    salt = ''.join(random.choice(string.digits) for _ in range(6))
    return 'RG' + "{}{}".format(time.strftime("%Y%m%d%H%M%S"), salt)


class RechargeRecord(models.Model):
    PAID = 'paid'
    UNPAID = 'unpaid'

    STATUS = ((PAID, '已支付'), (UNPAID, '未支付'))
    rchg_no = models.CharField(verbose_name='充值编号', max_length=128, unique=True, db_index=True, default=generate_rg_no)
    wxuser = models.ForeignKey('wxapp.WxUser', null=True, blank=True, verbose_name='用户',
                               related_name='recharge_records', on_delete=models.SET_NULL)
    amount = models.DecimalField(verbose_name='充值金额', max_digits=19, decimal_places=2)
    real_pay = models.DecimalField(verbose_name='支付金额', max_digits=19, decimal_places=2)
    trade_no = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="微信交易号")
    status = models.CharField(max_length=128, verbose_name='充值状态', choices=STATUS, default=UNPAID)
    create_time = models.DateTimeField(verbose_name='充值时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '充值记录'
        ordering = ('-create_time',)

    def __str__(self):
        return f'充值记录:{self.rchg_no}'

    @classmethod
    def create(cls, wxuser, amount, real_pay):
        return cls.objects.create(wxuser=wxuser, amount=amount, real_pay=real_pay)

    def recharge(self, trade_no=None):
        if self.status == self.PAID:
            return '已充值'
        self.status = self.PAID
        self.trade_no = trade_no
        self.wxuser.account.update_recharge_level(self.amount)
        WxUserAccountLog.record(self.wxuser, WxUserAccountLog.RECHARGE, balance=self.amount, remark='优惠充值', number=self.rchg_no)
        self.save()
