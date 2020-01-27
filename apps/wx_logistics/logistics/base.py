import json
import requests
from requests.compat import json as f_json


class APIBase:
    def __init__(self, base_url='', url_set=None):
        self.url_set = url_set or dict()
        self.base_url = base_url

    def _request(self, method, url, **kwargs):
        response = None
        base_url = kwargs.pop('base_url', self.base_url)
        fine_json = kwargs.pop('fine_json', False)

        if not url.startswith(('http://', 'https://')):
            _url = self.url_set.get(url, url)
            if not _url.startswith(('http://', 'https://')):
                _url = f'{base_url}/{_url}'
        else:
            _url = url

        try:
            res = requests.request(method, url=_url, **kwargs)
        except (Exception,) as e:
            print(e)
        else:
            if str(res.status_code).startswith('2'):
                try:
                    if fine_json:
                        response = f_json.loads(res.content)
                    else:
                        response = res.json()
                except json.JSONDecodeError:
                    print('JSON Decode Error')

        return response

    def _get(self, url, **kwargs):
        return self._request('get', url, **kwargs)

    def _post(self, url, **kwargs):
        data = kwargs.pop('data', None)
        if data is not None:
            data = f_json.dumps(data, ensure_ascii=False).encode('utf-8')
            kwargs.update({'data': data})
        return self._request('post', url, **kwargs)
