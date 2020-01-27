import time
import hashlib
import cProfile
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = 'Call API n times.'

    def add_arguments(self, parser):
        parser.add_argument('-t', '--times', type=int)
        parser.add_argument('-o', '--output', default=None)
    
    def handle(self, *args, **options):
        print('api profile.')
        n = options.get('times')
        if not n:
            n = 1
        out = options.get('output')
        if not out:
            out = f'{datetime.now().isoformat()}.pstats'

        from rest_framework.test import APIClient
        client = APIClient()
#        url = '/api/homepage/homebanner/?shop=17'
#        url = '/api/homepage/module/?shop=17'
#        url = '/api/homepage/shortcut/?shop=17'
#        url = '/api/goods/goods/?page_size=20&category=&shop=17&search=&groupbuy=&model_type=&recommendation='
#        url = '/api/goods/category/?page=1&page_size=1000&shop=17'
#        url = '/api/shop/shop/near_shop/?shop=17&address=&location='
#        url = '/api/video/video/?page=1&page_size=20'
#        url = '/api/config/level/?page=1&page_size=1000'
#        url = '/api/config/notice/?page=1&page_size=1000&is_active=true'
#        url = '/api/config/config?page=1&page_size=1000'
        url = '/api/sitemap/'
#        url = '/api/config/config'
        # 预先调用一次，热身。
        resp = client.get(url)

        start = time.time()
        resp = None
        pr = cProfile.Profile()
        pr.enable()
        for i in range(n):
            resp = client.get(url)
        pr.disable()
        pr.dump_stats(out)
        md5 = hashlib.md5(resp.content).hexdigest()
        print(f'time: {(time.time() - start):.3f}', resp.status_code, md5, resp.content[:50])
#        print(url)
#        print(resp.content.decode())
#        import json, pickle
#        start = time.time()
#        t = json.loads(resp.content)
#        print(f'json loads time: {(time.time() - start):.3f}')
#        print(t.get('next', None))
#        start = time.time()
#        pickle.dumps(t)
#        print(f'pickle dumps time: {(time.time() - start):.3f}')
