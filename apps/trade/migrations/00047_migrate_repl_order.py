from django.db import migrations, models
from django.db import transaction


def migrate_repl_order(apps, schema_editor):
    Orders = apps.get_model("trade", "Orders")
    with transaction.atomic():
        for order in Orders.objects.filter(model_type='repl'):
            order.credit = int(order.order_amount)
            order.order_amount = 0
            order.save()

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('trade', '0046_auto_20200109_1122'),

    ]

    operations = [
        migrations.RunPython(migrate_repl_order),
    ]
