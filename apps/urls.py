from django.urls import path, include, re_path
from django.contrib import admin
from rest_framework.documentation import include_docs_urls
from django.conf import settings
from . import views

urlpatterns = [
    path('sitemap/', views.SitemapView.as_view(), name='sitemap'),
    re_path('ws/(\S*)', views.TencentLbs.as_view()),
    path('web-hook/', views.WebHookView.as_view(), name='web-hook'),
    path('goods/', include('apps.goods.urls')),
    path('pt/', include('apps.group_buy.urls')),
    path('image/', include('apps.qfile.urls')),
    path('wxapp/', include('wxapp.urls', namespace='wxapp')),
    path('wxuser/', include('apps.account.urls')),
    path('logistics/', include('apps.wx_logistics.urls')),
    path('trade/', include('apps.trade.urls')),
    path('config/', include('apps.config.urls')),
    path('quser/', include('quser.urls')),
    path('count/', include('apps.count.urls')),
    path('shop/', include('apps.shop.urls')),
    path('user/', include('apps.user.urls')),
    path('feedback/', include('apps.feedback.urls')),
    path('homepage/', include('apps.homepage.urls')),
    path('video/', include('apps.short_video.urls')),
    path('sms/', include('apps.sms.urls')),
    #
]

urlpatterns += [
    path('django_admin/', admin.site.urls),
    path('captcha/', include('captcha.urls')),
]

if settings.DEBUG:
    urlpatterns.append(path('auth/', include('rest_framework.urls', namespace='rest_framework')))
    urlpatterns.append(path('doc/', include_docs_urls()))
