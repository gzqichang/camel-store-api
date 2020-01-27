
from django.db import migrations, models
from django.db import transaction


def migrate_goods_to_ord_goods(apps, schema_editor):
    # 将普通商品的特定信息迁移到普通商品信息表
    Goods = apps.get_model("goods", "Goods")
    OrdGoods = apps.get_model("goods", "OrdGoods")
    GoodType = apps.get_model("goods", "GoodType")
    with transaction.atomic():
        for goods in Goods.objects.all():
            instance = OrdGoods.objects.create()
            instance.gtypes.add(*GoodType.objects.filter(goods=goods))
            goods.ord_goods = instance
            goods.postage = None
            instance.save()
            goods.save()


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0034_migrate_image'),
    ]

    operations = [

        migrations.RunPython(migrate_goods_to_ord_goods),

        # 删除普通商品规格中的外键
        migrations.RemoveField(
            model_name='goodtype',
            name='goods',
        ),

    ]