from django.db import migrations



def create_sms_service_config(apps, schema_editor):
    BoolConfig = apps.get_model("config", "BoolConfig")
    open_buy, created = BoolConfig.objects.get_or_create(name='sms_service', defaults={'content': 'true'})
    open_buy.label = '是否开启短信服务'
    open_buy.save()


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0023_show_copyright'),
    ]

    operations = [
        migrations.RunPython(create_sms_service_config),
    ]