import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0053_migrate_delivery_method'),
    ]

    operations = [

        migrations.RemoveField(
            model_name='goods',
            name='delivery_method',
        ),
        migrations.RemoveField(
            model_name='goods',
            name='pick_up',
        ),
        migrations.RenameField(
            model_name='goods',
            old_name='delivery_method_list',
            new_name='delivery_method',
        ),
    ]
