from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False
router.register('ptinfo', views.GroupBuyInfoViewSet)
router.register('ptgroup', views.PtGroupViewSet)


urlpatterns = [
    path('settlement/',  views.Settlement.as_view(), name='settlement'),
    path('', include(router.urls)),
]