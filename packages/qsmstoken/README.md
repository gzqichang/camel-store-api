# qsmstoken

## 安装

先用 `git clone` 下载源代码，然后执行 `python setup.py develop` 安装。

## 配置

在 django project 的 `settings.py` 文件的 `INSTALLED_APPS` 中加入 `qsmstoken` 即可。

## 说明

短信验证码发送, 包装了阿里云通信和阿里大于两种 SDK, 配置 settings

```
# settings.py
SMS_CONFIG = {
    # 选择调用的客户端
    # 阿里云通信: qsmstoken.clients.aliyunsms.AliyunSMSClient
    # 阿里大于: qsmstoken.clients.alidayusms.AlidayuSMSClient
    'BACKEND': 'qsmstoken.clients.aliyunsms.AliyunSMSClient',  
    'ACCESS_KEY': 'ACCESS_KEY',
    'SECRET_KEY': 'SECRET_KEY',
    'SIGN_NAME': 'SIGN_NAME',  # 短信签名
    'CODE_TEMPLATE': '',  # 验证码的短信模板编号
    'CODE_EXPIRES': 300,  # 验证码失效时间, 单位: 秒
    'TOKEN_BIT': 6,  # 验证码的位数
}
```

在 `view.py` 中发送验证码

```
from qsmstoken import send_code, check_code

send_code(phone)
check_code(phone, code)

```

也可以单独使用

```
from django.conf import settings
from qsmstoken.clients.aliyunsms import AliyunSMSClient

client = AliyunSMSClient(settings.SMS_CONFIG)
client.send_sms(phone, params, template_code, *args, **kwargs)
```

### 自定义 Backend
```
from qsmstoken.clients import BaseSMSClient

class CustomBackend(BaseSMSClient):

    def send_sms(self, phone, params, template_code, *args, **kwargs):
        ...

    def test_send_sms(self, phone):
        ...

```