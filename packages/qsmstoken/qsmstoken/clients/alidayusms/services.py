# usr/bin/env python
# -*- coding: utf-8 -*-
import json
import top.api
from ..base import BaseSMSClient


class AlidayuSMSClient(BaseSMSClient):

    def __init__(self, sms_config):
        super().__init__(sms_config)
        self.req = top.api.AlibabaAliqinFcSmsNumSendRequest()
        self.req.set_app_info(top.appinfo(self.access_key, self.secret_key))

    def send_sms(self, phone, params, template_code, *args, **kwargs):
        self.req.extend = kwargs.pop("extend", "")
        self.req.sms_type = kwargs.pop("type", "normal")
        self.req.sms_free_sign_name = kwargs.pop("sign_name", self.sign_name)
        self.req.sms_param = json.dumps(params)
        self.req.rec_num = phone
        self.req.sms_template_code = template_code
        name = "alibaba_aliqin_fc_sms_num_send_response"
        try:
            resp = self.req.getResponse()
            print(resp)
            return 1, resp[name].get("msg", "succ")
        except Exception as e:
            print(e)
            return 0, e.submsg