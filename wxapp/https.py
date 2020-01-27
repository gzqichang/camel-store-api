# usr/bin/env python
# -*- coding: utf-8 -*-
import os
import json
from requests.compat import json as complexjson
from PIL import Image
from io import BytesIO
from django.conf import settings
from django.core.cache import cache
from . import BaseRequestClient, res2json


class WXAppRequestClient(BaseRequestClient):
    path_access_token = 'cgi-bin/token'  # 获取 access_token
    path_jscode2session = 'sns/jscode2session'  # 换取 session_key
    path_wxacode = 'wxa/getwxacodeunlimit'  # 获取小程序码，带场景值
    send_message = 'cgi-bin/message/wxopen/template/send'

    def __init__(self, appid, secret, host=None, port=None, ):
        self.appid = appid
        self.secret = secret
        self.host = host or 'api.weixin.qq.com'
        self.port = port or 443
        super().__init__(self.host, self.port)

    @res2json
    def get_session_key(self, code):
        url_path = self.build_request_url(self.path_jscode2session)
        params = {
            'appid': self.appid,
            'secret': self.secret,
            'js_code': code,
            'grant_type': 'authorization_code',
        }
        return self.send_request('GET', url_path, params=params)

    def get_access_token(self):
        access_token = cache.get('wx_access_token', None)
        if not access_token:
            url_path = self.build_request_url(self.path_access_token)
            params = {
                'appid': self.appid,
                'secret': self.secret,
                'grant_type': 'client_credential',
            }
            succ, resp_data = self.send_request('GET', url_path, params=params)
            resp_data = json.loads(resp_data.decode('utf-8'))
            access_token = resp_data.get('access_token', '')
            expires_in = resp_data.get('expires_in', 7200)
            cache.set('wx_access_token', access_token, expires_in)
        return access_token

    def get_wxa_code(self, scene, width=430, auto_color=False, line_color=None, page=None):
        url_path = self.build_request_url(self.path_wxacode)
        params = {
            'access_token': self.get_access_token(),
        }
        data = {
            'scene': scene,
            'width': width,
            'auto_color': auto_color,
            'line_color': line_color or {"r": "0", "g": "0", "b": "0"}
        }
        if page is not None:
            data.update({'page': page})
        url_path += '?access_token=' + self.get_access_token()
        succ, resp_data = self.send_request('POST', url_path, data=json.dumps(data), params=params)
        filename = 'wxacodes/{}.png'.format(scene)
        destination = os.path.join(settings.MEDIA_ROOT, filename)
        if not os.path.exists(os.path.dirname(destination)):
            os.mkdir(os.path.dirname(destination))
        if succ:
            try:
                image = Image.open(BytesIO(resp_data))
                if image.mode not in ('L', 'RGB'):
                    if image.mode == 'RGBA':
                        # 透明图片需要加白色底
                        image.load()
                        alpha = image.split()[3]
                        bg = alpha.point(lambda x: 255 - x)
                        image = image.convert('RGB')
                        image.paste((255, 255, 255), None, bg)
                    else:
                        image = image.convert('RGB')
                image.save(destination)
            except OSError as e:
                print(e)
        return filename

    def send_template_message(self, openid, template_id, form_id, content_data=None, page=None, emphasis_keyword=None):

        def format_content_data(content_data):
            if content_data:
                data_ = dict()
                for k, v in content_data.items():
                    data_.update({k: {'value': v}})
                return data_
            return None

        url_path = self.build_request_url(self.send_message)
        params = {
            'access_token': self.get_access_token(),
        }
        data = {
            'touser': openid,
            'template_id': template_id,
            'form_id': form_id,
            'content_data': format_content_data(content_data),
            'page': page,
            'emphasis_keyword': emphasis_keyword,
        }
        succ, resp_data = self.send_request('POST', url_path, data=json.dumps(data), params=params)
        return succ, resp_data

    # 订单导入好物圈(待完善）
    def importorder(self, is_history, data, is_test=False):
        importorder_url = 'mall/importorder'
        url_path = self.build_request_url(importorder_url)
        params = {
            'action': 'add-order',
            'access_token': self.get_access_token(),
            'is_history': 1 if is_history else 0
        }
        if is_test:
            params.update({'is_test': 1})
        data = complexjson.dumps(data, ensure_ascii=False).encode("utf-8")  # 解决中文乱码
        succ, resp_data = self.send_request('POST', url_path, data=data, params=params)
        return succ, resp_data

    # 删除导入好物圈的订单(待完善）
    def deleteorde(self, user_open_id, order_id):
        deleteorde_url = 'mall/deleteorder'
        url_path = self.build_request_url(deleteorde_url)
        params = {
            'access_token': self.get_access_token(),
        }
        data = {
            'user_open_id': user_open_id,
            'order_id': order_id
        }
        succ, resp_data = self.send_request('POST', url_path, data=json.dumps(data), params=params)
        return succ, resp_data


class WxRequestClient(BaseRequestClient):
    """ 微信网站登录的请求端 """
    path_access_token = 'sns/oauth2/access_token'  # 获取 access_token
    path_refresh_token = 'sns/oauth2/refresh_token'  # 获取 refresh_token
    path_get_userinfo = '/sns/userinfo'  # 获取用户信息

    def __init__(self, appid, secret, host=None, port=None, auth_type='web'):
        self.host = host or 'api.weixin.qq.com'
        self.port = port or 443
        self.appid = appid
        self.secret = secret
        self.refresh_token_name = 'wx_web_refresh_token'
        self.access_token_name = 'wx_web_access_token'
        if auth_type == 'app':
            self.refresh_token_name = 'wx_app_refresh_token'
            self.access_token_name = 'wx_app_access_token'
        super().__init__(self.host, self.port)

    @res2json
    def get_access_token(self, code, grant_type='authorization_code'):
        url_path = self.build_request_url(self.path_access_token)
        params = {
            'appid': self.appid,
            'secret': self.secret,
            'code': code,
            'grant_type': grant_type,
        }
        return self.send_request('GET', url_path, params=params)

    def refresh_access_token(self, code):
        refresh_token = cache.get(self.refresh_token_name, None)
        if not refresh_token:
            cache.set(self.access_token_name, None)
            return self.get_access_token(code)
        else:
            url_path = self.build_request_url(self.path_refresh_token)
            params = {
                'appid': self.appid,
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }

            succ, resp_data = self.send_request('GET', url_path, params=params)
            resp_data = json.loads(resp_data.decode('utf-8'))
            access_token = resp_data.get('access_token', '')
            refresh_token = resp_data.get('refresh_token', '')
            expires_in = resp_data.get('expires_in', 7200)
            cache.set(self.access_token_name, access_token, expires_in)
            cache.set(self.refresh_token_name, refresh_token, 2582000)
            return access_token

    @res2json
    def get_user_info(self, access_token, openid):
        url_path = self.build_request_url(self.path_get_userinfo)
        params = {
            'access_token': access_token,
            'openid': openid,
        }
        return self.send_request('GET', url_path, params=params)


wx_config = getattr(settings, 'WX_CONFIG', {})
wxapp_client = WXAppRequestClient(wx_config.get('WXAPP_APPID'), wx_config.get('WXAPP_APPSECRET'))  # 小程序 API 调取客户端
# 网站应用调取客户端
wx_web_client = WxRequestClient(wx_config.get('WEB_APPID'), wx_config.get('WEB_APPSECRET'))
# APP 应用调取客户端
wx_app_client = WxRequestClient(wx_config.get('APP_APPID'),
                                wx_config.get('APP_APPSECRET'),
                                auth_type='app')

