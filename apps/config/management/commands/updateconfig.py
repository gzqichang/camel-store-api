from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        print('Start')
        from apps.config.models import BoolConfig, Version, StoreName

        BoolConfig.objects.update_or_create(
            name='store_type',
            defaults={'content': 'camel'},
        )

        BoolConfig.objects.update_or_create(
            name='show_copyright',
            defaults={'content': 'false'},
        )

        BoolConfig.objects.update_or_create(
            name='video_switch',
            defaults={'content': 'false'},
        )

        Version.objects.update_or_create(
            name='version',
            defaults={'content': settings.CAMEL_STORE_VERSION},
        )

        StoreName.objects.update_or_create(
            name='store_name',
            defaults={'content': "骆驼小店"},
        )

        print('finish!!!!')
