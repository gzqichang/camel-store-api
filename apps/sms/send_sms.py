from django.conf import settings
from qsmstoken.clients.aliyunsms import AliyunSMSClient
from threading import Thread

from apps.config.models import BoolConfig
from .models import SmsRecord, SmsBalance


# def async_send(phone, params, template_code):
#     client = AliyunSMSClient(settings.SMS_CONFIG)
#     client.send_sms(phone, params, template_code)


def send_sms(phone, params, template_code):
    return
    # instance = SmsBalance.get()
    # if BoolConfig.get_bool('sms_service') and instance.num > 0:
    #     instance.num -= 1
    #     instance.save()
    #     SmsRecord.objects.create(phone=phone, model_code=template_code)
    #     send_sms_task = Thread(target=async_send, args=(phone, params, template_code))
    #     send_sms_task.start()
    #     return
