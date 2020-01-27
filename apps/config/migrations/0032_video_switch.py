from django.db import migrations


def create_video_switch_config(apps, schema_editor):
    BoolConfig = apps.get_model("config", "BoolConfig")
    obj, created = BoolConfig.objects.get_or_create(
        name='video_switch',
        defaults={'content': 'true'},
    )
    obj.label = '是否显示短视频'
    obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('config', '0031_datetime_config'),
    ]

    operations = [
        migrations.RunPython(create_video_switch_config),
    ]
