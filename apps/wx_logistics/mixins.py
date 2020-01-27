from django.db import models


class TimeLogMixin(models.Model):
    create_at = models.DateTimeField('创建时间', auto_now_add=True)
    update_at = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        abstract = True


class IsActiveMixin(models.Model):
    is_active = models.BooleanField(verbose_name="是否启用", default=True)

    class Meta:
        abstract = True
