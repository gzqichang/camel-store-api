from wx_pay import base
from django.conf import settings

class WxPayCloseClient(base.WxPayClient):

    def close_order(self, appid=None, out_trade_no=None):

        self.wx_pay_client.appid = getattr(settings, 'WX_PAY_WXA_APP_ID')
        return self.wx_pay_client.order.close(out_trade_no)