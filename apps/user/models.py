from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.



class User(AbstractUser):
    phone = models.CharField(verbose_name='手机号', max_length=20, null=True, blank=True)
    shop = models.ManyToManyField('shop.Shop', verbose_name='所属店铺', related_name='admin', blank=True)

    class Meta:
        verbose_name = '管理员'

        permissions = (
            ('view_all_user', "查看所有管理员"),
        )