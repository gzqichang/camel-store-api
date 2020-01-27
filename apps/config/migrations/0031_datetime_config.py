from django.db import migrations, transaction
from django.utils import timezone


def update_configs(apps, schema_editor):
    config = apps.get_model('config', 'SystemConfig')
    content = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    with transaction.atomic():
        keys = [
            'attach_switch',
            'qr_pay_switch',
            'subscription_switch',
        ]
        for name in keys:
            try:
                item = config.objects.get(name=name)
            except config.DoesNotExist:
                pass
            else:
                item.content = content
                item.save()


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0030_store_name'),
    ]

    operations = [
        migrations.RunPython(update_configs),
    ]
