from django.conf import settings

from wx_pay import base
from wx_pay.utils import qr_code


class WxPayOrderClient(base.WxPayClient):
    def create(self, **kwargs):
        channel = kwargs.get("channel")

        self.set_appid(channel=channel)
        kwargs["notify_url"] = self.set_notify_url(kwargs.get("notify_url"))

        if channel in ["wx_pub_qr"]:
            return self.qr_create(**kwargs)
        elif channel in ["wx_lite"]:
            return self.wx_lite_create(**kwargs)

    def perform_create(self, **kwargs):
        return super().create(**kwargs)

    def qr_create(self, **kwargs):
        instance = self.perform_create(**kwargs)
        return self.add_base64_qr_code(instance)

    def wx_lite_create(self, **kwargs):
        instance = self.perform_create(**kwargs)
        return self.generate_credential(instance)

    @staticmethod
    def set_notify_url(notify_url):
        if not notify_url:
            try:
                return settings.WX_PAY_NOTIFY_URL
            except AttributeError:
                raise AttributeError("notify url 参数错误")
        return notify_url

    @staticmethod
    def add_base64_qr_code(instance):
        base64_qr_cde = qr_code.generate_base64_qr_code(instance.get("code_url"))
        instance["base64_qr_cde"] = base64_qr_cde
        return instance

    def generate_credential(self, instance):
        return self.wx_pay_client.jsapi.get_jsapi_params(instance.get("prepay_id"))
