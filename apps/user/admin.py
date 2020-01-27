from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from . import models
# Register your models here.


@admin.register(models.User)
class UserAdmin(UserAdmin):
        list_display = ('username',)