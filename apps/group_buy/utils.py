from django.utils import timezone
from apps.account.models import WxUserCreditLog
from apps.goods.models import GoodType
from apps.trade.models import Orders, Items
from apps.trade.utils import validate_marketing_requirement
from apps.refund.utils import create_rartial_refund, create_refund
from apps.user.utils import remind_new_order


def get_ladder_index(ptgroup):
    """
    获得团当前的等级， 未达到返回0
    """
    ladder_ = ptgroup.ptgoods.groupbuy_info.ladder_
    ladder_index = 0  # 阶梯等级
    num = 0
    if ptgroup.mode == ptgroup.PEOPLE:
        num = ptgroup.partake.count() + ptgroup.robot
    elif ptgroup.mode == ptgroup.GOODS:
        for order in ptgroup.order.all():
            num += order.goods_backup.first().num
        num += ptgroup.robot_goods
    for ladder in ladder_:
        if num < ladder.get('num'):
            break
        ladder_index = ladder.get('index')
    return ladder_index


def settlement_ptgroups_order(order):
    """
    计算参与多个团的订单(参团后自己开团的订单)
    """
    ladder_index = 0
    for pt_group in order.pt_group.all():
        index_ = get_ladder_index(pt_group)
        if ladder_index < index_:
            ladder_index = index_
    order_settlement(order, ladder_index)


def order_settlement(order, ladder_index):
    """
    根据团等级结算订单
    """
    if ladder_index == 0:
        order.status = order.CLOSE
        # 退全款
        create_refund(order)
        order.is_pt = False
        order.items.update(send_type=Items.CLOSE)
        order.save()
        for goods in order.goods_backup.all():   # 返还库存
            gtype = GoodType.objects.filter(id=goods.gtype_id).first()
            if gtype:
                gtype.stock += goods.num
                gtype.save()
    else:
        goods_backup = order.goods_backup.first()
        gtype = GoodType.objects.filter(id=goods_backup.gtype_id).first()
        for i in gtype.ladder_:
            if i.get('index') == ladder_index:
                price = i.get('price')
                break
        money = (goods_backup.price - price) * goods_backup.num
        #  部分退款
        if money >= 0:
            create_rartial_refund(order, money)
        # 更新订单金额
        goods_backup.price = price
        goods_backup.save()
        order.is_pt = False
        if order.model_type == order.ORD:
            order.status = order.HAS_PAID
            order.items.update(send_type=Items.SENDING)
            order.save()
        validate_marketing_requirement(order.user)


def add_integral(user, integral, goods_name, ptgroup_no):
    if integral > 0:
        WxUserCreditLog.record(user, log_type=WxUserCreditLog.GROUPING, credit=integral, remark='拼团成功奖励',
                               note=goods_name, number=ptgroup_no)


def ptgroup_settlement(ptgroup):
    """
    拼团的结算
    """
    ladder_index = get_ladder_index(ptgroup)
    for order in ptgroup.order.filter(is_pt=True):
        if order.pt_group.filter(status=ptgroup.BUILD, end_time__gte=timezone.now()):   #订单有参与其他未结算的团，跳过
            continue
        if order.pt_group.count() > 1:      # 订单参与的团大于一个
            settlement_ptgroups_order(order)
        else:
            order_settlement(order, ladder_index)
    if ladder_index == 0:
        ptgroup.status = ptgroup.FAIL
    else:
        ptgroup.status = ptgroup.DONE
        add_integral(ptgroup.user, ptgroup.ptgoods.groupbuy_info.integral, ptgroup.ptgoods.name, ptgroup.ptgroup_no)
        remind_new_order(ptgroup.shop)
    ptgroup.save()
