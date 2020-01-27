from django.db import migrations, transaction


@transaction.atomic()
def migrate_old_printer_data(apps, schema_editor):
    Printer = apps.get_model('shop', 'Printer')
    QrCode = apps.get_model('shop', 'QrCode')
    old_data = Printer.objects.all()
    if not old_data:
        return
    for printer in old_data:
        if printer.shop:
            QrCode.objects.create(
                shop=printer.shop,
                device=printer,
                qrcode_url=printer.qrcode_url,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0011_auto_20190527_1522'),
    ]

    operations = [
        migrations.RunPython(migrate_old_printer_data),
        migrations.RemoveField(
            model_name='printer',
            name='qrcode_url',
        ),
        migrations.RemoveField(
            model_name='printer',
            name='shop',
        ),
    ]
