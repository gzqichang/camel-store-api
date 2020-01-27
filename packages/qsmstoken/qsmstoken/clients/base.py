"""
    基本短信接口

"""


class BaseSMSClient(object):

    def __init__(self, sms_config={}):
        self.access_key = sms_config.get('ACCESS_KEY')
        self.secret_key = sms_config.get('SECRET_KEY')
        self.sign_name = sms_config.get('SIGN_NAME')

    def send_sms(self, phone, params, template_code, *args, **kwargs):
        raise NotImplementedError('Must be Implement')

    def test_send_sms(self, phone):
        raise NotImplementedError('Must be Implement')