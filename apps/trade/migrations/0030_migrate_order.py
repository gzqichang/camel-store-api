from django.db import migrations, models
import django.db.models.deletion
from django.db import transaction


def migrate_order(apps, schema_editor):
    Order = apps.get_model("trade", "Order")

    DeliveryAddress = apps.get_model("trade", "DeliveryAddress")
    Invoice = apps.get_model("trade", "Invoice")
    Items = apps.get_model("trade", "Items")

    GoodsBackup = apps.get_model("trade", "GoodsBackup")
    Orders = apps.get_model("trade", "Orders")

    with transaction.atomic():
        for order in Order.objects.all():
            address = DeliveryAddress.objects.create(address_info=order.address_info,
                                                     sign_name=order.signer_name,
                                                     mobile_phone=order.singer_mobile)
            invoice = Invoice.objects.create(invoice_type=order.inv_type, title=order.inv_title,
                                             taxNumber=order.inv_taxNumber, companyAddress=order.inv_companyAddress,
                                             telephone=order.inv_telephone, bankName=order.inv_bankName,
                                             bankAccount=order.inv_bankAccount)

            instance = Orders.objects.create(user=order.user, shop=order.shop, order_sn=order.order_sn,
                                             trade_no=order.trade_no, remark=order.remark, status=order.status,
                                             order_amount=order.order_mount, postage_total=order.postage_total,
                                             real_amount=order.real_mount,
                                             asset_pay=order.asset_pay, recharge_pay=order.recharge_pay,
                                             discount=order.discount, pay_time=order.pay_time,
                                             flag_time=order.flag_time, invoice=invoice,
                                             delivery_address=address, add_time=order.add_time)
            for i in order.items.all():
                goodsbackup = GoodsBackup.objects.create(order=instance, goods=i.goods, gtype_id=getattr(i.gtype, 'id', None), goods_name=i.goods_name,
                                                         gtype_name=i.gtype_name, g_image=i.g_image, price=i.price,
                                                         original_price=i.original_price, market_price=i.market_price, num=i.num,
                                                         share_user_id=i.share_user_id, g_rebate=i.g_rebate, g_bonus=i.g_bonus,
                                                         delivery_method='express')
                item = Items.objects.create(order=instance, goods_backup=goodsbackup, send_type=i.status,
                                            express_num=i.express_num,
                                            express_company=i.express_company, send_time=i.send_time,
                                            receive_time=i.receive_time,
                                            flag_time=i.flag_time)


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('trade', '0029_auto_20190107_2141'),

    ]

    operations = [
        migrations.RunPython(migrate_order),

    ]
