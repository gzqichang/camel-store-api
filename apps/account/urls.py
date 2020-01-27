from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False
router.register('userinfo', views.WxUserInfoViewSet)
router.register('accountlog', views.AccountLogViewSet)
router.register('creditlog', views.WxUserCreditLogViewSet)
router.register('withdrawal', views.WithdrawViewSet)
router.register('operationlog', views.WithdrawOperationLogViewSet)
router.register('rchgrecord', views.RechargeRecordViewSet)


urlpatterns = [
    path('create_withdrawal/', views.WithdrawCreate.as_view(), name='create_withdrawal'),
    path('recharge', views.Recharge.as_view(), name='recharge'),
    path('', include(router.urls)),
]