import django_filters
from django_filters import rest_framework as filters
from wxapp.models import WxUser
from .models import WxUserAccountLog, Withdraw, RechargeRecord, WxUserCreditLog


class WxUserFilter(filters.FilterSet):
    nickname = filters.CharFilter(field_name='nickname', lookup_expr='icontains')
    province = filters.CharFilter(field_name='province', lookup_expr='icontains')
    city = filters.CharFilter(field_name='city', lookup_expr='icontains')
    date_joined = filters.DateFromToRangeFilter(field_name='date_joined')
    rebate_right = filters.CharFilter(method='rebate_right_filter')
    bonus_right = filters.CharFilter(method='bonus_right_filter')
    level = filters.CharFilter(field_name='level__level__title', lookup_expr='icontains')

    def rebate_right_filter(self, queryset, name, value):
        if value == 'true':
            return queryset.filter(rebate_right='true')
        elif value == 'false':
            return queryset.filter(rebate_right__in=['false', 'null'])
        return queryset

    def bonus_right_filter(self, queryset, name, value):
        print(value)
        if value == 'true':
            return queryset.filter(bonus_right='true')
        elif value == 'false':
            return queryset.filter(bonus_right__in=['false', 'null'])
        return queryset

    class Meta:
        model = WxUser
        fields = {
            'nickname': [],
            'province': [],
            'city': [],
            'date_joined': [],
            'testers': ['exact'],
            'upload_perm': ['exact'],
            'rebate_right': ['exact'],
            'bonus_right': ['exact'],
            'level': ['exact'],
        }


class WxUserAccountLogFilter(filters.FilterSet):
    user = filters.CharFilter(field_name='user__nickname', lookup_expr='contains')
    referral = filters.CharFilter(field_name='referral__nickname', lookup_expr='contains')
    date = filters.DateFromToRangeFilter(field_name='add_time')
    a_type = filters.ChoiceFilter(field_name='a_type', lookup_expr='exact',
                                  choices=((WxUserAccountLog.ASSET, '分享返利'), (WxUserAccountLog.BONUS, '分销返佣')))

    class Meta:
        model = WxUserAccountLog
        fields = {
            'user': [],
            'referral': [],
            'date': [],
            'a_type': ['exact'],
            'number': ['exact'],
        }


class WxUserCreditLogFilter(filters.FilterSet):
    user = filters.CharFilter(field_name='user__nickname', lookup_expr='contains')
    date = filters.DateFromToRangeFilter(field_name='add_time')

    class Meta:
        model = WxUserCreditLog
        fields = {
            'user': [],
            'date': [],
            'log_type': ['exact'],
            'number': ['exact'],
        }


class WithdrawFilter(filters.FilterSet):
    wxuser = filters.CharFilter(field_name='wxuser__nickname', lookup_expr='contains')
    wx_code = filters.CharFilter(field_name='wx_code', lookup_expr='contains')
    date = filters.DateFromToRangeFilter(field_name='add_time')

    class Meta:
        model = Withdraw
        fields = ['withdraw_no', 'wx_code', 'wxuser', 'date', 'status']


class RechargeRecordFilter(filters.FilterSet):
    wxuser = filters.CharFilter(field_name='wxuser__nickname', lookup_expr='contains')
    date = filters.DateFromToRangeFilter(field_name='create_time')
    trade_no = filters.CharFilter(field_name='trade_no', lookup_expr='contains')
    status = filters.CharFilter(field_name='status')

    class Meta:
        model = RechargeRecord
        fields = ['rchg_no', 'wxuser', 'date', 'trade_no', 'status']