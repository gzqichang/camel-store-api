# usr/bin/env python
# -*- coding: utf-8 -*-
import functools
import json
import urllib
import urllib.parse
import requests


def res2json(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        succ, data = f(*args, **kwargs)
        if succ:
            data = json.loads(data.decode('utf-8'))
        return succ, data
    return wrapper


class BaseRequestClient(object):

    def __init__(self, host, port=None):
        self.host = host
        self.port = port or 80

    def build_request_url(self, path, **kwargs):
        if '://' in path:
            return path

        host = kwargs.pop('host', self.host)
        port = kwargs.pop('port', self.port)
        ssl = (
            kwargs.pop('ssl', False) or
            'cert' in kwargs or
            port == 443
        )
        scheme = 'https' if ssl else 'http'

        uri = '{}://{}'.format(scheme, host)
        if ':' not in host and port not in [80, 443]:
            uri += ':{}'.format(port)
        return urllib.parse.urljoin(uri, path)

    def send_request(self, method, path, **kwargs):
        url = self.build_request_url(path, **kwargs)
        resp = requests.request(method, url, **kwargs)
        if resp.status_code != 200:
            return False, resp.status_code
        return True, resp.content

    def __call__(self, method, path, **kwargs):
        return self.send_request(method, path, **kwargs)