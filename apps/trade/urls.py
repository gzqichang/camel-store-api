from django.urls import path, include
from django.conf import settings
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.include_root_view = False
router.register('address', views.UserAddressViewSet)
router.register('express', views.ExpressViewSet)
router.register('delivery', views.DeliveryAddressViewSet)
router.register('order', views.OrdersViewSet)
router.register('item', views.ItemsViewSet)

urlpatterns = [
    path('wechatpay/', views.Wechatpay.as_view(), name='wechatpay'),
    path('468468418416846841684a6efaefa/', views.PayCallback.as_view(), name='paycallback'),
    path('pull_pay_result/', views.PullPayResult.as_view(), name='pull-pay-result'),
    path('cancel_order/', views.CancelOrder.as_view(), name='cance_lorder'),
    path('confirm_receipt/', views.ConfirmReceipt.as_view(), name='confirm_receipt'),
    path('cartbuy/', views.CartBuyView.as_view(), name='cartbuy'),
    path('replace/', views.ReplaceGoodsView.as_view(), name='replace'),
    path('batch-export/', views.ExportBatchDeliveryView.as_view(), name='batch-export'),
    path('batch-export-query/', views.QueryBatchDeliveryView.as_view(), name='batch-export-query'),
    path('', include(router.urls)),
]
