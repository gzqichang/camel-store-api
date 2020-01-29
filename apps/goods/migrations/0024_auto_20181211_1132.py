# Generated by Django 2.1.2 on 2018-12-11 03:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0001_initial'),
        ('goods', '0023_auto_20181203_1734'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='goods',
            name='a_type',
        ),
        migrations.RemoveField(
            model_name='goods',
            name='asset_ratio_1',
        ),
        migrations.RemoveField(
            model_name='goods',
            name='asset_ratio_2',
        ),
        migrations.RemoveField(
            model_name='goods',
            name='city',
        ),
        migrations.RemoveField(
            model_name='goodtype',
            name='asset_ratio',
        ),
        migrations.AddField(
            model_name='banner',
            name='shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='shop.Shop', verbose_name='所属店铺'),
        ),
        migrations.AddField(
            model_name='goods',
            name='is_template',
            field=models.BooleanField(default=False, verbose_name='是否是模板'),
        ),
        migrations.AddField(
            model_name='goods',
            name='shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='shop.Shop', verbose_name='所属店铺'),
        ),
        migrations.AddField(
            model_name='goodscategory',
            name='shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='shop.Shop', verbose_name='所属店铺'),
        ),
        migrations.AlterField(
            model_name='goods',
            name='image',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='image', to='qfile.File', verbose_name='封面图'),
        ),
        migrations.AlterField(
            model_name='goods',
            name='poster',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='poster', to='qfile.File', verbose_name='海报模板'),
        ),
    ]