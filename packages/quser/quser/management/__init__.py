from django.apps import apps as global_apps
from django.db import DEFAULT_DB_ALIAS, router
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.management import _get_all_permissions
from django.utils.translation import gettext_lazy as _


def create_permissions(app_config, verbosity=2, interactive=True, using=DEFAULT_DB_ALIAS, apps=global_apps, **kwargs):
    if not app_config.models_module:
        return

    app_label = app_config.label
    try:
        app_config = apps.get_app_config(app_label)
        ContentType = apps.get_model('contenttypes', 'ContentType')
        Permission = apps.get_model('auth', 'Permission')
    except LookupError:
        return

    if not router.allow_migrate_model(using, Permission):
        return

    # This will hold the permissions we're looking for as
    # (content_type, (codename, name))
    searched_perms = []
    # The codenames and ctypes that should exist.
    ctypes = set()
    for klass in app_config.get_models():
        # Force looking up the content types in the current database
        # before creating foreign keys to them.
        ctype = ContentType.objects.db_manager(using).get_for_model(klass)

        ctypes.add(ctype)
        klass._meta.default_permissions = ('view', 'add', 'change', 'delete')
        for perm in _get_all_permissions(klass._meta):
            searched_perms.append((ctype, perm))

    # Find all the Permissions that have a content_type for a model we're
    # looking for.  We don't need to check for codenames since we already have
    # a list of the ones we're going to create.
    all_perms = set(Permission.objects.using(using).filter(
        content_type__in=ctypes,
    ).values_list(
        "content_type", "codename"
    ))

    perms = [
        Permission(codename=codename, name=name, content_type=ct)
        for ct, (codename, name) in searched_perms
        if (ct.pk, codename) not in all_perms
    ]
    Permission.objects.using(using).bulk_create(perms)
    if verbosity >= 2:
        for perm in perms:
            print("Adding permission '%s'" % perm)


def patch_user_permissions(app_config, verbosity=2, interactive=True,
                           using=DEFAULT_DB_ALIAS, apps=global_apps, **kwargs):
    if not app_config.models_module:
        return

    if app_config.label != 'quser':
        return

    try:
        ContentType = apps.get_model('contenttypes', 'ContentType')
        Permission = apps.get_model('auth', 'Permission')
    except LookupError:
        return

    if not router.allow_migrate_model(using, Permission):
        return

    perms = [('can_reset_password', _('Can Reset User Password')), ]
    perms.extend(getattr(settings, 'USER_CUSTOM_PERMISSIONS', []))

    ct = ContentType.objects.get_for_model(get_user_model())

    for perm in perms:
        Permission.objects.update_or_create(content_type=ct,
                                            codename=perm[0],
                                            defaults=dict(name=perm[1]))
