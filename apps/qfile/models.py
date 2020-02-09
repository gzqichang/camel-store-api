import os

from django.db import models

from qcache.models import VersionedMixin

from .validators import FileValidator
from .utils.models import TimeLogMixin
from . import settings


class Tag(VersionedMixin, models.Model):
    content = models.CharField(verbose_name='内容', max_length=20)

    class Meta:
        verbose_name = verbose_name_plural = "标签"

    def __str__(self):
        return self.content


class File(VersionedMixin, TimeLogMixin, models.Model):
    VIDEO = 'video'
    PICTURE = 'picture'
    AUDIO = 'audio'

    FILE_TYPE = ((VIDEO, '视频'), (PICTURE, '图片'), (AUDIO, '音频'))

    label = models.CharField(
        verbose_name="文件名称", max_length=64, db_index=True, blank=True, help_text="不填写时，文件名称为上传文件：类型-名称"
    )
    file_type = models.CharField(verbose_name='素材类型', choices=FILE_TYPE, max_length=128, default=PICTURE)
    active = models.BooleanField(verbose_name='是否有效', default=True)
    file = models.FileField(upload_to="file", verbose_name="文件")
    tag = models.ManyToManyField(Tag, related_name='files', blank=True)

    type_mapping = {
        'jpg': PICTURE,
        'jpeg': PICTURE,
        'png': PICTURE,
        'mp4': VIDEO,
        'mp3': AUDIO,
                    }

    @property
    def get_file_url(self):
        return os.path.join(settings.MEDIA_URL, self.file.name)

    def save(self, *args, **kwargs):
        if not self.label:
            self.label = FileValidator.generate_file_name(self.file.name)
        suffix = os.path.splitext(self.file.name)[-1].replace('.', '')
        suffix = suffix.lower()
        self.file_type = self.type_mapping.get(suffix, self.PICTURE)
        super().save(*args, **kwargs)

    def __str__(self):
        return '{}(updated at {})'.format(self.label, self.update_at)

    class Meta:
        verbose_name = verbose_name_plural = "文件管理"
