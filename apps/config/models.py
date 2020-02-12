import os
from datetime import datetime, timedelta
from decimal import Decimal
import pytz
from django.conf import settings
from django.db import models
from django.utils import timezone

from django_global_request.middleware import get_request

from qcache.models import VersionedMixin


# 系统配置
class SystemConfig(VersionedMixin, models.Model):
    name = models.CharField('配置项', max_length=64, unique=True)
    content = models.TextField('配置内容', blank=True, default='')
    label = models.CharField(verbose_name='配置名称', max_length=64, null=True)

    class Meta:
        db_table = 'system_config'
        verbose_name = verbose_name_plural = '系统配置'

    def __str__(self):
        return self.name

    @classmethod
    def cache_all_config(cls):
        all_config = {}
        for cfg in cls.objects.all():
            all_config[cfg.name] = cfg
        setattr(get_request(), 'all_config', all_config)
        return all_config

    @classmethod
    def get(cls, name):
        all_config = getattr(get_request(), 'all_config', None)
        if not all_config:
            all_config = cls.cache_all_config()
        return all_config.get(name, None)

    @classmethod
    def get_value(cls, name):
        instance = cls.get(name)
        return instance.content if instance else ''


class FaqContent(VersionedMixin, models.Model):
    title = models.CharField(max_length=64, verbose_name='标题')
    content = models.TextField(verbose_name='内容')
    index = models.PositiveSmallIntegerField(verbose_name='排序', default=0)
    add_time = models.DateTimeField(verbose_name='添加时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '客服FAQ内容'
        ordering = ('index', '-add_time',)

    def __str__(self):
        return self.title


class Marketing(SystemConfig):
    class Meta:
        proxy = True
        verbose_name = verbose_name_plural = '推广设置'

    @classmethod
    def get_value(cls, name):
        instance = cls.get(name)
        return Decimal(instance.content) if instance else Decimal('0')

    @classmethod
    def value_eq_zero(cls, name):
        if cls.get_value(name) == Decimal('0'):
            return True
        return False


class Version(SystemConfig):
    class Meta:
        proxy = True
        verbose_name = verbose_name_plural = '后台版本'

class StoreType(SystemConfig):
    class Meta:
        proxy = True
        verbose_name = verbose_name_plural = '店铺类型'

class StoreName(SystemConfig):
    class Meta:
        proxy = True
        verbose_name = verbose_name_plural = '店铺名称'

    @classmethod
    def get_name(cls):
        instance = cls.get('store_name')
        return instance.content if instance else '骆驼小店'

    @classmethod
    def set_name(cls, name):
        instance = cls.get('store_name')
        instance.content = name
        instance.save()
        return instance.content if instance else '骆驼小店'


class Notice(VersionedMixin, models.Model):
    title = models.CharField(max_length=64, verbose_name='消息标题')
    content = models.TextField(verbose_name='消息内容')
    is_active = models.BooleanField(verbose_name='是否启用', default=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    update_time = models.DateTimeField(verbose_name='更新时间', auto_now=True)
    index = models.PositiveSmallIntegerField(verbose_name='排序', default=0)

    class Meta:
        verbose_name = verbose_name_plural = '店铺消息'
        ordering = ('index', '-create_time',)

    def __str__(self):
        return self.title


class BoolConfig(SystemConfig):
    class Meta:
        proxy = True
        verbose_name = verbose_name_plural = '开关式配置项'

    @classmethod
    def get_value(cls, name):
        instance = cls.get(name)
        return instance.content if instance else 'true'

    @classmethod
    def get_bool(cls, name):
        if cls.get_value(name) == 'true':
            return True
        elif cls.get_value(name) == 'false':
            return False


class DatetimeConfig(SystemConfig):
    class Meta:
        proxy = True
        verbose_name = verbose_name_plural = '时间式配置项'

    time_format = '%Y-%m-%d %H:%M:%S'

    @classmethod
    def get_value(cls, name):
        instance = cls.get(name)
        if instance and instance.content:
            instance = pytz.UTC.localize(datetime.strptime(instance.content, cls.time_format))
        return instance

    @classmethod
    def is_valid(cls, name):
        # if StoreType.get_value('store_type') == 'camel':
        #     return True
        value = cls.get_value(name)
        return value > timezone.now() if value is not None else False

    @classmethod
    def extend_expired_date(cls, name, days):
        instance = cls.get(name)
        value = cls.get_value(name)

        # 如果插件已经过期一段时间了则用当前的时间为基准
        expired_date = value if cls.is_valid(name) else timezone.now()
        expired_date += timedelta(days=days)

        instance.content = expired_date.strftime(cls.time_format)
        instance.save()


class Level(VersionedMixin, models.Model):
    title = models.CharField(verbose_name='会员等级名称', max_length=128, unique=True)
    threshold = models.DecimalField(verbose_name='充值金额门槛', max_digits=15, decimal_places=2, unique=True)
    discount = models.PositiveSmallIntegerField(verbose_name='折扣', default=100, help_text='%')
    icon = models.OneToOneField('qfile.File', verbose_name='图标', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = verbose_name_plural = '会员等级'
        ordering = ('threshold',)

    def __str__(self):
        return self.title


class RechargeType(VersionedMixin, models.Model):
    amount = models.DecimalField(verbose_name='充值金额', max_digits=15, decimal_places=2, unique=True)
    real_pay = models.DecimalField(verbose_name='实付金额', max_digits=15, decimal_places=2, unique=True)
    proposal = models.BooleanField(verbose_name='推荐', default=False)

    class Meta:
        verbose_name = verbose_name_plural = '优惠充值'
        ordering = ('amount',)


class StoreLogo(VersionedMixin, models.Model):
    label = models.CharField(verbose_name='图片配置项', max_length=20, unique=True)
    image = models.ForeignKey('qfile.File', verbose_name='图片', null=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = verbose_name_plural = '平台图片配置'

    def __str__(self):
        return self.label

    @classmethod
    def get(cls, label):
        instance = cls.objects.filter(label=label).first()
        if not instance or not instance.image:
            return None
        return instance


class WeChatConfig(VersionedMixin, models.Model):
    """
    导入setting的环境变量
    """
    key = models.CharField(verbose_name='变量名', max_length=256)
    value = models.TextField(verbose_name='变量值')

    @classmethod
    def set(cls, key, value):
        cls.objects.update_or_create(key=key, defaults={"value": value})

    @staticmethod
    def write_file(value, file_name):
        file_path = os.path.join(settings.BASE_DIR, 'conf/cert_file/')
        if not os.path.exists(file_path):
            os.mkdir(file_path)
        with open(os.path.join(file_path, file_name), 'w') as f:
            f.write(value)

    @classmethod
    def environ(cls):
        for instance in cls.objects.all():
            if instance.key == 'wx_pay_mch_cert':
                cls.write_file(instance.value, 'apiclient_cert.pem')
            elif instance.key == 'wx_pay_mch_key':
                cls.write_file(instance.value, 'apiclient_key.pem')
            else:
                settings.SETTINGS_CONFIG_DEFAULT[instance.key.upper()] = instance.value

        with open(settings.CONFIG_FILE_PATH, "w") as file:
            settings.SETTINGS_CONFIG.write(file)


