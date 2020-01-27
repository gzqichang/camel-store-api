from enum import Enum, unique


BASE_URL = 'https://api.weixin.qq.com/cgi-bin/express/business'

URL_SET = {
    # 账号管理接口
    'bind_account': 'account/bind',
    'get_all_account': 'account/getall',

    # 下单接口
    'get_all_delivery': 'delivery/getall',
    'add_order': 'order/add',
    'cancel_order': 'order/cancel',
    'get_order': 'order/get',

    # 查询运单轨迹
    'get_path': 'path/get',

    # 打印组件
    'update_printer': 'printer/update',
    'get_printer': 'printer/getall',

    # 查询电子面单余额
    'get_quota': 'quota/get',
}


@unique
class BasicEnum(Enum):
    @classmethod
    def has_value(cls, value):
        return any(value == i.value for i in cls)

    @classmethod
    def has_key(cls, key):
        return key in cls.__members__


@unique
class AccountAction(BasicEnum):
    """
    绑定账号
    """
    Bind = 'bind'
    Unbind = 'unbind'


@unique
class OrderSource(BasicEnum):
    """
    生成运单
    """
    Wxapp = 0
    H5app = 2  # 不发送物流服务通知


@unique
class PrinterAction(BasicEnum):
    """
    绑定打印员
    """
    Bind = 'bind'
    Unbind = 'unbind'
