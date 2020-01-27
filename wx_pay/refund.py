from wx_pay import base
from django.conf import settings

class WxRefundClient(base.WxPayClient):

    def refund(self, total_fee, refund_fee, out_refund_no, transaction_id=None, out_trade_no=None, fee_type='CNY',
               notify_url=None):

        if not isinstance(total_fee, int):
            raise ValueError('金额必须为单位为分，且必须为整数')

        if not isinstance(refund_fee, int):
            raise ValueError('金额必须为单位为分，且必须为整数')

        if refund_fee > total_fee:
            raise ValueError("退款金额不能大于订单总金额")

        if not transaction_id and not out_trade_no:
            raise ValueError("请至少携带订单号或微信流水号")

        notify_url = notify_url if notify_url else getattr(settings, 'REFUND_NOTIFY_URL', None)

        kwargs = {
            'total_fee': total_fee,
            'refund_fee': refund_fee,
            'out_refund_no': out_refund_no,
            'transaction_id': transaction_id,
            'out_trade_no': out_trade_no,
            'fee_type': fee_type,
            'notify_url': notify_url
        }


        self.wx_pay_client.appid = getattr(settings, 'WX_PAY_WXA_APP_ID')
        return self.wx_pay_client.refund.apply(**kwargs)

    def query(self, appid=None, refund_id=None, out_refund_no=None, transaction_id=None, out_trade_no=None):
        self.wx_pay_client.appid = appid
        return self.wx_pay_client.refund.query(refund_id, out_refund_no, transaction_id, out_trade_no)
