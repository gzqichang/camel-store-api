from datetime import datetime, timedelta
from apps.utils.lbs import lbs
from apps.user.utils import remind_lower_shelf


def compute_postage(goods, address=None, delivery_method=None):
    # 计算邮费，免邮或自提，邮费为0 (计算的是单次运费，要根据订单类型看是否需要*期数)
    '''

    :param goods: goods
    :param address: {'lat': , 'lng': }
    :param buyer_mention:
    :return:
    '''
    if goods.model_type == goods.REPLACE or goods.fictitious:        # 虚拟商品和积分换购免邮
        return 0
    if 'buyer' in goods.delivery_method and delivery_method == 'buyer':                              # 自提邮费为0
        return 0
    elif goods.postage_setup == goods.FREE:                          # 免邮
        return 0
    elif address:
        distance = lbs.one_to_one_distance(from_location=address,
                                           to_location={'lat': goods.shop.lat, 'lng': goods.shop.lng})
        for i in goods.postage_type:
            if distance > i.get('start') and distance < i.get('end'):
                return i.get('cost')
        else:
            return goods.postage_type[-1].get('cost', 0)
    return 0


def gtype_sell(gtype, num=1):
    gtype.stock -= num
    if gtype.stock <= 0:
        gtype.is_sell = False
    gtype.save()


def validate_can_sell(goods):
    if goods.model_type == goods.ORD:
        if not goods.ord_goods.gtypes.filter(is_sell=True):
            goods.status = goods.NOT_ENOUGH
            remind_lower_shelf(goods.shop, goods.name)
            goods.save()

    elif goods.model_type == goods.REPLACE:
        if not goods.repl_goods.gtypes.filter(is_sell=True):
            goods.status = goods.NOT_ENOUGH
            remind_lower_shelf(goods.shop, goods.name)
            goods.save()


def format_date(delivery_data, date_setup):
    """
    将配送时间设置转换为具体的日期类型或int类型
    :param delivery_data:  ["2019-01-10", "2019-01-15"] or ["1", "2", "3"]
    :param date_setup: 'specific' or 'weekly'
    :return: [datetime.date(2019, 1, 10), datetime.date(2019, 1, 15)] or [1, 2, 3, 0]
    """
    if date_setup == 'specific':
        delivery_data = list(map(lambda x: datetime.strptime(x, "%Y-%m-%d").date(), delivery_data))
    if date_setup == 'weekly':
        delivery_data = list(map(lambda x: int(x), delivery_data))
        if 0 in delivery_data:                   # 周日在js中是0，所以在使用时将0换为7
            delivery_data[delivery_data.index(0)] = 7
    delivery_data = sorted(delivery_data)
    return delivery_data


def get_delivery_data_num(delivery_data, date_setup, start=None, end=None):
    """
    计算可选范围内的配送日期的个数
    :param delivery_data: [datetime.date(2019, 1, 10), datetime.date(2019, 1, 15)] or [1, 2, 3]
    :param date_setup: 'specific' or 'weekly'
    :param start: 起始日期
    :param end: 终止日期
    :return:
    """
    if start and datetime.now().date() > start:
        start = datetime.now().date()
    if date_setup == 'specific':
        if start and end:
            return len(list(filter(lambda x: x >= start and x <= end, delivery_data)))
        else:
            return len(list(filter(lambda x: x >= datetime.now().date(), delivery_data)))
    if date_setup == 'weekly':
        num = 0
        for i in range(0, (end - start).days + 1):      #
            day = start + timedelta(days=i)
            if (day.weekday() + 1) in delivery_data:
                num += 1
        return num


