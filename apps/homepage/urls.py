from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False
router.register('homebanner', views.HomeBannerViewSet)
router.register('shortcut', views.ShortcutViewSet)
router.register('module', views.ModuleViewSet)

urlpatterns = [
    path('', include(router.urls)),
]