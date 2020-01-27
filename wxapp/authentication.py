# usr/bin/env python
# -*- coding: utf-8 -*-
from rest_framework import authentication
from rest_framework import exceptions
from .models import WxSession


class WxSessionAuthentication(authentication.BaseAuthentication):

    keyword = 'session'

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = '无效的Session头, session没有提供'
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = '无效的Session, session值不该包含空格'
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = 'Invalid token header. Token string should not contain invalid characters.'
            raise exceptions.AuthenticationFailed(msg)

        session = WxSession.get(token)
        if session is None:
            raise exceptions.AuthenticationFailed('401')

        user = session.user
        if user is None:
            raise exceptions.AuthenticationFailed('找不到对应的session用户')
        return user, session
