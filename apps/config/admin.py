from django.contrib import admin
from . import models
from .forms import BoolConfigForm, LevelForm, VersionForm, StoreTypeForm


@admin.register(models.FaqContent)
class FapContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'add_time')


@admin.register(models.BoolConfig)
class BoolConfigAdmin(admin.ModelAdmin):
    form = BoolConfigForm

    list_display = ('label', )
    readonly_fields = ('label', )

    fieldsets = (
        ('', {
            'fields': ('label', 'content')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(content__in=['true', 'false'])


@admin.register(models.Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'create_time', 'is_active')


@admin.register(models.Level)
class LevelAdmin(admin.ModelAdmin):
    form = LevelForm
    list_display = ('title', 'threshold', 'discount', 'icon')


@admin.register(models.RechargeType)
class RechargeType(admin.ModelAdmin):
    list_display = ('amount', 'real_pay')

    def has_add_permission(self, request):
        if self.model.objects.count() >= 6:
            return False
        return True


@admin.register(models.Version)
class VersionAdmin(admin.ModelAdmin):
    form = VersionForm
    list_display = ('label',)
    readonly_fields = ('label',)

    fieldsets = (
        ('', {
            'fields': ('label', 'content')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(name='version')
        
@admin.register(models.StoreType)
class StoreTypeAdmin(admin.ModelAdmin):
    form = StoreTypeForm
    list_display = ('label',)
    readonly_fields = ('label',)

    fieldsets = (
        ('', {
            'fields': ('label', 'content')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(name='store_type')