from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views


router = SimpleRouter()
# router.register('smsrecord', views.SmsRecordViewSet, basename='smsrecord')


urlpatterns = [
    # path('sms_balance/', views.SmsBalanceView.as_view(), name='sms_balance'),
    # path('recharge/', views.SmsRecharge.as_view(), name='sms_recharge'),
    # path('smsrechargefaefaefageafaweg/', views.SmsRechargeCallback.as_view(), name='smscallback'),
    # path('sms_switch/', views.SmsSwitchView.as_view(), name='sms_switch'),
    path('', include(router.urls)),
]
