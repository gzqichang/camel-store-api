from django.contrib import admin

# Register your models here.

from . import models

admin.site.register(models.Tag)
admin.site.register(models.Goods)
admin.site.register(models.People)