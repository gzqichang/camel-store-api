from django.db import migrations


def sms_switch_config(apps, schema_editor):
    SmsSwitch = apps.get_model("sms", "SmsSwitch")
    SmsSwitch.objects.get_or_create(label='下单通知', sms_type='order_notice', defaults={'switch': True})
    SmsSwitch.objects.get_or_create(label='后台管理每日提醒', sms_type='daily_remind', defaults={'switch': True})
    SmsSwitch.objects.get_or_create(label='反馈通知', sms_type='feedback_notice', defaults={'switch': True})
    SmsSwitch.objects.get_or_create(label='发货通知', sms_type='delivery_notice', defaults={'switch': True})
    SmsSwitch.objects.get_or_create(label='下架通知', sms_type='exhaustion_notice', defaults={'switch': True})



class Migration(migrations.Migration):

    dependencies = [
        ('sms', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(sms_switch_config),
    ]