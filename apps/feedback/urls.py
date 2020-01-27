from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False
router.register('feedback', views.FeedBackViewSet)


urlpatterns = [
    path('', include(router.urls)),
]