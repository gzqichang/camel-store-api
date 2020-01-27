# usr/bin/env python
# -*- coding: utf-8 -*-
from django.conf.urls import url
from . import views

app_name = 'wxapp'
urlpatterns = [
    # 小程序端
    url(r'^login/$', views.WxLoginView.as_view(), name='login'),
    url(r'^userinfo/save/$', views.SaveUserInfoFromWxAppView.as_view(), name='userinfo-save'),
    url(r'^userinfo/create/$', views.CreateWxUserFromWxAppView.as_view(), name='userinfo-create')
]
