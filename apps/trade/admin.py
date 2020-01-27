from django.contrib import admin
from . import models
# Register your models here.


@admin.register(models.Express)
class ExpressAdmin(admin.ModelAdmin):
    list_display = ('name', )
    readonly_fields = ('add_time', )
