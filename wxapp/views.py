# usr/bin/env python
# -*- coding: utf-8 -*-
import uuid
import urllib.parse
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from .https import wx_config, wxapp_client
from .permissions import OnlyWxUser
from .authentication import WxSessionAuthentication
from .models import WxUser, WxSession, AccessToken
from .serializers import WxAppLoginSerializer, SaveUserInfoFromWxAppSerializer, CreateWxUserFromWxAppSerializer


class WxLoginView(views.APIView):
    serializer_class = WxAppLoginSerializer
    """ 微信登录
        Web端:
        1. 默认返回相应参数，供网站内嵌二维码微信登录JS实现
        2. ?login_origin=from_url: 返回跳转链接
        3. Get: {code: 'xxxx', auth_type: 'web'}  请求用户的session token

        APP端:
        1. Get: {code: 'xxxx', auth_type: 'app'}  请求用户的session token

        小程序端登录:
        POST:  post: {code: 'xxxxx'}
    """

    def get(self, request, *args, **kwargs):
        """ 获取登录链接 """
        if request.GET.get('code'):
            code = request.GET.get('code')
            auth_type = request.GET.get('auth_type', 'web')
            instance = AccessToken.update_access_token(code, auth_type=auth_type)
            if instance is None:
                return Response(dict(message='code 无效，请重新登录'), status=status.HTTP_401_UNAUTHORIZED)
            user = instance.user
            wxsession = WxSession.get_or_update_session(user)
            return Response(dict(session=wxsession.session))

        login_origin = request.GET.get('login_origin')
        host = 'https://open.weixin.qq.com/connect/qrconnect'
        redirect_uri = urllib.parse.quote(reverse('wxapp:login', request=request))
        params = {
            'appid': wx_config.get('WEB_APPID'),
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'snsapi_login',
            'state': uuid.uuid4().hex,
            'auth_type': 'web',
        }

        if login_origin == 'from_url':
            return Response('{}?{}#wechat_redirect'.format(host, urllib.parse.urlencode(params)))
        else:
            return Response(params)

    def post(self, request, *args, **kwargs):
        """ 小程序端获取登录 Session """
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


# v1版本中的保存用户信息
class SaveUserInfoFromWxAppView(views.APIView):
    serializer_class = SaveUserInfoFromWxAppSerializer
    permission_classes = (OnlyWxUser, )
    authentication_classes = (WxSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        if not getattr(request.user, 'is_wechat', False):
            return Response(dict(message='必须是微信用户登录'), status=status.HTTP_403_FORBIDDEN)
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response(dict(message='保存成功'))


# v2版本的小程序微信用户创建
class CreateWxUserFromWxAppView(views.APIView):
    serializer_class = CreateWxUserFromWxAppSerializer
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        return Response(dict(message='保存成功'))
