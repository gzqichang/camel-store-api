from django.apps import AppConfig
from django.db.models.signals import post_migrate, pre_delete
from django.contrib.auth.management import create_permissions as django_create_permissions

from .management import create_permissions, patch_user_permissions
from .utils import can_not_delete_group


class QUserConfig(AppConfig):
    name = 'quser'

    def ready(self):
        from django.contrib.auth.models import Group

        post_migrate.disconnect(
            django_create_permissions,
            dispatch_uid='django.contrib.auth.management.create_permissions'
        )
        post_migrate.connect(
            create_permissions,
            dispatch_uid='quser.management.create_permissions'
        )
        post_migrate.connect(
            patch_user_permissions,
            dispatch_uid='quser.management.patch_user_permissions'
        )
        pre_delete.connect(
            can_not_delete_group,
            sender=Group,
            dispatch_uid='quser.can_not_delete_group'
        )

