from django.contrib import admin
from django.utils.safestring import mark_safe
from . import models

# Register your models here.


@admin.register(models.GoodsCategory)
class GoodsCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop', 'index', 'is_active')


@admin.register(models.Goods)
class GoodsAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'goods_brief',  'status', 'add_time',)
    readonly_fields = ('show_image', 'show_poster')
    search_fields = ('name',)
    list_filter = ('status', 'category')

    def show_image(self, obj):
        if obj.image:
            src = obj.image.get_file_url
            return mark_safe('<img height="62" width="62" src="{}" />'.format(src))
        else:
            return ''

    show_image.short_description = "当前封面图"

    def show_poster(self, obj):
        if obj.poster:
            src = obj.poster.get_file_url
            return mark_safe('<img height="83" width="47" src="{}" />'.format(src))
        else:
            return ''
    show_poster.short_description = "当前海报模板"

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'category', 'goods_brief', 'shop', 'status')
        }),
        ('封面图', {
            'fields': ('show_image', 'image', ),
        }),
        ('海报模板', {
            'fields': ('show_poster', 'poster',),
        }),
    )


@admin.register(models.Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('goods', 'shop', 'image', 'index')


@admin.register(models.HotWord)
class HotWordAdmin(admin.ModelAdmin):
    list_display = ('word', 'index')