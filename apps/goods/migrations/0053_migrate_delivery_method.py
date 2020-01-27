

import django.contrib.postgres.fields
from django.db import migrations, models


def migrate_delivery_method(apps, schema_editor):
    Goods = apps.get_model("goods", "Goods")
    for goods in Goods.objects.all():
        if goods.delivery_method:
            goods.delivery_method_list.append(goods.delivery_method)
        if goods.pick_up:
            goods.delivery_method_list.append('buyer')
        goods.save()


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0052_auto_20190424_1637'),
    ]

    operations = [

        migrations.RunPython(
            migrate_delivery_method
        ),
    ]
