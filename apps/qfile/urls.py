from rest_framework import routers
from django.urls import path, include

from . import views


router = routers.SimpleRouter()
router.register("file", views.FileViewSet, basename="file")
router.register("tag", views.TagViewSet, basename="tag")

urlpatterns = [
    path('', include(router.urls)),
]
