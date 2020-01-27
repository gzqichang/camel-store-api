from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Q
from rest_framework.response import Response
from rest_framework.views import APIView, status
from rest_framework.permissions import IsAdminUser

from apps.account.models import WxUserAccount, Withdraw
from apps.trade.models import Orders
from apps.shop.models import Shop
from apps.feedback.models import FeedBack
from apps.goods.models import Goods
from apps.config.models import Level
from wxapp.models import WxUser

from .models import Count, FeedbackStatistics, WithdrawStatistics, RechargeStatistics, WxUserStatistics, \
    OrderStatistics, TurnoversStatistics
from .utils import calc, feedbackstatistics, withdrawstatistics, rechargestatistics, wxuserstatistics, orderstatistics, \
    view_statistics_perm, get_date_range, sum_turnovers


def get_last_month(date):
    # 上个月的年份和月份
    if date.month == 1:
        return date.year - 1, 12
    return date.year, date.month - 1


class Statistic(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        '''
        /count/statistic/?shop=1  (全部：shop=all)
        '''
        shop = request.query_params.get('shop', None)
        if not shop:
            return Response('缺少参数', status=status.HTTP_400_BAD_REQUEST)
        ord_orders = Orders.objects.filter(model_type=Orders.ORD, status=Orders.HAS_PAID)
        feedback = FeedBack.objects.filter(solve=False)
        ord_goods = Goods.objects.filter(model_type=Goods.ORD, status=Goods.IS_SELL, is_template=False)
        asset = WxUserAccount.objects.only('asset').aggregate(total=Sum('asset'))
        if shop == 'all':
            if not request.user.has_perm('count.view_total_count'):
                return Response('没有权限', status=status.HTTP_400_BAD_REQUEST)
        else:
            ord_orders = ord_orders.filter(shop__id=int(shop))
            feedback = feedback.filter(shop__id=int(shop))
            ord_goods = ord_goods.filter(shop__id=int(shop))

        return Response({'ord_orders': ord_orders.count(),
                         'feedback': feedback.count(),
                         'ord_goods': ord_goods.count(),
                         'asset': asset.get('total') if asset.get('total') else 0,
                         })


class ManageCount(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        '''
        /count/count/?shop=1  (全部：shop=all)
        '''
        shop = request.query_params.get('shop', None)
        if not shop:
            return Response('缺少参数', status=status.HTTP_400_BAD_REQUEST)
        today = timezone.localtime().date()
        yesterday = today + timezone.timedelta(days=-1)
        week_ago_day = today + timezone.timedelta(days=-7)
        yesterday_count = Count.objects.filter(date=yesterday)
        week_ago_count = Count.objects.filter(date__gte=week_ago_day)

        if shop == 'all':
            if not request.user.has_perm('count.view_total_count'):
                return Response('没有权限', status=status.HTTP_400_BAD_REQUEST)
        else:
            yesterday_count = yesterday_count.filter(shop__id=int(shop))
            week_ago_count = week_ago_count.filter(shop__id=int(shop))

        yesterday_count = yesterday_count.aggregate(order_total=Sum('order_count'), turnovers_total=Sum('turnovers'))
        week_ago_count = week_ago_count.aggregate(order_total=Sum('order_count'), turnovers_total=Sum('turnovers'))

        e_yesterday = Withdraw.objects.filter(succ_time__date=yesterday).aggregate(amount_total=Sum('amount'))
        e_week_ago = Withdraw.objects.filter(succ_time__date__gte=week_ago_day).aggregate(amount_total=Sum('amount'))
        return Response({
            'order_count': {
                'yesterday': yesterday_count.get('order_total') if yesterday_count.get('order_total') else 0,
                'week_ago': week_ago_count.get('order_total') if week_ago_count.get('order_total') else 0},
            'turnovers': {
                'yesterday': yesterday_count.get('turnovers_total') if yesterday_count.get('turnovers_total') else 0,
                'week_ago': week_ago_count.get('turnovers_total') if week_ago_count.get('turnovers_total') else 0},
            'expenditure': {'yesterday': e_yesterday.get('amount_total') if e_yesterday.get('amount_total') else 0,
                            'week_ago': e_week_ago.get('amount_total') if e_week_ago.get('amount_total') else 0}
        })

    def post(self, request, *args, **kwargs):
        '''
        {\n
            'shop': 1 or(all)
            'start': "2019-01-10",
            'end': "2019-01-17"
        }
        '''
        shop = request.data.get('shop', None)
        if not shop:
            return Response('缺少参数', status=status.HTTP_400_BAD_REQUEST)
        if not view_statistics_perm(request.user, shop):
            return Response('您没有查看权限', status=status.HTTP_403_FORBIDDEN)
        start, end = get_date_range(request.data, interval=7)
        date_list = []
        count_list = []
        for i in range(0, (end - start).days + 1):
            date = start + timezone.timedelta(days=i)
            date_list.append(date)
        for date in date_list:
            if shop == 'all':  # 查看所有店
                if not request.user.has_perm('count.view_total_count'):
                    return Response('没有权限', status=status.HTTP_400_BAD_REQUEST)
                count = Count.objects.filter(date=date)
                if count:
                    amount = count.aggregate(total=Sum('turnovers'))
                    order_count = count.aggregate(total=Sum('order_count'))
                    amount = amount.get('total') if amount.get('total') else 0
                    order_count = order_count.get('total') if order_count.get('total') else 0
                    count_list.append({'date': date.strftime('%m-%d'),
                                       'amount': amount,
                                       'order_count': order_count})
                else:
                    count_list.append({'date': date.strftime('%m-%d'), 'amount': 0, 'order_count': 0})
            else:  # 查看某个店
                count = Count.objects.filter(shop__id=int(shop)).filter(date=date).first()
                if count:
                    count_list.append({'date': date.strftime('%m-%d'),
                                       'amount': count.turnovers,
                                       'order_count': count.order_count})
                else:
                    count_list.append({'date': date.strftime('%m-%d'), 'amount': 0, 'order_count': 0})
        return Response({
            'count': count_list,
        })


class Calc(APIView):
    permission_classes = []

    # throttle_scope = 'calc'

    def get(self, request, *args, **kwargs):
        now = timezone.localtime()
        date = now.date() + timezone.timedelta(days=-1)
        calc(date)  # 概况页统计
        feedbackstatistics(date)  # 每日客户反馈统计
        withdrawstatistics(date)  # 每日提现统计
        rechargestatistics(date)  # 每日充值统计
        wxuserstatistics(date)  # 每日新增用户统计
        orderstatistics(date)  # 每日订单统计
        return Response('success')


class WithdrawStatisticsAPI(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end = get_date_range(request.query_params, interval=30)
        count_list = []
        for i in range(0, (end - start).days + 1):
            date = start + timezone.timedelta(days=i)
            statistics_data = WithdrawStatistics.objects.filter(date=date).first()
            if statistics_data:
                count_list.append({'date': date, 'withdraw_num': statistics_data.withdraw_num,
                                   'succ_num': statistics_data.succ_num})
            else:
                count_list.append({'date': date, 'withdraw_num': 0, 'succ_num': 0})
        return Response(count_list)


class RechargeStatisticsAPI(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end = get_date_range(request.query_params, interval=30)
        count_list = []
        for i in range(0, (end - start).days + 1):
            date = start + timezone.timedelta(days=i)
            statistics_data = RechargeStatistics.objects.filter(date=date).first()
            if statistics_data:
                count_list.append({'date': date, 'amount_total': statistics_data.amount_total})
            else:
                count_list.append({'date': date, 'amount_total': Decimal(0.0)})
        return Response(count_list)


class WxUserStatisticsAPI(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        start, end = get_date_range(request.query_params, interval=30)
        count_list = []
        for i in range(0, (end - start).days + 1):
            date = start + timezone.timedelta(days=i)
            statistics_data = WxUserStatistics.objects.filter(date=date).first()
            if statistics_data:
                count_list.append({'date': date, 'new_user_num': statistics_data.new_user_num,
                                   'user_total': statistics_data.user_total})
            else:
                count_list.append({'date': date, 'new_user_num': 0, 'user_total': 0})
        return Response(count_list)


class FeedbackStatisticsAPI(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        '''
        shop: 1 or all
        '''
        shop = request.query_params.get("shop", 'all')
        if not view_statistics_perm(request.user, shop):
            return Response('您没有查看权限', status=status.HTTP_403_FORBIDDEN)
        start, end = get_date_range(request.query_params, interval=30)
        count_list = []
        for i in range(0, (end - start).days + 1):
            new_num = 0
            solve_num = 0
            date = start + timezone.timedelta(days=i)
            if shop == 'all':
                statistics_data = FeedbackStatistics.objects.filter(date=date)
            else:
                statistics_data = FeedbackStatistics.objects.filter(shop__id=int(shop), date=date)
            for i in statistics_data:
                new_num += i.new_num
                solve_num += i.solve_num
            count_list.append({'date': date, 'new_num': new_num, 'solve_num': solve_num})
        return Response(count_list)


class OrderStatisticsAPI(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        '''
        shop: 1 or all
        '''
        shop = request.query_params.get("shop", 'all')
        if not view_statistics_perm(request.user, shop):
            return Response('您没有查看权限', status=status.HTTP_403_FORBIDDEN)
        start, end = get_date_range(request.query_params, interval=30)
        count_list = []
        for i in range(0, (end - start).days + 1):
            ord_num = 0
            repl_num = 0
            date = start + timezone.timedelta(days=i)
            if shop == 'all':
                statistics_data = OrderStatistics.objects.filter(date=date)
            else:
                statistics_data = OrderStatistics.objects.filter(shop__id=int(shop), date=date)
            for i in statistics_data:
                ord_num += i.ord_num
                repl_num += i.repl_num
            count_list.append({'date': date, 'ord_num': ord_num, 'repl_num': repl_num, 'total': ord_num + repl_num})
        return Response(count_list)


class TurnoversStatisticsAPI(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        '''
        shop: 1 or all
        '''
        shop = request.query_params.get("shop", 'all')
        if not view_statistics_perm(request.user, shop):
            return Response('您没有查看权限', status=status.HTTP_403_FORBIDDEN)
        start, end = get_date_range(request.query_params, interval=30)
        count_list = []
        for i in range(0, (end - start).days + 1):
            ord_turnovers = Decimal(0.00)
            turnovers = Decimal(0.00)
            date = start + timezone.timedelta(days=i)
            if shop == 'all':
                statistics_data = TurnoversStatistics.objects.filter(date=date)
            else:
                statistics_data = TurnoversStatistics.objects.filter(shop__id=int(shop), date=date)
            for i in statistics_data:
                ord_turnovers += i.ord_turnovers
                turnovers += i.turnovers
            count_list.append(
                {'date': date, 'ord_turnovers': ord_turnovers, 'turnovers': turnovers})
        return Response(count_list)


class LevelStatisticsAPI(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        res = []
        total = WxUser.objects.count()
        non_member = total
        for level in Level.objects.all():
            num = level.users.count()
            proportion = (num / total) * 100
            res.append({'level': level.title, 'num': num, 'proportion': proportion})
            non_member = non_member - num
        res.append({'level': 'null', 'num': non_member, 'proportion': (non_member / total) * 100})
        return Response(res)


class OnlineAPI(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        goods = Goods.objects.filter(is_template=False, status=Goods.IS_SELL).count()
        orders = Orders.objects.exclude(model_type=Orders.REPL).exclude(Q(status=Orders.PAYING)|Q(status=Orders.CLOSE))
        orders_num = orders.count()
        if orders_num > 0:
            turnovers = sum_turnovers(orders)
        else:
            turnovers = 0
        return Response({'goods': goods, 'orders': orders_num, 'turnovers': turnovers})