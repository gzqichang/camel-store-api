import os
from .base import *


SECRET_KEY = ''                # 密钥

DEBUG = False

SHOP_NAME = '骆驼小店'               # 店铺名
SHOP_SITE = 'luotuoxiaodian'        #

DEFAULT_ADMIN_PASSWORD = ''  # 默认的管理员密码

NUMBER_OF_SHOP = 10   #最大门店数量

ALLOWED_HOSTS = ['*', ]
AUTH_PASSWORD_VALIDATORS = []


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',   # MYSQL数据库
        'HOST': '127.0.0.1',   # 数据库主机
        'PORT': '5432',
        'NAME': '',
        'USER': 'postgres',        # 数据库用户
        'PASSWORD': '',  # 数据库用户密码
        'ATOMIC_REQUESTS': True,
    }
}


#七牛
QFILE_JUST_ALLOW_IMG = True
QFILE_QINIU_ACCESS_KEY = ''
QFILE_SECRET_KEY = ''
QFILE_QINIU_BUCKET_DOMAIN = ''
QFILE_QINIU_BUCKET_NAME = ''
QFILE_QINIU_SECURE_URL = True

QFILE_QINIU_MEDIA_ROOT = os.path.join(SHOP_SITE, 'media')

DEFAULT_FILE_STORAGE = 'apps.qfile.storage.qiniu.QiniuMediaStorage'



#腾讯地图api KEY
TENCENT_LBS_KEY = ''


WX_CONFIG = {
    'WXAPP_APPID': '',
    'WXAPP_APPSECRET': '',
}


#微信支付相关
WX_PAY_WXA_APP_ID = ""  # 小程序 appid
WX_PAY_API_KEY = ""  # 商户 key
WX_PAY_MCH_ID = ""  # 商户号
WX_PAY_SUB_MCH_ID = ""  # 子商户号，受理模式下必填
WX_PAY_MCH_CERT = os.path.join(BASE_DIR, "conf/cert_file/apiclient_cert.pem")  # 商户证书路径
WX_PAY_MCH_KEY = os.path.join(BASE_DIR, "conf/cert_file/apiclient_key.pem")  # 商户证书私钥路径


#邮箱配置
SEND_EMAIL = True                #是否启用邮件发送服务
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_SSL = True
EMAIL_HOST = 'smtp.exmail.qq.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER  #网站使用的邮箱
