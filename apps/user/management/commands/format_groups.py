from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.db import transaction


class Command(BaseCommand):
    help = "创建超级管理员和管理员角色"

    def add_arguments(self, parser):
        parser.add_argument('action', nargs='?', help='action ?')

    def superuser_permission(self):
        return Permission.objects.all()

    def user_permission(self):
        exclude = []
        for i in ['group', 'permission', 'config', 'boolconfig', 'systemconfig', 'systemconfig', 'shop', 'user']:
            exclude = exclude + ['add_' + i, 'change_' + i, 'delete_' + i]
        for i in ['permission', 'rechargerecord', 'withdraw', 'withdrawoperationlog', 'wxuseraccountlog',
                  'level', 'hotword', 'faqcontent', 'notice', 'rechargetype']:
            exclude = exclude + ['add_' + i, 'change_' + i, 'delete_' + i, 'view_' + i]
        exclude = exclude + ['change_rebate_bonus', 'create_template', 'view_total_count', 'view_all_shop', 'view_all_user',
                             'change_account']
        return Permission.objects.exclude(codename__in=exclude)

    def handle(self, *args, **options):
        with transaction.atomic():
            print('start!')
            superuser, created = Group.objects.get_or_create(pk=1) # python manage.py init_staff 会创建一个所有权限的角色，更名为超级管理员
            superuser.name = '超级管理员'
            superuser.save()
            user, created = Group.objects.get_or_create(name='管理员')
            # superuser.permissions.remove(*superuser.permissions.all())
            user.permissions.remove(*user.permissions.all())
            superuser.permissions.add(*self.superuser_permission())
            user.permissions.add(*self.user_permission())
            print('ok!')
