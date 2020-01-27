from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False

# 打印员
router.register('printer', views.DeliveryPrinterViewSet)

# 账号管理
router.register('account', views.DeliveryAccountViewSet)

# 发件人地址管理
router.register('address', views.SenderViewSet)


urlpatterns = [
    path('', include(router.urls)),

    # 下单接口
    path('get-all-delivery/', views.AllDeliveryView.as_view()),
    path('get-order/', views.DeliveryOrderView.as_view()),
    path('cancel-order/', views.CancelOrderView.as_view()),
    path('add-order/', views.AddOrderView.as_view()),

    # 查询运单轨迹
    path('get-path/', views.DeliveryPathView.as_view()),

    # 获取电子面单余额。仅在使用加盟类快递公司时，才可以调用
    path('get-quota/', views.QuotaView.as_view()),
]
