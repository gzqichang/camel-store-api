from wx_pay import base


class WxPayQueryClient(base.WxPayClient):
    def query(self, appid=None, transaction_id=None, out_trade_no=None):
        self.wx_pay_client.appid = appid
        return self.wx_pay_client.order.query(transaction_id, out_trade_no)
