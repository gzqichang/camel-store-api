from django.urls import path, include
from django.conf import settings
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False
router.register('user', views.UserViewSet)
router.register('group', views.GroupViewSet)


urlpatterns = [
    path('change-password/', views.UserChangePasswordView.as_view(), name='admin-change-password'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('', include(router.urls)),
]

