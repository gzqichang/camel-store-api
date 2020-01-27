from wechatpy import WeChatPay

from wx_pay.pay import api


class CustomWeChatPay(WeChatPay):
    custom_order = api.CustomWeChatOrder
