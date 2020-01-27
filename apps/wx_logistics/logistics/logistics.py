from .base import APIBase
from .decorators import with_access_token

from .config import (
    AccountAction,
    PrinterAction,
    OrderSource,
)


class WXLogistics(APIBase):
    @with_access_token
    def _get(self, url, **kwargs):
        """
        Override for better Chinese support
        """
        return super()._get(url, **kwargs, fine_json=True)

    @with_access_token
    def _post(self, url, **kwargs):
        """
        Override for better Chinese support
        """
        return super()._post(url, **kwargs, fine_json=True)

    def check_fields(self, obj, func, fields, tips):
        """
        For Key-Value based Object check None
        :param obj: Dict
        :param func: Function
        :param fields: List
        :param tips: Str
        :return: None
        """
        if not func([obj.get(key, None) is not None for key in fields]):
            raise ValueError(tips)

    def bind_account(self,
                     action=AccountAction.Bind,
                     biz_id='',
                     delivery_id='',
                     password='',
                     remark_content='',
                     ):
        """
        绑定账号
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.bindAccount.html

        :param action: AccountAction
        :param biz_id: 快递公司客户编码
        :param delivery_id: 快递公司ID
        :param password: 快递公司客户密码
        :param remark_content: 备注内容（提交EMS审核需要）
        :return: Dict
        """

        data = {
            'type': action,
            'biz_id': biz_id,
            'delivery_id': delivery_id,
            'password': password,
        }

        if not all([action, biz_id, delivery_id, password]):
            raise ValueError('action, biz_id, delivery_id, password 都为必填项')

        if not AccountAction.has_value(action):
            raise ValueError('错误的 action')

        if remark_content:
            data.update({'remark_content': remark_content})

        if not remark_content and delivery_id == 'EMS':
            raise ValueError('当提交中国邮政速递物流(EMS)时审核需要备注内容(remark_content)')

        res = self._post('bind_account', data=data)

        if res and not res.get('errcode', None) == 0:
            raise Exception(res)

        return res

    def get_all_account(self):
        """
        拉取已绑定账号
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.getallAccount.html
        """

        res = self._post('get_all_account')

        if res and res.get('errmsg', None) is not None:
            raise Exception(res.get('errmsg'))

        return res

    def get_all_delivery(self):
        """
        获取支持的快递公司列表
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.getAllDelivery.html
        """

        additional_info = {
            'BEST': {
                'services': [{'id': 1, 'name': '标准快递'}],
                'biz_id': None,
                'mode': '加盟',
            },
            'DB': {
                'services': [{'id': 1, 'name': '大件快递3.60'}, {'id': 2, 'name': '特准快件'}],
                'biz_id': 'DB_CASH',
                'mode': '直营',
            },
            'EMS': {
                'services': [{'id': 6, 'name': '标准快递'}, {'id': 9, 'name': '快递包裹'}],
                'biz_id': None,
                'mode': '直营',
            },
            'OTP': {
                'services': [{'id': 1, 'name': '标准快递'}],
                'biz_id': 'OTP_CASH',
                'mode': '直营',
            },
            'PJ': {
                'services': [{'id': 1, 'name': '标准快递'}],
                'biz_id': 'PJ_CASH',
                'mode': '直营',
            },
            'SF': {
                'services': [
                    {'id': 0, 'name': '标准快递'},
                    {'id': 1, 'name': '顺丰即日'},
                    {'id': 2, 'name': '顺丰次晨'},
                    {'id': 3, 'name': '顺丰标快'},
                    {'id': 4, 'name': '顺丰特惠'},
                ],
                'biz_id': 'SF_CASH',
                'mode': '直营',
            },
            'STO': {
                'services': [{'id': 1, 'name': '标准快递'}],
                'biz_id': None,
                'mode': '加盟',
            },
            'YTO': {
                'services': [{'id': 0, 'name': '普通快递'}, {'id': 1, 'name': '圆准达'}],
                'biz_id': None,
                'mode': '加盟',
            },
            'YUNDA': {
                'services': [{'id': 0, 'name': '标准快件'}],
                'biz_id': None,
                'mode': '加盟',
            },
            'ZTO': {
                'services': [{'id': 0, 'name': '标准快件'}],
                'biz_id': None,
                'mode': '加盟',
            },
        }

        all_delivery = self._get('get_all_delivery')

        if all_delivery and all_delivery.get('errcode', None) is not None:
            raise Exception(all_delivery)

        if all_delivery.get('data', None) is not None:
            for item in all_delivery['data']:
                if item.get('delivery_id', '') in additional_info:
                    item.update(additional_info[item['delivery_id']])
                else:
                    item.update({'services': [], 'biz_id': None, 'mode': ''})

        return all_delivery.get('data', [])

    def add_order(self,
                  add_source=OrderSource.Wxapp,
                  wx_appid='',
                  expect_time='',
                  order_id='',
                  openid='',
                  delivery_id='',
                  biz_id='',
                  custom_remark='',
                  tagid=None,
                  sender=None,
                  receiver=None,
                  cargo=None,
                  shop=None,
                  insured=None,
                  service=None,
                  ):
        """
        生成运单
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.addOrder.html

        :param add_source: OrderSource
        :param wx_appid: App或H5的appid，add_source=2时必填，需和开通了物流助手的小程序绑定同一open帐号
        :param expect_time: 预期的上门揽件时间
            0表示已事先约定取件时间；否则请传预期揽件时间戳，
            需大于当前时间，收件员会在预期时间附近上门。
            例如expect_time为“1557989929”，表示希望收件员将在2019年05月16日14:58:49-15:58:49内上门取货。
            说明：若选择 了预期揽件时间，请不要自己打单，由上门揽件的时候打印。
        :param order_id: 订单ID
        :param openid: 用户openid, 如果请求的订单是小程序的(OrderSource.Wxapp) 那么就需要传 openid
        :param delivery_id: 快递公司ID
        :param biz_id: 快递公司客户编码
        :param custom_remark: 快递备注信息，比如"易碎物品"
        :param tagid: 订单标签id，用于平台型小程序区分平台上的入驻方，
            tagid须与入驻方账号一一对应，非平台型小程序无需填写该字段
        :param sender: 发件人信息
        :param receiver: 收件人信息
        :param cargo: 包裹信息
        :param shop: 商品信息，会展示到物流服务通知中，当add_source=2时无需填写（不发送物流服务通知）
        :param insured: 保价信息
        :param service: 服务类型
        """

        data = {
            'add_source': add_source,
            'order_id': order_id,
            'delivery_id': delivery_id,
            'biz_id': biz_id,
            'sender': sender,
            'receiver': receiver,
            'cargo': cargo,
            'insured': insured,
            'service': service,
        }

        not_required_fields = {
            'wx_appid': wx_appid,
            'expect_time': expect_time,
            'openid': openid,
            'custom_remark': custom_remark,
            'tagid': tagid,
            'shop': shop,
        }

        for key, value in not_required_fields.items():
            if value:
                data.update({key: value})

        if not all([sender, receiver, cargo, insured, service]):
            raise ValueError('sender, receiver, cargo, insured, service 都为必填项')

        if not OrderSource.has_value(add_source):
            raise ValueError('错误的 add_source')

        if not wx_appid and add_source == OrderSource.H5app:
            raise ValueError('当为App或H5的时 wx_appid 必填')

        if not expect_time and delivery_id == 'SF':
            raise ValueError('当提交顺丰时需要预期的上门揽件时间(expect_time)')

        if not openid and add_source == OrderSource.Wxapp:
            raise ValueError('当为小程序时 openid 必填')

        if not shop and add_source == OrderSource.Wxapp:
            raise ValueError('当为小程序时 shop 必填')

        contact_info_fields = ['tel', 'mobile']
        delivery_info_fields = ['name', 'province', 'city', 'area', 'address']
        cargo_info_fields = ['count', 'weight', 'space_x', 'space_y', 'space_z', 'detail_list']
        shop_info_fields = ['wxa_path', 'img_url', 'goods_name', 'goods_count']
        insured_info_fields = ['use_insured', 'insured_value']
        service_info_fields = ['service_type', 'service_name']

        self.check_fields(sender, all, delivery_info_fields, f'sender 必须包含 {" ".join(delivery_info_fields)}')
        self.check_fields(sender, any, contact_info_fields, f'sender 必须包含 {" 或 ".join(contact_info_fields)}')

        self.check_fields(receiver, all, delivery_info_fields, f'receiver 必须包含 {" ".join(delivery_info_fields)}')
        self.check_fields(receiver, any, contact_info_fields, f'receiver 必须包含 {" 或 ".join(contact_info_fields)}')

        self.check_fields(cargo, all, cargo_info_fields, f'cargo 必须包含 {" ".join(cargo_info_fields)}')

        if not all([('name' in i and 'count' in i) for i in cargo.get('detail_list', [])]):
            raise ValueError('cargo.detail_list 的内容必须包含 name, count')

        self.check_fields(shop, all, shop_info_fields, f'shop 必须包含 {" ".join(shop_info_fields)}')

        self.check_fields(insured, all, insured_info_fields, f'insured 必须包含 {" ".join(insured_info_fields)}')

        self.check_fields(service, all, service_info_fields, f'service 必须包含 {" ".join(service_info_fields)}')

        res = self._post('add_order', data=data)

        if res and res.get('errcode', None) is not None:
            raise Exception(res)

        return res

    def cancel_order(self,
                     order_id='',
                     openid='',
                     delivery_id='',
                     waybill_id='',
                     ):
        """
        取消运单
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.cancelOrder.html

        :param order_id: 订单 ID，需保证全局唯一
        :param openid: 用户openid, 如果请求的订单是小程序的(OrderSource.Wxapp) 那么就需要传 openid
        :param delivery_id: 快递公司ID
        :param waybill_id: 运单ID
        :return: Dict
        """

        data = {
            'order_id': order_id,
            'delivery_id': delivery_id,
            'waybill_id': waybill_id,
        }

        if not all([order_id, delivery_id, waybill_id]):
            raise ValueError('order_id, delivery_id, waybill_id 都为必填项')

        if openid:
            data.update({'openid': openid})

        res = self._post('cancel_order', data=data)

        if res and not res.get('errcode', None) == 0:
            raise Exception(res)

        return res

    def get_order(self,
                  order_id='',
                  openid='',
                  delivery_id='',
                  waybill_id='',
                  ):
        """
        获取运单数据
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.getOrder.html

        :param order_id: 订单 ID，需保证全局唯一
        :param openid: 用户openid, 如果请求的订单是小程序的(OrderSource.Wxapp) 那么就需要传 openid
        :param delivery_id: 快递公司ID
        :param waybill_id: 运单ID
        :return: Dict
        """

        data = {
            'order_id': order_id,
            'delivery_id': delivery_id,
            'waybill_id': waybill_id,
        }

        if not all([order_id, delivery_id, waybill_id]):
            raise ValueError('order_id, delivery_id, waybill_id 都为必填项')

        if openid:
            data.update({'openid': openid})

        return self._post('get_order', data=data)

    def get_path(self,
                 order_id='',
                 openid='',
                 delivery_id='',
                 waybill_id=''
                 ):
        """
        查询运单轨迹
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.getPath.html

        :param order_id: 订单 ID，需保证全局唯一
        :param openid: 用户openid, 如果请求的订单是小程序的(OrderSource.Wxapp) 那么就需要传 openid
        :param delivery_id: 快递公司ID
        :param waybill_id: 运单ID
        :return: Dict
        """

        data = {
            'order_id': order_id,
            'delivery_id': delivery_id,
            'waybill_id': waybill_id,
        }

        if not all([order_id, delivery_id, waybill_id]):
            raise ValueError('order_id, delivery_id, waybill_id 都为必填项')

        if openid:
            data.update({'openid': openid})

        return self._post('get_path', data=data)

    def update_printer(self,
                       openid='',
                       action=PrinterAction.Bind,
                       tagid_list='',
                       ):
        """
        配置打印员
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.updatePrinter.html

        :param openid: 用户openid
        :param action: PrinterAction
        :param tagid_list: 用于平台型小程序设置入驻方的打印员面单打印权限，
            同一打印员最多支持10个tagid，使用逗号分隔，如填写123，456，
            表示该打印员可以拉取到tagid为123和456的下的单，非平台型小程序无需填写该字段
        :return: Dict
        """

        data = {
            'openid': openid,
            'update_type': action,
        }

        if not all([openid, action]):
            raise ValueError('openid, action 都为必填项')

        if not PrinterAction.has_value(action):
            raise ValueError('错误的 action')

        if tagid_list:
            data.update({'tagid_list': tagid_list})

        res = self._post('update_printer', data=data)

        if res and not res.get('errcode', None) == 0:
            raise Exception(res)

        return res

    def get_printer(self):
        """
        查询打印员
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.getPrinter.html
        """

        return self._post('get_printer')

    def get_quota(self,
                  biz_id='',
                  delivery_id='',
                  ):
        """
        查询电子面单余
        https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/express/by-business/logistics.getQuota.html

        :param biz_id: 快递公司客户编码
        :param delivery_id: 快递公司ID
        :return: Dict
        """

        data = {
            'biz_id': biz_id,
            'delivery_id': delivery_id,
        }

        if not all([biz_id, delivery_id]):
            raise ValueError('biz_id, delivery_id 都为必填项')

        return self._post('get_quota', data=data)
