from django.db import migrations, models
from django.db import transaction


def migrate_banner(apps, schema_editor):
    # 首页轮播图数据迁移
    Banner = apps.get_model("goods", "Banner")

    with transaction.atomic():
        for banner in Banner.objects.all():
            if banner.subgoods:
                try:
                    banner.goods = banner.subgoods.goods
                    banner.save()
                except AttributeError:
                    continue


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0036_migrate_subgoods'),
    ]

    operations = [

        migrations.RunPython(migrate_banner),

        migrations.RemoveField(
            model_name='banner',
            name='goods_type',
        ),
        migrations.RemoveField(
            model_name='banner',
            name='subgoods',
        ),

    ]