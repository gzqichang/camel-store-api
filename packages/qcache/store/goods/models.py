from django.db import models
from pkg_resources import require

# Create your models here.
from qcache.models import VersionedMixin


class Tag(models.Model):
    label = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.label

class People(VersionedMixin, models.Model):
    name = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.name

class Goods(VersionedMixin, models.Model):
    name = models.CharField(max_length=64, unique=True, blank=False)
    price = models.FloatField(default=0.0)
    maker = models.ForeignKey(People, on_delete=models.SET_NULL, null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self):
        return self.name