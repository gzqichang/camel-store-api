from django.contrib import admin
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse, path
from django.utils.safestring import mark_safe

from . import models
from wxapp.models import WxUser
from apps.qfile.models import File
# Register your models here.

admin.site.site_title = "管理后台"
admin.site.site_header = "管理后台"


class WxUserAccountLogInline(admin.TabularInline):
    model = models.WxUserAccountLog
    fk_name = 'user'
    list_display = ('a_type', 'asset', 'referral', 'remark', 'cost')
    readonly_fields = ('user', 'a_type', 'asset', 'referral', 'remark', 'cost')
    exclude = ('note', 'number')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WxUser)
class WxUserAdmin(admin.ModelAdmin):
    list_display = ('nickname', 'gender', 'country', 'province', 'city', 'date_joined')
    inlines = [WxUserAccountLogInline, ]

    readonly_fields = ('nickname',  'language', 'gender', 'country', 'province',
                       'city', 'asset', 'total_asset', 'date_joined')
    search_fields = ('nickname',)
    list_filter = ('gender', 'testers', 'country', 'province', 'city')
    fieldsets = (
        ('用户信息', {
            'fields': ('nickname', 'language', 'gender',  'testers', 'country', 'province',
                       'city', 'asset', 'total_asset', 'date_joined')
        }),
    )

    def asset(self, instance):
        return instance.account.asset
    asset.short_description = '佣金余额'

    def total_asset(self, instance):
        return instance.account.total_asset
    total_asset.short_description = '佣金累积总额'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    actions = None
    list_filter = ('status',)
    list_display = ('withdraw_no', 'wxuser', 'amount', 'wx_code', 'add_time', 'status', 'operation')
    readonly_fields = ('withdraw_no', 'wxuser', 'amount', 'wx_code', 'add_time', 'succ_time', 'status',)
    change_list_template = 'admin/withdrawlog_change_list.html'

    fieldsets = (
        ('提款单号信息', {
            'fields': ('withdraw_no', 'wxuser', 'amount')
        }),
        ('收款人微信号', {
            'fields': ('wx_code',)
        }),
        ('提现情况', {
            'fields': ('add_time', 'succ_time', 'status', 'remark')
        })
    )

    class Media:
        js = (
            'admin/plugins/jquery/jquery-2.2.1.min.js',
            'admin/plugins/bootstrap3.3.7/js/bootstrap.min.js',
            'admin/js/base.js',
            'admin/js/account_change_list.js',
        )
        css = {
            'all': (
                'admin/plugins/bootstrap3.3.7/css/bootstrap.min.css',
                'admin/css/fix-bootcss.css',
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_info = self.model._meta.app_label, self.model._meta.model_name

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(dict(reject_url=reverse('admin:%s-%s-reject-withdraw' % self.model_info)))
        return super().changelist_view(request, extra_context)

    def operation(self, instance):
        if instance.need_pay:
            html_str = '''<a class="button" href="javascript:void(0);"
                             onclick="toWithdraw('{url}', '{no}');">已转账</a>  
                          <a class="button" href="javascript:void(0);"
                             onclick="toRejectWithdraw('{no}');">转账失败</a>  
                       '''.format(url=reverse('admin:%s-%s-agree-withdraw' % self.model_info),
                                  reject_url=reverse('admin:%s-%s-reject-withdraw' % self.model_info),
                                  no=instance.withdraw_no,
                                  )
            return mark_safe(html_str)
        return ''
    operation.short_description = '操作'

    def agree_withdraw(self, request, *args, **kwargs):
        if request.method == 'POST' and request.is_ajax():
            no = request.POST.get('no')
            try:
                instance = self.model.objects.get(withdraw_no=no)
            except self.model.DoesNotExist:
                return JsonResponse(dict(code=400, message='没有此记录, 请确认'), status=400)
            instance.succ(admin=request.user)            # 完成提现
            return JsonResponse(dict(code=0, message='提现完成'))
        return JsonResponse(dict(code=405, message='方法不允许'), status=405)

    def reject_withdraw(self, request, *args, **kwargs):
        if request.method == 'POST' and request.is_ajax():
            no = request.POST.get('no')
            remark = request.POST.get('remark')
            try:
                instance = self.model.objects.get(withdraw_no=no)
            except self.model.DoesNotExist:
                return JsonResponse(dict(code=400, message='没有此记录, 请确认'), status=400)
            instance.fail(admin=request.user, remark=remark)         #提现失败
            return JsonResponse(dict(code=0, message='提现已关闭'))
        return JsonResponse(dict(code=405, message='方法不允许'), status=405)

    def get_urls(self):
        return [
            path('agree-withdraw/', self.agree_withdraw, name='%s-%s-agree-withdraw' % self.model_info),
            path('reject-withdraw/', self.reject_withdraw, name='%s-%s-reject-withdraw' % self.model_info),
        ] + super().get_urls()


@admin.register(models.WithdrawOperationLog)
class WithdrawOperationLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'withdraw_no', 'add_time', 'operation')
    readonly_fields = ('admin', 'withdraw_no', 'add_time', 'operation')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.RechargeRecord)
class RechargeRecordAdmin(admin.ModelAdmin):
    list_display = ('wxuser', 'amount', 'real_pay', 'trade_no', 'create_time')
    readonly_fields = ('wxuser', 'amount', 'real_pay', 'trade_no', 'create_time')
    exclude = ('rchg_no', 'status')

    def get_queryset(self, request):
        queryset = super(RechargeRecordAdmin, self).get_queryset(request)
        return queryset.filter(status='paid')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
