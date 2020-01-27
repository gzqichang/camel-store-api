from django.utils import timezone
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Count Date Data"

    def add_arguments(self, parser):
        parser.add_argument('action', nargs='?', help='action ?')

    def handle(self, *args, **options):
        print('Start Count')
        from apps.trade.models import Orders
        from apps.count.models import Count
        from apps.shop.models import Shop
        from apps.count.utils import sum_turnovers

        now = timezone.now()
        date = now.date() + timezone.timedelta(days=-1)
        shops = Shop.objects.all()
        if shops:
            for shop in shops:
                orders = Orders.objects.filter(shop=shop, pay_time__date=date)
                orders_count = orders.count()
                turnovers = sum_turnovers(orders)
                Count.objects.update_or_create(date=date, shop=shop,
                                defaults={'turnovers': turnovers, 'order_count': orders_count})
        else:
            orders = Orders.objects.filter(pay_time__date=date)
            orders_count = orders.count()
            turnovers = sum_turnovers(orders)

            Count.objects.update_or_create(date=date, defaults={'turnovers': turnovers,
                                                'order_count': orders_count})
        print('Count finish!!!!')