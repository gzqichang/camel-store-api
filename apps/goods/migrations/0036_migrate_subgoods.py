from django.db import migrations, models
from django.db import transaction


def migrate_subgoods_to_goods(apps, schema_editor):
    # 将订阅商品中共有的基本信息迁移到商品信息表中
    Goods = apps.get_model("goods", "Goods")
    SubGoods = apps.get_model("goods", "SubGoods")
    Images = apps.get_model("goods", "Images")
    with transaction.atomic():
        for subgoods in SubGoods.objects.all():
            goods = Goods.objects.create(
                name=subgoods.name,
                category=subgoods.category,
                shop=subgoods.shop,
                goods_brief=subgoods.goods_brief,
                image=subgoods.image,
                poster=subgoods.poster,
                status=subgoods.status,
                index=subgoods.index,
                model_type='sub',
                delivery_method=subgoods.delivery_method,
                pick_up=subgoods.pick_up,
                postage_setup=subgoods.postage_setup,
                postage=subgoods.postage,
                add_time=subgoods.add_time,
            )
            goods.sub_goods = subgoods
            goods.save()
            for banner in subgoods.banners.all():
                goods.banner.add(Images.objects.create(image=banner.image, index=banner.index))
            for detail in subgoods.details.all():
                goods.detail.add(Images.objects.create(image=detail.image, index=detail.index))




class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0035_migrate_goods'),
    ]

    operations = [

        migrations.RunPython(migrate_subgoods_to_goods),

        # 删除特定商品中的通用字段
        migrations.AlterModelOptions(
            name='subgoods',
            options={'verbose_name': '订阅商品', 'verbose_name_plural': '订阅商品'},
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='add_time',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='banners',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='category',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='delivery_method',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='details',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='goods_brief',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='image',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='index',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='name',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='pick_up',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='postage',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='postage_setup',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='poster',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='shop',
        ),
        migrations.RemoveField(
            model_name='subgoods',
            name='status',
        ),

        migrations.RemoveField(
            model_name='subgoodsimage',
            name='image',
        ),
        migrations.DeleteModel(
            name='SubGoodsImage',
        ),
    ]