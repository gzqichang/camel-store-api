
from django.db import migrations, models

def init_shop(apps, schema_editor):
    Shop = apps.get_model("shop", "Shop")
    shop = Shop.objects.all().first()
    # 此处拿到的 Shop 是 __fake__.Shop，也就是假的，拿不到 models.Shop.UNLIMIT，所以只好写字符串了
    shop.delivery_divide = 'unlimit'
    shop.save()

class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0016_auto_20200218_1738'),
    ]

    operations = [
        migrations.RunPython(init_shop),
    ]