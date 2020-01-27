# usr/bin/env python
# -*- coding: utf-8 -*-
"""
    来自微信小程序文档官网的示例代码
"""

import base64
import json
from Crypto.Cipher import AES


class WXBizDataCrypt:
    def __init__(self, app_id, session_key):
        self.appId = app_id
        self.session_key = session_key

    def decrypt(self, encrypted_data, iv):
        # base64 decode
        session_key = base64.b64decode(self.session_key)
        encrypted_data = base64.b64decode(encrypted_data)
        iv = base64.b64decode(iv)

        cipher = AES.new(session_key, AES.MODE_CBC, iv)
        decrypted = json.loads(self._unpad(cipher.decrypt(encrypted_data)).decode('utf-8'))

        if decrypted['watermark']['appid'] != self.appId:
            raise Exception('Invalid Buffer')

        return decrypted

    def _unpad(self, s):
        return s[:-ord(s[len(s)-1:])]
