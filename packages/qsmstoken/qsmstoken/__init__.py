# usr/bin/env python
# -*- coding: utf-8 -*-


def send_code(phone):
    from .models import SMSToken
    instance = SMSToken.create(phone)
    instance.send_code()


def check_code(phone, code):
    from .models import SMSToken
    return SMSToken.check_code(phone, code)
