from django.db import migrations


def create_invoice_switch_config(apps, schema_editor):
    BoolConfig = apps.get_model("config", "BoolConfig")
    obj, created = BoolConfig.objects.get_or_create(
        name='invoice_switch',
        defaults={'content': 'true'},
    )
    obj.label = '是否显示发票'
    obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0032_video_switch'),
    ]

    operations = [
        migrations.RunPython(create_invoice_switch_config),
    ]
