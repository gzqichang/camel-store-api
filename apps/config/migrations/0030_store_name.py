import os
from django.db import migrations, transaction


def update_configs(apps, schema_editor):
    config = apps.get_model('config', 'StoreName')
    store_name = os.environ.get('SHOP_NAME', '')

    with transaction.atomic():
        config.objects.update_or_create(
            name='store_name',
            defaults={
                'label': '店铺名称',
                'content': store_name,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0029_storename'),
    ]

    operations = [
        migrations.RunPython(update_configs),
    ]
