from django.db import models
from qcache.models import VersionedMixin
# Create your models here.


class ShortVideo(VersionedMixin, models.Model):

    user = models.ForeignKey('wxapp.WxUser', verbose_name='上传用户', related_name='video', on_delete=models.CASCADE)
    title = models.CharField(verbose_name='标题', max_length=200)
    browse = models.PositiveIntegerField(verbose_name='浏览数', default=0)
    video = models.FileField(verbose_name='短视频', upload_to='shortvideo')
    is_open = models.BooleanField(verbose_name='是否公开', default=True)
    size = models.IntegerField(verbose_name='短视频文件大小(MB)', default=0)
    goods = models.ManyToManyField('goods.Goods', verbose_name='短视频推荐商品')
    create_time = models.DateTimeField(verbose_name='上传时间', auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = '短视频'

    def __str__(self):
        return self.title


class BlockWxUser(VersionedMixin, models.Model):
    user = models.OneToOneField('wxapp.WxUser', verbose_name='上传用户', on_delete=models.CASCADE)
    create_time = models.DateTimeField(verbose_name='封禁时间', auto_now_add=True)

    @classmethod
    def block_list(cls):
        return list(BlockWxUser.objects.values_list('user_id', flat=True))
