import requests
import os
from urllib.parse import urljoin, urlparse
from collections import OrderedDict
from rest_framework import views
from rest_framework.reverse import reverse
from rest_framework.response import Response
from django.conf import settings
from apps.utils.lbs import lbs

"""
- sitemap: Sitemap
- wx_login: 微信登陆
- wx_userinfo: 微信用户信息
- wx_user_phone: 微信用户手机号
- wx_user_referrals: 微信用户帮手

- city: 城市列表
- location: 定位城市
- category: 商品分类
- goods: 商品列表
- banner: 首页轮播图
- address：用户收货地址
- order: 用户订单
- buy: 下单
- wechatpay: 调起付接口

- withdrawal: 用户查看提现记录接口
- create_withdrawal: 提交提现请求接口
- faq: 帮助中心
- hotword: 热搜词

- cartbuy: 购物车下单的接口
- orders: 新的订单的接口
- goodsitems: 订单内的商品的接口
- config: 系统配置
- level: 会员等级
- rechargetype: 优惠充值类型
- recharge: 充值
- rchgrecord: 充值记录
- express: 快递公司api
- express_list: 快递100公司列表
- shop: 店铺列表
- shop_list: 小程序获取店铺列表
- near_shop: 小程序获取合适的店铺
- user: 管理员
- goodslist: 商品列表(订阅商品和普通商品合并)
- orderlist: 定单列表(订阅和普通订单合并)
- ptgroup: 拼团列表
- build_ptgroups: 正参团订单自己开团
- order_statistic: 微信用户获取不同状态订单个数
- feedback: 用户反馈
- search: 传统首页的查询接口(当前店铺没有符合的商品时的其他店铺的查询结果的接口)
- homebanner: 传统首页的轮播图
- shortcut: 传统首页快速入口
- moduleL: 传统首页各模块
- shortvideo: 短视频
- video_personal: 短视频个人中心
- blockuser: 封禁用户
- sms_balance: 短信余额
- sms_recharge: 短信充值
- sms_switch: 短信开关
"""

sitemap_items = (
    ('sitemap', 'sitemap'),

    ('wx_login', 'wxapp:login'),
    ('wx_userinfo', 'wxuser-list'),
    ('wx_user_phone', 'wxuser-phone'),
    ('wx_user_referrals', 'wxuser-referrals'),
    ('accountlog', 'wxuseraccountlog-list'),

    ('category', 'goodscategory-list'),
    ('goods', 'goods-list'),
    ('search_goods', 'search-goods'),
    ('validate_cart', 'goods-validate-cart'),
    ('banner', 'banner-list'),

    ('address', 'useraddress-list'),
    ('wechatpay', 'wechatpay'),

    ('withdrawal', 'withdraw-list'),
    ('create_withdrawal', 'create_withdrawal'),

    ('faq', 'faqcontent-list'),
    ('hotword', 'hotword-list'),

    ('cartbuy', 'cartbuy'),
    ('order', 'orders-list'),
    ('pull_pay_result', 'pull-pay-result'),
    ('notice', 'notice-list'),
    ('config', 'config'),
    ('level', 'level-list'),
    ('rechargetype', 'rechargetype-list'),
    ('recharge', 'recharge'),
    ('rchgrecord', 'rechargerecord-list'),
    ('express', 'express-list'),
    ('experss_list', 'express-express-list'),
    ('shop', 'shop-list'), ('shop_list', 'shop-shop-list'), ('near_shop', 'shop-near-shop'),
    ('is_range', 'shop-is-range'),
    ('ptgroup', 'ptgroup-list'),
    ('build_ptgroups', 'ptgroup-build-ptgroup'),
    ('order_statistic', 'orders-statistic'),
    ('feedback', 'feedback-list'),
    ('search', 'search'),
    ('homebanner', 'homebanner-list'),
    ('shortcut', 'shortcut-list'),
    ('module', 'module-list'),
    ('replace', 'replace'),
    ('validate_replgoods', 'goods-validate-replgoods'),
    ('storeinfo', 'storeinfo'),

    ('shortvide', 'shortvideo-list'),
    ('video_personal', 'shortvideo-personal'),
    ('blockuser', 'shortvideo-blockuser'),
)

sitemap_cache = {}

class SitemapView(views.APIView):

    def get(self, request, *args, **kwargs):
        global sitemap_items, sitemap_cache
        url = request.build_absolute_uri()
        netloc = urlparse(url).netloc

        # try cache.
        try:
            sitemap = sitemap_cache[(request.scheme, netloc)]
        except LookupError:
            sitemap = self.gen_sitemap(request)
            # update cache
            sitemap_cache[(request.scheme, netloc)] = sitemap
            
        return Response(sitemap)

    def gen_sitemap(self, request):
        sitemap = OrderedDict()
        for key, view in sitemap_items:
            sitemap[key] = reverse(view, request=request)
        return sitemap

class TencentLbs(views.APIView):
    '''
    腾讯地图跳转
    '''

    def get(self, request, *args, **kwargs):
        url = 'https://apis.map.qq.com/'
        path = request.path
        url = urljoin(url, path.replace('/api/', ''))
        data = request.query_params.dict()
        data['key'] = lbs.key
        data['sig'] = lbs.gen_sig(data)
        res = requests.get(url, params=data)
        return Response(res.json(), status=res.status_code)


class WebHookView(views.APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        sh_path = os.path.dirname(os.path.dirname(settings.BASE_DIR))
        sh = os.path.join(sh_path, 'develop.sh').replace('\\', '/')
        print(sh)
        if os.path.exists(sh):
            os.system('/bin/bash {}'.format(sh))
        return Response(request.POST)
