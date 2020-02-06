from django.utils import timezone
from django.db.models import Sum
from wxapp.models import WxUser
from apps.shop.models import Shop
from apps.feedback.models import FeedBack
from apps.account.models import Withdraw, RechargeRecord
from apps.trade.models import Orders

from .models import Count, FeedbackStatistics, WithdrawStatistics, RechargeStatistics, WxUserStatistics, \
    OrderStatistics, TurnoversStatistics


def sum_turnovers(queryset):
    # 计算订单查询集的收入总和

    orders = queryset.aggregate(real_mount=Sum('real_amount'),
                                asset_pay=Sum('asset_pay'),
                                recharge_pay=Sum('recharge_pay'))

    return sum([orders.get('real_mount') if orders.get('real_mount') else 0,
                orders.get('asset_pay') if orders.get('asset_pay') else 0,
                orders.get('recharge_pay') if orders.get('recharge_pay') else 0])


def get_date_range(request_data, interval=30):
    """
    从request中获取起止日期字符串，转化为datetime,默认时间间隔为interval
    :param request_data:
    :param interval:
    :return:
    """
    start = request_data.get('start', None)
    end = request_data.get('end', None)
    if start and end:
        try:
            start = timezone.datetime.strptime(start, "%Y-%m-%d").date()
            end = timezone.datetime.strptime(end, "%Y-%m-%d").date()
        except ValueError:
            end = timezone.localtime().date()
            start = end + timezone.timedelta(days=-interval)
    else:
        end = timezone.localtime().date()
        start = end + timezone.timedelta(days=-interval)
    return start, end




def calc(date):
    # 概况页每日统计
    shops = Shop.objects.all()
    if shops:
        for shop in shops:
            orders = Orders.objects.filter(shop=shop, pay_time__date=date)
            orders_count = orders.count()
            ord_turnovers = sum_turnovers(orders.filter(model_type=Orders.ORD))
            turnovers = ord_turnovers
            Count.objects.update_or_create(date=date, shop=shop,
                                           defaults={'turnovers': turnovers, 'order_count': orders_count})
            TurnoversStatistics.objects.update_or_create(date=date, shop=shop,
                                                         defaults={'ord_turnovers': ord_turnovers,
                                                                   'turnovers': turnovers})
    else:
        orders = Orders.objects.filter(pay_time__date=date)
        orders_count = orders.count()
        ord_turnovers = sum_turnovers(orders.filter(model_type=Orders.ORD))
        turnovers = ord_turnovers
        Count.objects.update_or_create(date=date, defaults={'turnovers': turnovers,
                                                            'order_count': orders_count})
        TurnoversStatistics.objects.update_or_create(date=date,
                                                     defaults={'ord_turnovers': ord_turnovers,
                                                               'qrpay_turnovers': 0,
                                                               'turnovers': turnovers})


def feedbackstatistics(date):
    # 每日反馈统计
    shops = Shop.objects.all()
    if shops:
        for shop in shops:
            new_num = FeedBack.objects.filter(shop=shop, add_time__date=date).count()
            solve_num = FeedBack.objects.filter(shop=shop, solve=True, update_time__date=date).count()
            FeedbackStatistics.objects.update_or_create(date=date, shop=shop,
                                                        defaults={'new_num': new_num, 'solve_num': solve_num})
    else:
        new_num = FeedBack.objects.filter(add_time__date=date).count()
        solve_num = FeedBack.objects.filter(solve=True, update_time__date=date).count()
        FeedbackStatistics.objects.update_or_create(date=date,
                                                    defaults={'new_num': new_num, 'solve_num': solve_num})


def withdrawstatistics(date):
    # 每日提现统计
    withdraws = Withdraw.objects.filter(add_time__date=date)
    withdraw_num = withdraws.count()
    amount_total = withdraws.aggregate(amount_total=Sum('amount'))
    amount_total = amount_total.get('amount_total') if amount_total.get('amount_total') else 0
    succ_num = Withdraw.objects.filter(status=Withdraw.SUCCESS, succ_time__date=date).count()
    WithdrawStatistics.objects.update_or_create(date=date, defaults={
        'withdraw_num': withdraw_num, 'amount_total': amount_total, 'succ_num': succ_num,
    })


def rechargestatistics(date):
    # 每日充值统计
    recharges = RechargeRecord.objects.filter(create_time__date=date, status=RechargeRecord.PAID)
    recharge_num = recharges.count()
    amount_total = recharges.aggregate(amount_total=Sum('real_pay'))
    amount_total = amount_total.get('amount_total') if amount_total.get('amount_total') else 0
    RechargeStatistics.objects.update_or_create(date=date, defaults={
        'recharge_num': recharge_num, 'amount_total': amount_total,
    })


def wxuserstatistics(date):
    # 每日新增用户统计
    new_user_num = WxUser.objects.filter(date_joined__date=date).count()
    user_total = WxUser.objects.count()
    WxUserStatistics.objects.update_or_create(date=date, defaults={'new_user_num': new_user_num, 'user_total': user_total})


def orderstatistics(date):
    # 每日订单统计
    shops = Shop.objects.all()
    if shops:
        for shop in shops:
            orders = Orders.objects.filter(shop=shop, pay_time__date=date)
            ord_num = orders.filter(model_type=Orders.ORD).count()
            repl_num = orders.filter(model_type=Orders.REPL).count()
            OrderStatistics.objects.update_or_create(date=date, shop=shop, defaults={
                'ord_num': ord_num, 'repl_num': repl_num
            })
    else:
        orders = Orders.objects.filter(pay_time__date=date)
        ord_num = orders.filter(model_type=Orders.ORD).count()
        repl_num = orders.filter(model_type=Orders.REPL).count()
        OrderStatistics.objects.update_or_create(date=date, defaults={
            'ord_num': ord_num, 'repl_num': repl_num,
        })


def view_statistics_perm(user, shop_id):
    if user.has_perm('count.view_total_count'):  # 超级管理员
        return True
    if shop_id == 'all':  # 非超级管理员，验证是否是查询的店铺的管理员
        return False
    shop = Shop.objects.filter(id=int(shop_id)).first()
    if not shop or user not in shop.admin.all():
        return False
    return True
