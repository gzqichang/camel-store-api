
from django.db import migrations, models

def init_shop(apps, schema_editor):
    Shop = apps.get_model("shop", "Shop")
    if not Shop.objects.all():
        Shop.objects.create(name='总店', province='广东省', city='广州市', district='天河区', detail='建工路12号')


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0006_printer_machine_name'),
    ]

    operations = [
        migrations.RunPython(init_shop),
    ]