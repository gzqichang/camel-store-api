from django.contrib import admin
from .models import SmsRecord, SmsSwitch
# Register your models here.


@admin.register(SmsRecord)
class SmsRecordAdmin(admin.ModelAdmin):
    list_display = ('phone', 'model_code', 'add_time')
    list_filter = ('model_code', 'add_time')


    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SmsSwitch)
class SmsSwitchAdmin(admin.ModelAdmin):
    list_display = ('label', 'switch')

    readonly_fields = ('label', )

    fieldsets = (
        ('', {
            'fields': ('label', 'switch')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False