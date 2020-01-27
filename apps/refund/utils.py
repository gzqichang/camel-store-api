from django.utils import timezone

from apps.account.models import WxUserAccountLog
from wx_pay.refund import WxRefundClient

from .models import RefundRecord


def refund(refund_record, refund_id=None):
    """
    退款
    """
    if refund_record.asset_pay > 0 or refund_record.recharge_pay > 0:
        WxUserAccountLog.record(refund_record.user, WxUserAccountLog.USE_RETURN, asset=refund_record.asset_pay,
                            balance=refund_record.recharge_pay, remark='退款', note=f'订单:{refund_record.order.order_sn}')
    refund_record.status = RefundRecord.REFUND
    refund_record.refund_time = timezone.now()
    refund_record.refund_id = refund_id
    refund_record.save()


def create_refund(order):
    """
    全额退款
    """
    instance = RefundRecord.create(order, order.user, order.real_amount, order.asset_pay, order.recharge_pay,
                                   refund_desc='拼团失败')
    if instance.real_amount > 0 and order.trade_no:        # order.real_amount 大于0说明需要微信退款
        res = WxRefundClient().refund(
            total_fee=int(order.real_amount*100),
            refund_fee=int(instance.real_amount*100),
            out_refund_no=instance.refund_no,
            out_trade_no=order.order_sn)
        if res.get('return_code') == 'SUCCESS':
            refund(instance, res.get('refund_id'))
    else:
        refund(instance)


def create_rartial_refund(order, money):
    """
    部分退款
    """
    if money >= order.asset_pay + order.recharge_pay:
        real_amount = money - order.asset_pay - order.recharge_pay
        asset_pay = order.asset_pay
        recharge_pay = order.recharge_pay
    elif money > order.recharge_pay:
        real_amount = 0
        asset_pay = money - order.asset_pay
        recharge_pay = order.recharge_pay
    else:
        real_amount = 0
        asset_pay = 0
        recharge_pay = money

    instance = RefundRecord.create(order, order.user, real_amount, asset_pay, recharge_pay,
                                   refund_desc='拼团成功返还优惠差价')
    if instance.real_amount > 0 and order.trade_no:        # order.real_amount 大于0说明需要微信退款
        res = WxRefundClient().refund(
            total_fee=int(order.real_amount*100),
            refund_fee=int(instance.real_amount*100),
            out_refund_no=instance.refund_no,
            out_trade_no=order.order_sn)
        if res.get('return_code') == 'SUCCESS':
            refund(instance, res.get('refund_id'))
    else:
        refund(instance)