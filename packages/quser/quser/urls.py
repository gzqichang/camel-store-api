from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

app_name = "quser"

router = SimpleRouter()
router.register('users', views.UserViewSet, basename='user')
router.register('groups', views.GroupViewSet, basename='group')


urlpatterns = [
    path('captcha-generate/', views.CaptchaView.as_view(), name='captcha'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('change-password/', views.UserChangePasswordView.as_view(), name='change-password'),

    path('', include(router.urls)),
]
