from rest_framework import routers
from django.urls import path, include

from . import views


router = routers.SimpleRouter()
router.register("video", views.ShortVideoViewSet, basename="shortvideo")


urlpatterns = [
    path('switch/', views.SwitchViews.as_view(), name='video_switch'),
    path('', include(router.urls)),
]
