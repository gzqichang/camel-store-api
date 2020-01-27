from django.db import migrations, transaction
from django.utils import timezone


def update_configs(apps, schema_editor):
    config = apps.get_model('config', 'BoolConfig')
    content = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    with transaction.atomic():
        config.objects.update_or_create(
            name='attach_switch',
            defaults={'content': content},
        )
        config.objects.update_or_create(
            name='qr_pay_switch',
            defaults={'content': content},
        )
        config.objects.update_or_create(
            name='subscription_switch',
            defaults={'content': content},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0027_datetimeconfig'),
    ]

    operations = [
        migrations.RunPython(update_configs),
    ]
