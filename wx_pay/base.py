from django.conf import settings

from wechatpy import WeChatPay


class WxPayBaseClient(object):
    def __init__(self, appid, api_key, mch_id, sub_mch_id=None, mch_cert=None, mch_key=None):
        self.wx_pay_client = WeChatPay(appid, api_key, mch_id, sub_mch_id, mch_cert, mch_key)

    def create(
            self, channel, body, total_fee, notify_url, client_ip=None, openid=None, out_trade_no=None, detail=None,
            attach=None, fee_type=None, time_start=None, time_expire=None, goods_tag=None, product_id=None,
            device_info=None, limit_pay=None, scene_info=None
    ):

        assert isinstance(total_fee, int), "金额必须为单位为分，且必须为整数"
        if fee_type is None:
            fee_type = 'CNY'

        trade_type = self.get_trade_type(channel)

        data = {
            'trade_type': trade_type,
            'body': body,
            'total_fee': total_fee,
            'notify_url': notify_url,
            'detail': detail,
            'out_trade_no': out_trade_no,
            'device_info': device_info,
            'attach': attach,
            'fee_type': fee_type,
            'client_ip': client_ip,
            'time_start': time_start,
            'time_expire': time_expire,
            'goods_tag': goods_tag,
            'limit_pay': limit_pay,
            'product_id': product_id,
            'user_id': openid,
            'scene_info': scene_info,
        }
        self.assert_required_params(channel, data)

        return self.wx_pay_client.order.create(**data)

    @staticmethod
    def get_trade_type(channel):
        if channel in ["wx_lite"]:
            trade_type = "JSAPI"
        elif channel in ["wx_pub_qr"]:
            trade_type = "NATIVE"
        else:
            raise ValueError("请传入正确的渠道值")

        return trade_type

    @staticmethod
    def assert_required_params(channel, data):
        # Todo 后期改为用 trade type处理
        if channel in ["wx_lite"]:
            param = "user_id"
        elif channel in ["wx_pub_qr"]:
            param = "product_id"
        else:
            return True

        param_required = data.get(param, None)
        assert param_required, "此交易渠道下，{}参数必须包含且不为空".format(param)


class WxPayClient(WxPayBaseClient):
    def __init__(self, appid=None,  api_key=None, mch_id=None, sub_mch_id=None, mch_cert=None, mch_key=None):
        """
        :param appid: 微信公众号或者小程序 appid
        :param api_key: 商户 key
        :param mch_id: 商户号
        :param sub_mch_id: 可选，子商户号，受理模式下必填
        :param mch_cert: 商户证书路径
        :param mch_key: 商户证书私钥路径
        """
        try:
            appid = appid
            api_key = api_key or settings.WX_PAY_API_KEY
            mch_id = mch_id or settings.WX_PAY_MCH_ID
            sub_mch_id = sub_mch_id or settings.WX_PAY_SUB_MCH_ID
            mch_cert = mch_cert or settings.WX_PAY_MCH_CERT
            mch_key = mch_key or settings.WX_PAY_MCH_KEY
        except AttributeError:
            raise AttributeError("配置参数错误")

        super().__init__(appid, api_key, mch_id, sub_mch_id, mch_cert, mch_key)

    def set_appid(self, appid=None, channel=None):
        if not self.wx_pay_client.appid:
            if appid:
                self.wx_pay_client.app = appid
            else:
                try:
                    if channel in ["wx_lite"]:
                        self.wx_pay_client.appid = settings.WX_PAY_WXA_APP_ID
                    else:
                        self.wx_pay_client.appid = settings.WX_PAY_APP_ID
                except AttributeError:
                    raise AttributeError("APP ID 参数错误")
