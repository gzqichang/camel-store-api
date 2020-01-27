import requests
from requests.exceptions import SSLError, ConnectTimeout, ConnectionError
from .company import company


class Logistics():
    kuaidi_url = 'http://www.kuaidi100.com/query'

    def get_code(self, express):
        code = None
        for i in company:
            if i.get('name') == express:
                code = i.get('code')
                break
        return code

    def get_Logistics_info(self, express, postid):
        code = self.get_code(express)
        if not code:
            return 404, '未检索到相关快递公司'
        data = {'type': code, 'postid': postid}
        try:
            res = requests.get(self.kuaidi_url, params=data)
            info = res.json()
            info.update({'express': express})
            return 200, info
        except (SSLError, ConnectTimeout, ConnectionError):
            return 400, '请求错误'


logistics = Logistics()