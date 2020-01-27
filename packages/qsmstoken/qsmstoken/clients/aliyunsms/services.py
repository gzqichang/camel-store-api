# usr/bin/env python
# -*- coding: utf-8 -*-
import uuid
import json
from django.conf import settings
from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
from aliyunsdkcore.client import AcsClient
from ..base import BaseSMSClient


class AliyunSMSClient(BaseSMSClient):

    def __init__(self, sms_config):
        super().__init__(sms_config)
        self.region = sms_config.get('REGION', 'cn-hangzhou')
        self.client = AcsClient(self.access_key, self.secret_key, self.region)

    def send_sms(self, phone, params, template_code, *args, **kwargs):
        smsRequest = SendSmsRequest.SendSmsRequest()
        # 申请的短信模板编码,必填
        smsRequest.set_TemplateCode(template_code)

        # 短信模板变量参数
        template_param = params
        if template_param is not None:
            if isinstance(template_param, dict):
                template_param = json.dumps(template_param)
            smsRequest.set_TemplateParam(template_param)

        # 设置业务请求流水号，必填。
        smsRequest.set_OutId(uuid.uuid1())
        # 短信签名
        smsRequest.set_SignName(kwargs.get('sign_name', self.sign_name))
        # 短信发送的号码列表，必填。
        smsRequest.set_PhoneNumbers(phone)
        # 调用短信发送接口，返回json
        smsResponse = self.client.do_action_with_exception(smsRequest)
        # TODO 业务处理
        return smsResponse

    def test_send_sms(self, phone):
        sign_name = '阿里云短信测试专用'
        template_code = 'SMS_73105023'
        params = {'customer': "短信测试员"}
        return self.send_sms(phone, sign_name, template_code, params)

