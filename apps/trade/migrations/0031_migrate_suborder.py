from django.db import migrations, models
import django.db.models.deletion
from django.db import transaction


def migrate_suborder(apps, schema_editor):
    SubOrder = apps.get_model("trade", "SubOrder")

    DeliveryAddress = apps.get_model("trade", "DeliveryAddress")
    Invoice = apps.get_model("trade", "Invoice")
    Items = apps.get_model("trade", "Items")
    SubGoodsBackup = apps.get_model("trade", "SubGoodsBackup")
    GoodsBackup = apps.get_model("trade", "GoodsBackup")
    Orders = apps.get_model("trade", "Orders")

    with transaction.atomic():
        for order in SubOrder.objects.all():
            address = DeliveryAddress.objects.create(address_info=order.address_info,
                                                     sign_name=order.signer_name,
                                                     mobile_phone=order.singer_mobile)
            invoice = Invoice.objects.create(invoice_type=order.inv_type, title=order.inv_title,
                                             taxNumber=order.inv_taxNumber, companyAddress=order.inv_companyAddress,
                                             telephone=order.inv_telephone, bankName=order.inv_bankName,
                                             bankAccount=order.inv_bankAccount)

            status = {0: 'serving', 1: 'paying', 2: 'done', 3: 'close'}.get(order.status)
            instance = Orders.objects.create(user=order.user, shop=order.shop, order_sn=order.order_sn,
                                             trade_no=order.trade_no, remark=order.remark, status=status,
                                             order_amount=order.order_mount, postage_total=order.postage,
                                             real_amount=order.real_mount, model_type='sub',
                                             asset_pay=order.asset_pay, recharge_pay=order.recharge_pay,
                                             discount=order.discount, pay_time=order.pay_time,
                                             flag_time=order.flag_time,
                                             invoice=invoice, next_send=order.next_send,
                                             delivery_address=address, add_time=order.add_time)
            sub_goods_info = SubGoodsBackup.objects.create(cycle_num=order.cycle_num,
                                                           delivery_setup=order.delivery_setup,
                                                           date_setup=order.date_setup,
                                                           delivery_data=order.delivery_data,
                                                           interval=order.interval,
                                                           start_send_date=order.start_send_date,
                                                           send_start_time=order.send_start_time,
                                                           send_end_time=order.send_end_time)
            goodsbackup = GoodsBackup.objects.create(order=instance, gtype_id=getattr(order.gtype, 'id', None),
                                                     goods_name=order.goods_name,
                                                     gtype_name=order.gtype_name, g_image=order.g_image,
                                                     price=order.price,
                                                     original_price=order.original_price,
                                                     market_price=order.market_price, delivery_method=order.delivery_method,
                                                     num=1, sub_goods_info=sub_goods_info)
            for i in order.items.all():
                item = Items.objects.create(order=instance, goods_backup=goodsbackup, cycle=i.cycle,
                                            send_date=i.send_date, send_start=i.send_start, send_end=i.send_end,
                                            send_type=i.send_type, express_num=i.express_num,
                                            express_company=i.express_company, send_time=i.send_time,
                                            receive_time=i.receive_time,
                                            flag_time=i.flag_time)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('trade', '0030_migrate_order'),

    ]

    operations = [

        migrations.RunPython(migrate_suborder),
    ]
