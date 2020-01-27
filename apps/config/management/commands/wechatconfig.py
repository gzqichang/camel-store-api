from django.utils import timezone
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print('Start')
        from apps.config.models import WeChatConfig

        WeChatConfig.environ()
        print('finish!!!!')
