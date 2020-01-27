# coding: utf-8
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

ALL_PERMISSIONS = '所有权限'


class Command(BaseCommand):
    def handle(self, *args, **options):
        group = self.build_group_all()
        staff = self.build_staff()
        self.build_permission(group, staff)

    def build_group_all(self):
        print('1: build group for all permission')
        group = Group.objects.first()

        if group:
            group_all, created = Group.objects.update_or_create(pk=group.id, defaults=dict(name=ALL_PERMISSIONS))
        else:
            group_all = Group.objects.create(name=ALL_PERMISSIONS)

        all_permission = set(Permission.objects.all())
        group_permission = set(group_all.permissions.all())

        add = all_permission - group_permission
        remove = group_permission - all_permission
        print('add: ', add)
        print('remove: ', remove)

        group_all.permissions.remove(*remove)
        group_all.permissions.add(*add)

        return group_all

    def build_staff(self):
        print("2: build super & staff & user")
        filter_kwargs = {
            "password": getattr(settings, 'ADMIN_PASSWORD',
                                getattr(settings, 'DEFAULT_ADMIN_PASSWORD', '123456')),
        }
        username = getattr(settings, 'DEFAULT_ADMIN_USERNAME', 'admin')
        staff = self.generate_user(username=username, is_staff=True, **filter_kwargs)
        return staff

    def build_permission(self, group, admin):
        if group:
            try:
                group = Group.objects.get(name=ALL_PERMISSIONS)
            except:
                return

        if not admin:
            try:
                admin = get_user_model().objects.get(username='admin')
            except:
                return
        admin.groups.add(group)

    def generate_user(self, **kwargs):
        user_model = get_user_model()

        username = kwargs.get('username')
        password = kwargs.pop('password', '123123')

        try:
            user = user_model.objects.get(username=username)
        except user_model.DoesNotExist:
            user = user_model.objects.model(**kwargs)
            user.set_password(password)
            user.save()
        return user

