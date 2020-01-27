from django.conf import settings
from apps.utils.send_email import send_email
from apps.sms.models import SmsSwitch
from apps.sms.send_sms import send_sms
from .models import User


def remind_new_order(shop):
    """
    新待处理订单通知
    """
    if not shop:
        return
    manage = []
    for admin in User.objects.filter(shop=shop):
        if admin.email:
            manage.append(admin.email)
        if admin.phone and SmsSwitch.get('order_notice'):
            send_sms(admin.phone, {"business": getattr(settings, 'SHOP_NAME')}, 'SMS_157070785')
    if manage:
        store = getattr(settings, 'SHOP_NAME')
        text_content = f"【骆驼小店】尊敬的{store}商家你好，您的小店有新的订单，请登录管理后台及时处理和发货。"
        html = text_content
        send_email('新订单通知', text_content, html, manage)


def remind_lower_shelf(shop, goods_name):
    """
    商品下架短信提醒
    """
    if not SmsSwitch.get('exhaustion_notice'):
        return
    if not shop:
        return
    for admin in User.objects.filter(shop=shop):
        if admin.phone:
            store = getattr(settings, 'SHOP_NAME')
            send_sms(admin.phone, {"business": store, "commodity": goods_name},
                     'SMS_157070808')
