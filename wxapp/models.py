# usr/bin/env python
# -*- coding: utf-8 -*-
import binascii
import os
import hashlib
import uuid
from urllib.parse import urljoin
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from django.utils.safestring import mark_safe
from qcache.models import VersionedMixin

from apps.config.models import Marketing
from .https import wx_config, wxapp_client, wx_web_client, wx_app_client
from .WXBizDataCrypt import WXBizDataCrypt


class WxUser(VersionedMixin, models.Model):
    """ 微信的关注用户 """
    GENDER = ((0, '未知'), (1, '男'), (2, '女'))

    TRUE = 'true'
    FALSE = 'false'
    NULL = 'null'
    RIGHT = ((TRUE, '是'), (FALSE, '否'), (NULL, '未达标'))

    union_id = models.CharField('unionID', max_length=128, blank=True, default='')
    web_openid = models.CharField('Web openID', max_length=128, blank=True, default='')
    app_openid = models.CharField('App openID', max_length=128, blank=True, default='')
    wx_app_openid = models.CharField('WxApp openID', max_length=128, blank=True, default='')
    nickname = models.CharField('用户昵称', max_length=128, blank=True, default='')
    avatar_url = models.CharField('头像URL', max_length=512, blank=True, default='')
    language = models.CharField('语言', max_length=32, blank=True, default='')
    gender = models.IntegerField('用户性别', choices=GENDER, default=0)
    province = models.CharField('省份', max_length=64, blank=True, default='')
    city = models.CharField('城市', max_length=64, blank=True, default='')
    country = models.CharField('国家', max_length=64, blank=True, default='')
    date_joined = models.DateTimeField('加入时间', auto_now_add=True)
    qrcode_url = models.CharField('小程序码', max_length=256, blank=True, default='')
    testers = models.BooleanField('是否是测试人员', default=False)
    upload_perm = models.BooleanField('是否可以上传短视频', default=False)
    rebate_right = models.CharField('推广返利权利', choices=RIGHT, max_length=32, default=NULL)
    bonus_right = models.CharField('分销反佣权利', choices=RIGHT, max_length=32, default=NULL)

    is_staff = False
    is_active = True
    is_superuser = False

    class Meta:
        verbose_name = verbose_name_plural = '微信用户'

    def __str__(self):
        return self.nickname

    def avatar(self):
        html = '<img src="{}" width="50" height="50"/>'.format(self.avatar_url)
        return html
    avatar.short_description = '头像'
    avatar.allow_tags = True

    @property
    def has_rebate_right(self):
        if self.rebate_right == self.TRUE:
            return True
        elif self.rebate_right == self.FALSE:
            return False
        elif self.rebate_right == self.NULL and Marketing.value_eq_zero('rebate'):
            return True
        return False

    @property
    def has_bonus_right(self):
        if self.bonus_right == self.TRUE:
            return True
        elif self.bonus_right == self.FALSE:
            return False
        elif self.bonus_right == self.NULL and Marketing.value_eq_zero('bonus'):
            return True
        return False

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_wechat(self):
        return True

    def get_username(self):
        return self.union_id

    @classmethod
    def check_signature(cls, session_key, raw_data, signature):
        """ 校验小程序端数据完整性 """
        now_signature = hashlib.sha1((raw_data + session_key).encode()).hexdigest()
        return now_signature == signature

    def save_from_encrypted_data(self, encrypted_data, iv):
        """ 从小程序端获取用户信息 """

        pc = WXBizDataCrypt(wx_config.get('WXAPP_APPID'), self.session.session_key)
        userinfo = pc.decrypt(encrypted_data, iv)
        if self.wx_app_openid != userinfo.get('openId'):
            return None
        user_data = {
            'union_id': userinfo.get('unionId', ''),
            'wx_app_openid': userinfo.get('openId', ''),
            'nickname': userinfo.get('nickName', ''),
            'avatar_url': userinfo.get('avatarUrl', ''),
            'language': userinfo.get('language', ''),
            'gender': userinfo.get('gender', 0),
            'province': userinfo.get('province', ''),
            'city': userinfo.get('city', ''),
            'country': userinfo.get('country', '')
        }
        self.update_info(user_data)
        return self

    def update_info(self, data):
        is_change = False
        for key, value in data.items():
            now_value = getattr(self, key, '')
            if value and value != now_value:
                is_change = True
                setattr(self, key, value)
        if is_change:
            self.save()

    @classmethod
    def create_from_encrypted_data(cls, encrypted_data, iv, session_key):
        """ 从小程序端获取用户信息 """
        pc = WXBizDataCrypt(wx_config.get('WXAPP_APPID'), session_key)
        userinfo = pc.decrypt(encrypted_data, iv)
        union_id = userinfo.get('unionId')
        wx_app_openid = userinfo.get('openId'),
        user_data = {
            'union_id': userinfo.get('unionId', ''),
            'wx_app_openid': userinfo.get('openId', ''),
            'nickname': userinfo.get('nickName', ''),
            'avatar_url': userinfo.get('avatarUrl', ''),
            'language': userinfo.get('language', ''),
            'gender': userinfo.get('gender', 0),
            'province': userinfo.get('province', ''),
            'city': userinfo.get('city', ''),
            'country': userinfo.get('country', '')
        }
        user = cls.objects.filter(Q(union_id=union_id) | Q(wx_app_openid=wx_app_openid)).distinct().first()
        created = False
        if user:
            is_change = False
            for key, value in user_data.items():
                now_value = getattr(user, key, '')
                if value and value != now_value:
                    is_change = True
                    setattr(user, key, value)
            if is_change:
                user.save()
        else:
            user = cls.objects.create(**user_data)
            created = True
        return user, created

    @property
    def wxa_qrcode(self):
        """ 个人小程序码 """
        path = os.path.join(settings.MEDIA_ROOT, self.qrcode_url)
        if os.path.isfile(path):
            return urljoin(settings.MEDIA_URL, self.qrcode_url)
        print(
            wx_config.get('WXAPP_USER_QRCODE_PAGE')
        )
        self.qrcode_url = wxapp_client.get_wxa_code(self.wx_app_openid,
                                                    page=wx_config.get('WXAPP_USER_QRCODE_PAGE'))
        self.save()
        return urljoin(settings.MEDIA_URL, self.qrcode_url)


class WxSession(VersionedMixin, models.Model):
    """ 小程序用户的session维护 """
    user = models.OneToOneField(WxUser, verbose_name='微信用户', related_name='session',
                                null=True, blank=True, on_delete=models.CASCADE)
    session = models.CharField('Session', unique=True, max_length=128)
    session_key = models.CharField('Session Key', max_length=128, blank=True, default='')
    wxapp_openid = models.CharField('WxApp OpenId', max_length=128, blank=True, default='')
    expires_in = models.IntegerField('有效时间(秒)', default=7200)

    class Meta:
        verbose_name = verbose_name_plural = 'Session'

    def __str__(self):
        return self.session

    @classmethod
    def create_session(cls, user=None, session_key='', openid='', expires_in=7200):
        instance = cls.objects.create(user=user,
                                      session_key=session_key,
                                      expires_in=expires_in,
                                      wxapp_openid=openid,
                                      session=cls.generate_key())
        return instance

    @classmethod
    def generate_key(cls):
        return binascii.hexlify(os.urandom(20)).decode()

    @classmethod
    def get_or_update_session(cls, user=None, session_key='', openid='', expires_in=7200):
        if user is not None:
            instance = getattr(user, 'session', None)
        elif openid:
            instance = cls.get_by_openid(openid)
        else:
            instance = None

        if instance is not None:
            instance.update_session(session_key, user, openid)
        else:
            instance = cls.create_session(user, session_key, openid, expires_in)
        return instance

    @classmethod
    def get(cls, session):
        try:
            return cls.objects.get(session=session)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_by_openid(cls, wxapp_openid):
        return cls.objects.filter(Q(user__wx_app_openid=wxapp_openid) |
                                  Q(wxapp_openid=wxapp_openid)
                                  ).distinct().first()

    def update_session(self, session_key=None, user=None, openid=None):
        if session_key and not self.is_valid(session_key):
            self.session_key = session_key
            self.session = self.generate_key()
        if self.user is None and user is not None:
            self.user = user
        if not self.wxapp_openid and openid:
            self.wxapp_openid = openid
        self.save()

    def is_valid(self, session_key):
        return self.session_key == session_key


def generate_scene():
    return uuid.uuid4().hex


class WxAppCode(VersionedMixin, models.Model):
    name = models.CharField('渠道', max_length=64)
    scene = models.CharField('场景值', max_length=32, unique=True, default=generate_scene)
    url = models.CharField('url地址', max_length=128, blank=True, default='')
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '渠道'
        verbose_name_plural = '渠道管理'

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.url:
            self.url = wxapp_client.get_wxa_code(self.scene)
        return super().save(force_insert, force_update, using, update_fields)

    @property
    def media_url(self):
        return urljoin(settings.MEDIA_URL, self.url)

    def url_display(self):
        html = '<a href="{}" download >下载</a>'.format(self.media_url)
        return mark_safe(html)
    url_display.short_description = "下载"

    @classmethod
    def get(cls, scene):
        try:
            return cls.objects.get(scene=scene)
        except cls.DoesNotExist:
            return None


def default_access_token_deadline(seconds=7200):
    return timezone.now() + timezone.timedelta(seconds=seconds)


def default_refresh_token_deadline(seconds=2505600):
    return timezone.now() + timezone.timedelta(seconds=seconds)


class AccessToken(VersionedMixin, models.Model):
    unionid = models.CharField('unionID', max_length=128, blank=True, default='')
    web_openid = models.CharField('web_openid', max_length=128, blank=True, default='')
    app_openid = models.CharField('app_openid', max_length=128, blank=True, default='')
    web_access_token = models.CharField('web_access_token', max_length=256, blank=True, default='')
    web_refresh_token = models.CharField('web_refresh_token', max_length=256, blank=True, default='')
    web_access_token_deadline = models.DateTimeField('web access_token失效时间', default=default_access_token_deadline)
    web_refresh_token_deadline = models.DateTimeField('web refresh_token失效时间', default=default_refresh_token_deadline)
    app_access_token = models.CharField('app_access_token', max_length=256, blank=True, default='')
    app_refresh_token = models.CharField('app_refresh_token', max_length=256, blank=True, default='')
    app_access_token_deadline = models.DateTimeField('app access_token失效时间', default=default_access_token_deadline)
    app_refresh_token_deadline = models.DateTimeField('app refresh_token失效时间', default=default_refresh_token_deadline)

    class Meta:
        db_table = 'wx_access_token'

    @classmethod
    def update_access_token(cls, code, auth_type='web'):
        """ 兼容Web和APP的登录access_token """
        openid = '{}_openid'.format(auth_type)
        access_token = '{}_access_token'.format(auth_type)
        refresh_token = '{}_refresh_token'.format(auth_type)
        access_token_deadline = '{}_access_token_deadline'.format(auth_type)
        refresh_token_deadline = '{}_refresh_token_deadline'.format(auth_type)
        if auth_type == 'web':
            client = wx_web_client
        elif auth_type == 'app':
            client = wx_app_client
        else:
            return None

        succ, resp = client.get_access_token(code)
        if succ and not resp.get('errcode'):
            unionid = resp.get('unionid')
            defaults = {
                openid: resp.get('openid'),
                access_token: resp.get('access_token'),
                refresh_token: resp.get('refresh_token'),
                access_token_deadline: default_access_token_deadline(resp.get('expires_in')),
                refresh_token_deadline: default_refresh_token_deadline()
            }
            instance, created = cls.objects.update_or_create(unionid=unionid, defaults=defaults)
            return instance
        return None

    @property
    def user(self):
        user = WxUser.objects.filter(
            Q(union_id=self.unionid) |
            Q(web_openid=self.web_openid) |
            Q(app_openid=self.app_openid)
        ).order_by('date_joined').first()
        if user is None:
            if self.web_openid and self.web_access_token:
                auth_type = 'web'
                succ, res = wx_web_client.get_user_info(self.web_access_token, self.web_openid)
            elif self.app_openid and self.app_access_token:
                auth_type = 'app'
                succ, res = wx_app_client.get_user_info(self.app_access_token, self.app_openid)
            else:
                return None
            if succ and not res.get('errcode'):
                user_data = {
                    'union_id': res.get('unionid'),
                    '{}_openid'.format(auth_type): res.get('openid'),
                    'nickname': res.get('nickname'),
                    'avatar_url': res.get('headimgurl'),
                    'gender': res.get('sex'),
                    'province': res.get('province'),
                    'city': res.get('city'),
                    'country': res.get('country'),
                    'language': res.get('language')
                }
                user = WxUser.objects.create(**user_data)
                if hasattr(user, 'wxuserinfo'):
                    user.wxuserinfo.scene = '1000'
                    user.wxuserinfo.save()
        if not user.web_openid:
            user.web_openid = self.web_openid
        if not user.app_openid:
            user.app_openid = self.app_openid
        user.save()
        return user
