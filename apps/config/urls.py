from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False
router.register('faq', views.FaqContentViewSet)
router.register('notice', views.NoticeViewSet)
router.register('level', views.LevelViewSet)
router.register('rechargetype', views.RechargeTypeViewSet)


urlpatterns = [
    path('storename', views.StoreName.as_view()),
    path('storename/', views.StoreName.as_view()),
    path('storelogo/', views.StoreLogoAPI.as_view()),
    path('storeposter/', views.StorePosterAPI.as_view()),
    path('config', views.Config.as_view(), name='config'),
    path('marketing', views.MarketingView.as_view()),
    path('storeinfo/', views.StoreInfoAPI.as_view(), name='storeinfo'),
    path('wechatconfig/', views.WechatConfigView.as_view(), name='wechatconfig'),
    path('wxapp-qrcode/', views.WxAppQrCodeView.as_view()),
    path('', include(router.urls)),
]