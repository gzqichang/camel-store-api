from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import views, status, decorators, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework.reverse import reverse
from wx_pay.unified import WxPayOrderClient
from wx_pay.utils import dict_to_xml
from apps.utils.parser import TextTypeXMLParser
from .serializers import SmsRecordSerializer
from .models import SmsSwitch, SmsBalance, SMSRechargeRecord, SmsRecord
# Create your views here.


# todo: 暂时去除短信服务
# class SmsBalanceView(views.APIView):
#     permission_classes = [IsAdminUser]
#
#     def get(self, request, *args, **kwargs):
#         instance = SmsBalance.get()
#         return Response(instance.num)
#
#
# class SmsRecharge(views.APIView):
#     """
#     post:
#     {
#         "amount": 100
#     }
#     """
#     permission_classes = [IsAdminUser]
#
#     def post(self, request, *args, **kwargs):
#         amount = request.data.get('amount')
#         try:
#             amount = int(amount)
#         except ValueError:
#             return Response('参数错误', status=status.HTTP_400_BAD_REQUEST)
#         instance = SMSRechargeRecord.create(amount)
#         appid = settings.QICAHNG_APP_ID
#         api_key = settings.QICAHNG_API_KEY
#         mch_id = settings.QICAHNG_MCH_ID
#         mch_cert = settings.QICAHNG_MCH_CERT
#         mch_key = settings.QICAHNG_MCH_KEY
#         client = WxPayOrderClient(appid=appid, api_key=api_key, mch_id=mch_id, mch_cert=mch_cert, mch_key=mch_key)
#         res = client.create(channel='wx_pub_qr', body='短信充值', attach='sms', out_trade_no=instance.out_trade_no,
#                             fee_type="CNY", total_fee=instance.amount * 100, client_ip=request.META['REMOTE_ADDR'],
#                             notify_url=reverse('smscallback', request=request),
#                             product_id=100000)
#         return Response(res)
#
#
# class SmsRechargeCallback(views.APIView):
#     parser_classes = (TextTypeXMLParser,)
#     permission_classes = []
#
#     def post(self, request, *args, **kwargs):
#         data = request.data
#         transaction_id = data.get("transaction_id")
#         out_trade_no = data.get("out_trade_no")
#         instance = SMSRechargeRecord.objects.get(out_trade_no=out_trade_no)
#         if not instance.has_paid:
#             instance.transaction_id = transaction_id
#             instance.has_paid = True
#             instance.paid_time = timezone.now()
#             instance.save()
#             balance = SmsBalance.get()
#             balance.num += instance.num
#             balance.save()
#         return HttpResponse(dict_to_xml({"return_code": "SUCCESS"}), content_type='application/xml')
#
#
# class SmsSwitchView(views.APIView):
#     """
#     post:
#     {\n
#         "sms_type": "daily_remind"
#         "switch": "true"
#     }
#     """
#
#     permission_classes = [IsAdminUser]
#
#     def get(self, request, *args, **kwargs):
#         res = []
#         for switch in SmsSwitch.objects.all():
#             res.append({'label': switch.label, 'sms_type': switch.sms_type, 'switch': switch.switch})
#         return Response(res)
#
#     def post(self, request, *args, **kwargs):
#         sms_type = request.data.get('sms_type')
#         switch = request.data.get('switch')
#         if sms_type not in list(SmsSwitch.objects.values_list('sms_type', flat=True)):
#             return Response('参数错误', status=status.HTTP_400_BAD_REQUEST)
#         sms_switch = SmsSwitch.objects.get(sms_type=sms_type)
#         if switch == 'true':
#             sms_switch.switch = True
#         else:
#             sms_switch.switch = False
#         sms_switch.save()
#         return Response('短信设置修改完成')
#
#
# class SmsRecordViewSet(viewsets.ModelViewSet):
#     serializer_class = SmsRecordSerializer
#     queryset = SmsRecord.objects.all()
#     permission_classes = [IsAdminUser]