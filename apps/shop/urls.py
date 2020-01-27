from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False
router.register('shop', views.ShopViewSet)


urlpatterns = [
    path('daily_remind/', views.DailyRemindAPI.as_view()),
    path('', include(router.urls)),
]