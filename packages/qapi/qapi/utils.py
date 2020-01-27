import random
import string
from io import BytesIO
from urllib.parse import urljoin
from django.core.files.storage import default_storage
from django.db import models
from django.db.models.fields import Field
from django.http import QueryDict
from django.utils import timezone
from django.utils.encoding import iri_to_uri
from django.template.loader import render_to_string


def generate_fields(model, add=None, remove=None):
    """
    根据 model 生成可用于序列化的字段列表
        @author: Zhong Lv
        if `add` and `remove` is None
            :return all fields of model
        else:
            :return fields of models after add and remove
    """
    if add is None:
        add = []
    if remove is None:
        remove = []

    result = []
    result.append('url')
    # remove.append('id')
    for field in model._meta.get_fields():
        if isinstance(field, Field):
            result.append(field.name)
    for item in remove:
        try:
            result.remove(item)
        except ValueError:
            pass
    for item in add:
        result.append(item)
    return tuple(result)


def native_to_aware(date_time, is_dst=None):
    """
    Native time to aware time
    :param date_time:
    :param is_dst:
    :return:
    """
    if timezone.is_naive(date_time):
        return timezone.make_aware(date_time, is_dst=is_dst)
    else:
        return date_time


def aware_to_native(date_time):
    """
    Aware time to native time
    :param date_time:
    :return:
    """
    if timezone.is_aware(date_time):
        return timezone.make_naive(date_time)
    else:
        return date_time


def get_date_start(date):
    """
    获取当天的开始时间
    :param date:
    :return:
    """
    return timezone.datetime.combine(date, timezone.now().time().min)


def get_date_end(date):
    """
    获取当天的结束时间
    :param date:
    :return:
    """
    return timezone.datetime.combine(date, timezone.now().time().max)


def combine_datetime(date, time):
    """
    合并日期和时间
    :param date:
    :param time:
    :return:
    """
    if isinstance(date, str):
        date = timezone.datetime.strptime(date, "%Y-%m-%d").date()
    if isinstance(time, str):
        time = timezone.datetime.strptime(time, "%H:%M").time()
    return timezone.datetime.combine(date, time)


def add_param(url, params=None):
    """
    为 url 添加参数
    :param url:
    :param params:
    :return:
    """
    params = params or {}
    if not params:
        return url
    else:
        if not isinstance(params, dict):
            return url
        host = url.split('?')[0]
        try:
            query_string = url.split('?')[1]
        except IndexError:
            query_string = None
        query_dict = QueryDict('', mutable=True)
        if query_string:
            for item in query_string.split('&'):
                key, value = item.split('=')
                query_dict.update({key: value})

        for k, v in params.items():
            if type(v) is list:
                query_dict.setlist(k, v)
            else:
                query_dict[k] = v
        return host + '?' + query_dict.urlencode()


def generate_full_uri(request=None, suffix=None):
    """
    生成绝对链接
    :param request:
    :param suffix:
    :return:
    """
    url = suffix or ''
    if request:
        request_host = request.get_host()
        host, *sub_path = request_host.split("/", 1)
        base_uri = '{scheme}://{host}'.format(scheme=request.scheme, host=host)
    else:
        base_uri = ''

    if '://' in url:
        return iri_to_uri(url)

    if sub_path:
        sub_path = sub_path[0]
        url = url.rstrip("/")
        url = "{}/{}".format(sub_path, url)

    return iri_to_uri(urljoin(base_uri, url))


def format_datetime(datetime):
    """
    本地格式化时间
    :param datetime:
    :return:
    """
    if datetime:
        return aware_to_native(datetime).strftime('%Y-%m-%d %H:%M')
    return datetime


def model2dict(instance):
    """
    读取model 转换为字典
    :param instance:
    :return:
    """
    fields = instance._meta.get_fields()
    obj = {}
    for field in fields:
        # print(field)
        name = field.name
        value = getattr(instance, name, None)
        if isinstance(field, models.Field):
            if field.choices:
                function_name = 'get_{}_display'.format(name)
                obj.update({function_name: getattr(instance, function_name)()})

            if isinstance(field, models.CharField):
                if value is None:
                    value = ''
            elif isinstance(field, models.DecimalField):
                value = str(value)
            elif isinstance(field, (models.DateTimeField, models.DateField, models.TimeField)):
                value = format_datetime(value)
            elif isinstance(field, (models.ForeignKey, models.OneToOneField)):
                value = model2dict(value)
            elif isinstance(field, models.ManyToManyField):
                if value:
                    value = [model2dict(m2m_obj) for m2m_obj in value.all()]
                else:
                    value = []
            obj.update({name: value})
    return obj


def get_update_different(instance, data):
    """
    比较实例和数据的不同之处
    :param instance:
    :param data:
    :return:
    """
    different = {}
    for key, value in data.items():
        origin_value = getattr(instance, key, None)
        if origin_value != value:
            different.update({
                key: (origin_value, value)
            })
    return different


def get_html_content(template_name, context=None, request=None):
    """
    渲染模板内容
    :param template_name:
    :param context:
    :param request:
    :return:
    """
    return render_to_string(template_name, context, request)


def generate_no(prefix=None, add_salt=False, salt_length=6):
    """
    按时间戳生成序号
    :param prefix:
    :param add_salt:
    :param salt_length:
    :return:
    """
    prefix = prefix or ''
    no = prefix + timezone.now().strftime('%Y%m%d%H%M%S')
    if add_salt:
        salt = ''.join(random.choice(string.digits) for _ in range(salt_length))
        no += salt
    return no


def format_no(num, length=12, prefix=None):
    """
    生成填充0的序号
    :param num:
    :param length:
    :param prefix:
    :return:
    """
    prefix = prefix or ''
    return '%s%0{}d'.format(length) % (prefix, num)


def generate_model_no(model, length=12, prefix=None, **kwargs):
    """
    根据 model id 生成序号
    :param model:
    :param length:
    :param prefix:
    :param kwargs:
    :return:
    """
    newest = model.objects.filter(**kwargs).order_by('id').last()
    newest_id = newest.id if newest is not None else 0
    return format_no(newest_id + 1, length, prefix)


def generate_model_day_no(model, field_name, length=12, prefix=None):
    """
    根据model和时间来生成
    :param model:
    :param field_name:
    :param length:
    :param prefix:
    :return:
    """
    today = timezone.datetime.today()
    start, end = native_to_aware(get_date_start(today)), native_to_aware(get_date_end(today))
    lookups = {
        field_name + '__range': (start, end)
    }
    count = model.objects.filter(**lookups).count()
    newest_id = count + 1
    return format_no(newest_id + 1, length, prefix)


def secret_string(s, total=11, head=3, tail=3):
    """ 针对敏感信息进行加密 """
    if not s:
        return s
    while len(s) < total:
        s += s
    assert total > head and total > tail, '`head` and `tail` must be less than `total`'
    head_str = s[:head]
    tail_str = s[-tail:]
    return head_str + '*' * (total - head - tail) + tail_str


def save_file(name, content, cover=False):
    """
    保存文件
    :param name:
    :param content:
    :param cover:
    :return:
    """
    if cover and default_storage.exists(name):
        default_storage.delete(name)
    elif cover is False and default_storage.exists(name):
        # 不覆盖文件则返回
        raise FileExistsError('File exist')

    if isinstance(content, bytes):
        content = BytesIO(content)
    return default_storage.save(name, content)
