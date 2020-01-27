# usr/bin/env python
# -*- coding: utf-8 -*-
from rest_framework import serializers
from wxapp.https import wxapp_client
from .models import WxUser, WxSession
from qapi.utils import generate_fields


class WxAppLoginSerializer(serializers.Serializer):
    code = serializers.CharField(label='code', required=True)
    userinfo = serializers.DictField(label='userinfo', required=False)

    wxuser = None
    wxsession = None

    def create(self, validated_data):
        return None

    def update(self, instance, validated_data):
        return None

    def validate_code(self, value):
        succ, res = wxapp_client.get_session_key(value)
        if 'errcode' in res:
            raise serializers.ValidationError(res)
        else:
            open_id = res.get('openid')
            session_key = res.get('session_key')
            expires_in = res.get('expires_in', 7200)
            wxuser, created = WxUser.objects.get_or_create(wx_app_openid=open_id)
            wxsession = WxSession.get_or_update_session(wxuser, session_key, open_id, expires_in)
            self.wxuser = wxuser
            self.wxsession = wxsession
        return value

    def validate(self, attrs):
        userinfo = attrs.get('userinfo', {})
        raw_data = userinfo.get('rawData')
        signature = userinfo.get('signature')
        if self.wxsession is None:
            raise serializers.ValidationError('登录失败, 获取不到 session')
        session_key = self.wxsession.session_key
        if raw_data and signature and not WxUser.check_signature(session_key, raw_data, signature):
            raise serializers.ValidationError('用户信息签名与微信服务器返回不一致')
        return attrs

    def save(self, **kwargs):
        userinfo = self.validated_data.get('userinfo', {})
        user_info = userinfo.get('userInfo')
        encrypted_data = userinfo.get('encryptedData')
        iv = userinfo.get('iv')
        wxuser = self.wxuser
        if encrypted_data and iv:
            wxuser.save_from_encrypted_data(encrypted_data, iv)
        elif user_info:
            user_data = {
                'nickname': user_info.get('nickName', ''),
                'avatar_url': user_info.get('avatarUrl', ''),
                'language': user_info.get('language', ''),
                'gender': user_info.get('gender', 0),
                'province': user_info.get('province', ''),
                'city': user_info.get('city', ''),
                'country': user_info.get('country', '')
            }
            wxuser.update_info(user_data)

        user_serializer = WxUserSerializer(wxuser, context=self.context)
        data = user_serializer.data
        data.update({
            'session': wxuser.session.session
        })
        return data


class WxUserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = WxUser
        fields = ('id', 'web_openid', 'app_openid', 'wx_app_openid', 'nickname', 'avatar_url', 'language',
                  'gender', 'province', 'city', 'country', 'date_joined', 'qrcode_url')
        exclude = ()


class SaveUserInfoFromWxAppSerializer(serializers.Serializer):
    raw_data = serializers.CharField(label='rawData')
    signature = serializers.CharField(label='signature')
    encrypted_data = serializers.CharField(label='encryptedData')
    iv = serializers.CharField(label='iv')

    def validate(self, attrs):
        raw_data = attrs.get('raw_data')
        signature = attrs.get('signature')
        request = self.context.get('request')
        if request and getattr(request.user, 'is_wechat', None):
            session_key = request.user.session.session_key
            if not WxUser.check_signature(session_key, raw_data, signature):
                raise serializers.ValidationError('用户信息签名与微信服务器返回不一致')
            return attrs
        else:
            raise serializers.ValidationError('必须登录微信')

    def save(self, **kwargs):
        request = self.context.get('request')
        encrypted_data = self.validated_data['encrypted_data']
        iv = self.validated_data['iv']
        request.user.save_from_encrypted_data(encrypted_data, iv)
        return request.user


class CreateWxUserFromWxAppSerializer(serializers.Serializer):
    raw_data = serializers.CharField(label='rawData')
    signature = serializers.CharField(label='signature')
    encrypted_data = serializers.CharField(label='encryptedData')
    iv = serializers.CharField(label='iv')
    session = serializers.CharField(label='session')

    def validate(self, attrs):
        raw_data = attrs.get('raw_data')
        signature = attrs.get('signature')
        session = attrs.get('session')
        wxsession = WxSession.get(session)
        if not WxUser.check_signature(wxsession.session_key, raw_data, signature):
            raise serializers.ValidationError('用户信息签名与微信服务器返回不一致')
        return attrs

    def save(self, **kwargs):
        encrypted_data = self.validated_data['encrypted_data']
        iv = self.validated_data['iv']
        session = self.validated_data['session']
        wxsession = WxSession.get(session)
        user, created = WxUser.create_from_encrypted_data(encrypted_data, iv, wxsession.session_key)
        if created or not wxsession.user:
            wxsession.user = user
            wxsession.save()
        return user
