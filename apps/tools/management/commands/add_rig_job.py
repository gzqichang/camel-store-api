from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        from apps.tools.views import add_rig_cron_job

        add_rig_cron_job()
