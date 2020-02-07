import os, configparser

from .base import *


SECRET_KEY = ''

DEBUG = False

CAMEL_STORE_VERSION = '3.8.1'
SHOP_NAME = '骆驼小店'         # 店铺名

ALLOWED_HOSTS = ['*', ]
AUTH_PASSWORD_VALIDATORS = []

INSTALLED_APPS += [
    'rest_framework.authtoken',
    'django_filters',
    'captcha',

    'qapi',
    'quser',
    'qcache',
    'qsmstoken',

    'apps.qfile',
    'wxapp',
    'apps.account',
    'apps.config',
    'apps.goods',
    'apps.group_buy',
    'apps.refund',
    'apps.trade',
    'apps.count',
    'apps.shop',
    'apps.user',
    'wx_pay',
    'apps.feedback',
    'apps.homepage',
    'apps.sms',
    'apps.tools',
    'apps.cloud',
    'apps.wx_logistics',
    'apps.short_video',
    'apps.utils',
]


DEFAULT_DB =  {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'camelstore',
    'USER': 'camelstore',
    'PASSWORD': '',
    'HOST': '127.0.0.1',
    'PORT': '5432',
    "ATOMIC_REQUESTS": True
}

DATABASES = {
    'default': DEFAULT_DB
}


# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        # 'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'LOCATION': '/var/tmp/django_cache',
        'TIMEOUT': 1 * 60 * 60,
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        },
    },
    'qcache': {
        'BACKEND': 'qcache.no_pickle_cache_backend.NoPickleLocMemCache',
        'LOCATION': 'qcache-only',
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        },
    },
}


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/api/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "staticfiles/"),
]
MEDIA_URL = '/api/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
#朋友圈分享海报
POSTER_ROOT = os.path.join(MEDIA_ROOT, 'poster')

if not os.path.exists(MEDIA_ROOT):
    os.mkdir(MEDIA_ROOT)

if not os.path.exists(POSTER_ROOT):
    os.mkdir(POSTER_ROOT)


CONFIG_FILE_PATH = os.path.join(BASE_DIR, "config.ini")
SETTINGS_CONFIG = configparser.ConfigParser()
SETTINGS_CONFIG.read(CONFIG_FILE_PATH)
SETTINGS_CONFIG_DEFAULT = SETTINGS_CONFIG["DEFAULT"]

if "WX_LITE_SECRET" in SETTINGS_CONFIG_DEFAULT:
    WX_LITE_SECRET = SETTINGS_CONFIG_DEFAULT["wx_lite_secret"]
else:
    WX_LITE_SECRET = os.environ.get('WX_LITE_SECRET')


AUTH_USER_MODEL = 'user.User'

SHOP_NAME = '骆驼小店'
SHOP_SITE = 'luotuoxiaodian'
NUMBER_OF_SHOP = 1    # 店铺数量

#七牛
QFILE_JUST_ALLOW_IMG = False
QFILE_QINIU_ACCESS_KEY = ''
QFILE_SECRET_KEY = ''
QFILE_QINIU_BUCKET_DOMAIN = ''
QFILE_QINIU_BUCKET_NAME = ''
QFILE_QINIU_SECURE_URL = False

# DEFAULT_FILE_STORAGE = 'apps.qfile.storage.qiniu.QiniuMediaStorage'
# STATICFILES_STORAGE = 'apps.qfile.storage.qiniu.QiniuStaticStorage'


#腾讯地图api KEY
TENCENT_LBS_KEY = ''
TENCENT_LBS_SK = ''


WX_CONFIG = {
    'WXAPP_APPID': '',
    'WXAPP_APPSECRET': '',
}


#微信支付相关
WX_PAY_APP_ID = ""  # 微信公众号 appid
WX_PAY_WXA_APP_ID = ""  # 小程序 appid
WX_PAY_API_KEY = ""  # 商户 key
WX_PAY_MCH_ID = ""  # 商户号
WX_PAY_SUB_MCH_ID = ""  # 子商户号，受理模式下必填
WX_PAY_MCH_CERT = os.path.join(BASE_DIR, "conf/cert_file/qichang/apiclient_cert.pem")  # 商户证书路径
WX_PAY_MCH_KEY = os.path.join(BASE_DIR, "conf/cert_file/qichang/apiclient_key.pem")  # 商户证书私钥路径
WX_PAY_NOTIFY_URL = "http://**.com/api/trade/"  # 支付结果通知回调
