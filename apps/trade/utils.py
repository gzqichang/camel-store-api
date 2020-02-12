import datetime
import re
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings
from apps.config.models import Marketing, BoolConfig
from apps.account.models import WxUserAccountLog, WxUserCreditLog
from apps.goods.models import GoodType, ReplGoodsType
from wxapp.models import WxUser
from apps.group_buy.models import PtGroup
from apps.refund.utils import create_refund
from apps.user.utils import remind_new_order
from apps.sms.models import SmsSwitch
from apps.sms.send_sms import send_sms
from .models import Orders, Items, BuyerCode, GoodsBackup


# 支付后结算用户是否满足推广与返利门槛
def validate_marketing_requirement(user):
    if user.rebate_right != user.NULL and user.bonus_right != user.NULL:
        return
    order = Orders.objects.filter(user=user, status__in=[Orders.HAS_PAID, Orders.RECEIVING, Orders.DONE, Orders.SERVING])\
        .aggregate(real_amount=Sum('real_amount'), asset_pay=Sum('asset_pay'), rcharge_pay=Sum('recharge_pay'))
    total = sum([order.get('real_amount') if order.get('real_amount') else 0,
                       order.get('asset_pay') if order.get('asset_pay') else 0,
                       order.get('recharge_pay') if order.get('recharge_pay') else 0])
    if Marketing.get_value('rebate') <= total and user.rebate_right == user.NULL:
        user.rebate_right = user.TRUE
    if Marketing.get_value('bonus') <= total and user.bonus_right == user.NULL:
        user.bonus_right = user.TRUE
    user.save()


def order_pay(order, trade_no=None):
    # 订单支付
    if order.status == order.CLOSE:     # 避免出现订单已关闭后支付的情况
        create_refund(order)
        return
    if order.status != order.PAYING:
        return "该订单已支付"
    order.trade_no = trade_no
    order.pay_time = timezone.now()
    if order.is_pt:
        order.status = order.GROUPBUY
        order.save()
        if not order.pt_group.all():       # 开团订单，支付后建立团
            goods_backup = order.goods_backup.first()
            pt = PtGroup.create(order.user, goods_backup.goods, order.shop)
            pt.order.add(order)
            pt.partake.add(order.user)
        elif order.pt_group.all() and not order.pt_group.filter(status=PtGroup.BUILD):
            # 参团订单支付后团已经结算，退款
            order.status = order.CLOSE
            order.save()
            create_refund(order)
        else:
            for pt in order.pt_group.filter(status=PtGroup.BUILD):
                pt.partake.add(order.user)
    else:
        if order.model_type in [order.ORD, order.REPL]:
            order.status = order.HAS_PAID
            order.items.update(send_type=Items.SENDING)
            order.save()
            remind_new_order(order.shop)
    validate_marketing_requirement(order.user)


def order_cancel(order):
    # 订单关闭
    if order.is_pt:
        for pt in order.pt_group.all():
            pt.order.remove(order)
            pt.partake.remove(order.user)
            order.is_pt = False
    order.status = order.CLOSE
    order.items.update(send_type=Items.CLOSE)  # 关闭子订单
    for goods in order.goods_backup.all():  # 返还库存
        if order.model_type == order.ORD:
            gtype = GoodType.objects.filter(id=goods.gtype_id).first()
        if order.model_type == order.REPL:
            gtype = ReplGoodsType.objects.filter(id=goods.gtype_id).first()
        if gtype:
            gtype.stock += goods.num
            gtype.save()
    if order.asset_pay > 0 or order.recharge_pay > 0:
        WxUserAccountLog.record(order.user, WxUserAccountLog.USE_RETURN, asset=order.asset_pay,
                                balance=order.recharge_pay, remark='取消订单退还', note=f'订单:{order.order_sn}', number=order.order_sn)
    if order.credit > 0:
        WxUserCreditLog.record(order.user, WxUserCreditLog.REPLACEMENT_RETURN, credit=order.credit, number=order.order_sn,
                               remark='订单未支付返还积分')
    order.save()


def compute_amount(order, order_amount, postage_total, use_wallet=False):
    # 计算订单的金额
    order.order_amount = order_amount
    order.postage_total = postage_total
    if use_wallet and BoolConfig.get_bool('wallet_switch'):
        total = order.order_amount + order.postage_total
        account = getattr(order.user, 'account', None)
        asset = getattr(account, 'asset', Decimal('0'))
        recharge = getattr(account, 'recharge', Decimal('0'))
        if total < asset:
            order.asset_pay = total
            order.real_amount = 0
        elif total > asset and total < asset + recharge:
            order.asset_pay = asset
            order.recharge_pay = total - asset
            order.real_amount = 0
        elif total >= asset + recharge:
            order.asset_pay = asset
            order.recharge_pay = recharge
            order.real_amount = total - asset - recharge
        remark = '商品购买'
        number = order.order_sn
        WxUserAccountLog.record(order.user, WxUserAccountLog.USE, asset=order.asset_pay,
                                balance=order.recharge_pay, remark=remark, note=f'订单:{order.order_sn}', number=number)
    else:
        order.real_amount = order.order_amount + order.postage_total
    order.save()
    return order


def order_validate_all_send(order):
    # 检查订单的子订单是否全部发货， 全发后状态改为待收货
    if not order.items.filter(send_type=Items.SENDING):
        order.status = order.RECEIVING
        order.send_time = timezone.now()
        order.flag_time = timezone.now() + timezone.timedelta(days=7)  # 发货七天后自动收货
        order.save()


def order_done(order):
    # 订单确认收货

    order.status = order.DONE
    order.receive_time = timezone.now()
    order.save()
    for item in order.items.all():  # 订单确认收货，每个商品计算返利等
        item_confirm_receipt(item)


def calc_asset(item):
    # 计算分销和返利的

    """ 分销 """
    goods_info = item.goods_backup
    if BoolConfig.get_bool('bonus_switch'):
        direct_relation = None
        if getattr(item.order.user, 'referrer_relations', None):
            direct_relation = item.order.user.referrer_relations.user  # 上线
        if direct_relation and direct_relation.has_bonus_right and goods_info.g_bonus > 0:
            WxUserAccountLog.record(direct_relation, WxUserAccountLog.BONUS, asset=goods_info.g_bonus * goods_info.num,
                                    referral=item.order.user,
                                    number=item.order_sn, remark='成员消费返利', note=item.order.user.nickname,
                                    cost=goods_info.price * goods_info.num)
    """ 分享返积分返利 """
    if goods_info.g_rebate <= 0 or not BoolConfig.get_bool('rebate_switch'):
        return False
    if not goods_info.share_user_id:
        return False
    share_user = WxUser.objects.filter(id=int(goods_info.share_user_id)).first()
    if not share_user or not share_user.has_rebate_right:
        return False
    WxUserCreditLog.record(share_user, WxUserCreditLog.SHATE, credit=goods_info.g_rebate * goods_info.num,
                            number=item.order_sn, remark='商品分享返利', note=goods_info.goods_name)


def item_send(item):
    # 子订单发货
    if item.goods_backup.delivery_method == GoodsBackup.BUYER:
        BuyerCode.create(item)

    if item.order.model_type in [Orders.ORD, Orders.REPL]:
        item.send_time = timezone.now()
        item.send_type = item.RECEIVING
        item.save()
        order_validate_all_send(item.order)
    delivery_notice(item)


def item_confirm_receipt(item):
    # 子订单确认收货

    if item.send_type == item.OVER:
        return
    item.send_type = item.OVER
    if not item.receive_time:
        item.receive_time = timezone.now()
    item.save()
    if item.order.model_type == Orders.ORD:
        calc_asset(item)


def sub_order_done(order):
    # 检查订阅订单是否完成

    if not order.items.exclude(send_type=Items.OVER):
        order.status = order.DONE
        order.next_send = None
        order.receive_time = timezone.now()
        order.save()


def arrive(item):
    # 子订单送达

    item.receive_time = timezone.now()
    item.send_type = item.ARRIVE
    item.save()


def delivery_notice(item):
    """
    发货短信通知
    """
    if not SmsSwitch.get('delivery_notice'):
        return
    purchaser_phone = None
    receiver_phone = None
    try:
        receiver_phone = item.order.delivery_address.mobile_phone
        purchaser_phone = item.order.user.info.phone
    except AttributeError as e:
        print(e)

    if receiver_phone == purchaser_phone:     # 手机号一致，只发给收件人
        purchaser_phone = None
    if purchaser_phone:
        data = {"member": item.order.user.nickname,
                "commodity": item.goods_backup.goods_name,
                "business": getattr(settings, 'SHOP_NAME')}
        send_sms(purchaser_phone, data, 'SMS_157100140')
    if receiver_phone:
        #根据不同配送方式发送不同的通知短信
        data = {
            "receiver": item.order.delivery_address.sign_name,
            "commodity": item.goods_backup.goods_name,
            "business": getattr(settings, 'SHOP_NAME'),
        }
        if item.goods_backup.delivery_method == 'own':  # 自配送
            send_sms(receiver_phone, data, 'SMS_157100062')
        if item.goods_backup.delivery_method == 'express':  # 快递物流
            data.update({
                "expresscompany": item.express_company,
                "trackingnumber": item.express_num,
            })
            send_sms(receiver_phone, data, 'SMS_157100132')
        if item.goods_backup.delivery_method == 'buyer':  # 自提
            data.update({
                "address": item.order.shop.address,
                "store": item.order.shop.name,
            })
            send_sms(receiver_phone, data, 'SMS_157100093')


def parseAddress(address):
    levels = ['省|市|区', '市|区', '市|区|县']
    patterns = [
        f'(\\S[^ {levels[0]}]+[{levels[0]}])',
        f'(\\S[^ {levels[1]}]+[{levels[1]}])',
        f'(\\S[^ {levels[2]}]+[{levels[2]}])',
        f'(\\S*)',
    ]
    results = re.match(''.join(patterns), address)
    return results.groups() if results is not None else []
