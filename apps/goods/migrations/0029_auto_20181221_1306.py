# Generated by Django 2.1.4 on 2018-12-21 05:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0028_auto_20181220_1818'),
    ]

    operations = [
        migrations.RenameField(
            model_name='subgoods',
            old_name='create_time',
            new_name='add_time',
        ),
        migrations.RenameField(
            model_name='subgoods',
            old_name='gtype',
            new_name='gtypes',
        ),
        migrations.RenameField(
            model_name='subgoodstemplate',
            old_name='create_time',
            new_name='add_time',
        ),
        migrations.RenameField(
            model_name='subgoodstemplate',
            old_name='gtype',
            new_name='gtypes',
        ),
    ]