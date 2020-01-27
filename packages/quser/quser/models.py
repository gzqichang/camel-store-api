from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.utils import ProgrammingError
from django.utils.translation import gettext, gettext_lazy as _

# User Model
User = get_user_model()

# django system permissions
DJANGO_SYSTEM_PERMISSIONS = ()

# 可用于角色编辑的权限
# EDITABLE_PERMISSIONS: a list or tuple which has all editable permissions and set in settings.
# as:
# EDITABLE_PERMISSIONS = (
#     'app_label.ModelName:add|change|delete|others',
#     'auth.Group:add|change|delete',
#     ...
# )
EDITABLE_PERMISSIONS = getattr(settings, 'EDITABLE_PERMISSIONS', [])

# Permission Action
VIEW = _('view')
ADD = _('add')
CHANGE = _('change')
DELETE = _('delete')

DEFAULT_ACTIONS = ('view', 'add', 'change', 'delete')

# Action`s verbose_name
ACTIONS = {
    'view': VIEW,
    'add': ADD,
    'change': CHANGE,
    'delete': DELETE,
}

# Update Custom Actions
PERMISSION_ACTIONS = getattr(settings, 'PERMISSION_ACTIONS', {})
ACTIONS.update(PERMISSION_ACTIONS)

# Custom Action name to display permission module
MANAGE = _('Manage')

# 可编辑权限的 ids
_editable_perms_ids = set()
# 可编辑权限的 models
_editable_models = list()
# 可编辑权限的 permissions
_editable_models_perms = dict()


def _parse_perm_str(perm_str):
    header, _, actions = perm_str.partition(':')
    actions = actions.split('|')
    if len(actions) == 1 and not actions[0]:
        actions = DEFAULT_ACTIONS
    app_label, model_name = header.split('.')
    app_label = app_label.lower()
    model_name = model_name.lower()

    code_names = [
        '{}_{}'.format(action, model_name) for action in actions if action in DEFAULT_ACTIONS
    ]
    code_names.extend(list(set(actions) - set(DEFAULT_ACTIONS)))

    return header, app_label, model_name, code_names


def get_editable_permissions(editable_permissions=None):
    """
    Get the editable permissions or use which defined in settings.EDITABLE_PERMISSIONS

    :param editable_permissions:
    :return: permissions set
    """
    try:
        if not _editable_perms_ids:

            editable_permissions = editable_permissions or EDITABLE_PERMISSIONS

            for perm in editable_permissions:
                header, app_label, model_name, code_names = _parse_perm_str(perm)

                _editable_models.append(header.lower())
                _editable_models_perms[header.lower()] = code_names
                try:
                    ct = ContentType.objects.get_by_natural_key(app_label, model_name)
                    perms = Permission.objects.filter(
                        content_type=ct, codename__in=code_names
                    ).values_list('id', flat=True)

                    _editable_perms_ids.update(set(perms))
                except ContentType.DoesNotExist:
                    pass

        return Permission.objects.filter(pk__in=_editable_perms_ids).distinct()
    except ProgrammingError:
        return Permission.objects.none()


def get_user_group_permissions(user):
    """
    Get user`s group permissions

    :param user:
    :return:
    """
    groups = user.groups.all()
    perm_ids = set()

    for group in groups:
        perms = group.permissions.all().values_list('id', flat=True)
        perm_ids.update(set(perms))

    return Permission.objects.filter(pk__in=perm_ids).distinct()


def get_user_editable_permissions(user):
    """
    Get user all editable permissions
    :param user:
    :return:
    """
    perms = set(user.user_permissions.all())
    group_perms = set(get_user_group_permissions(user))
    editable_perms = set(get_editable_permissions())
    return (perms | group_perms) & editable_perms


def get_group_editable_permissions(group):
    """
    Get group editable permissions

    :param group:
    :return:
    """
    perms = set(group.permissions.all())
    editable_perms = set(get_editable_permissions())
    return perms & editable_perms


def get_permission_code(permission):
    """
    Get unique code for identify permission

    :param permission: Permission object
    :return: unique_code: unique code of Permission object
    """
    return '{app_label}.{codename}'.format(
        app_label=permission.content_type.app_label,
        # model=permission.content_type.model,
        codename=permission.codename,
    )


def get_permission_code_set(permissions):
    """
    Get set of unique code for identify permission

    :param permissions:
    :return:
    """
    permissions_code = set([get_permission_code(p) for p in permissions])
    return permissions_code


def get_user_permissions_code_set(user):
    """
    Get user editable permissions code

    :param user: Admin User object
    :return:
    """
    return get_permission_code_set(get_user_editable_permissions(user))


def get_permission_info(permission, group_permissions=None):
    """
    Get human info for Permission object

    :param permission: Permission object
    :param group_permissions: None or (list, tuple, set) of Permission object
    :return: info: verbose info which is a dict object for Permission object
    """
    perms_is_not_iterable = group_permissions is None or isinstance(group_permissions, (list, tuple, set))
    assert perms_is_not_iterable, 'group_permissions be None or list or tuple or set'

    action, _, other = permission.codename.partition('_')

    if action in DEFAULT_ACTIONS:
        human_readable_permission_name = '%s%s' % (ACTIONS.get(action, action), permission.content_type.name)
    else:
        human_readable_permission_name = gettext(permission.name)

    code = get_permission_code(permission)

    info = {
        'id': permission.id,
        'model': '%s.%s' % permission.content_type.natural_key(),
        'name': human_readable_permission_name,
        'code': code,
        'codename': permission.codename,
        'in_group': group_permissions and permission in group_permissions,
    }
    return info


def _get_permissions_tree(perms_trees, group_permissions=None):
    _tree_list = []

    for ct, perms in perms_trees.items():
        permissions = sorted(
            [get_permission_info(perm, group_permissions) for perm in perms],
            key=lambda x: _editable_models_perms[x['model']].index(x['codename'])
        )
        perm_dict = {
            'module_name': '{}{}'.format(MANAGE, ct.name),
            'model': '%s.%s' % (ct.natural_key()),
            'permissions': permissions,
        }
        _tree_list.append(perm_dict)

    _tree_list.sort(key=lambda x: _editable_models.index(x['model']))

    return _tree_list


def get_permissions_tree(permissions=None, group_permissions=None):
    """
    Get the tree of permissions for frontend to rendering

    :param permissions: iterable
    :param group_permissions: None or (list, tuple) of Permission object
    :return: list of permissions info
    """
    permissions = permissions or EDITABLE_PERMISSIONS
    _perms_tree = {}

    for perm in permissions:
        header, app_label, model_name, code_names = _parse_perm_str(perm)

        ct = ContentType.objects.get_by_natural_key(app_label, model_name)
        perms = set(Permission.objects.filter(content_type=ct, codename__in=code_names))

        _perms_tree[ct] = perms

    return _get_permissions_tree(_perms_tree, group_permissions)


def get_permission_tree_from_queryset(permissions, group_permissions=None):
    """
    Get permission tree from a queryset
    :param permissions:
    :param group_permissions:
    :return:
    """
    _perms_tree = {}
    for perm in permissions:
        ct = perm.content_type
        try:
            _perms_tree[ct].append(perm)
        except KeyError:
            _perms_tree[ct] = [perm, ]

    return _get_permissions_tree(_perms_tree, group_permissions)


def trans_codes(codes):
    _perms = {}
    for code in codes:
        app_label, code_name = code.split('.')
        action, model_name = code_name.split('_')
        try:
            _perms['%s.%s' % (app_label, model_name)].append(action)
        except KeyError:
            _perms['%s.%s' % (app_label, model_name)] = [action, ]
    return ['{}:{}'.format(key, '|'.join(value)) for key, value in _perms.items()]


def register_field_to_model(model, name, field_class, **kwargs):
    """
    Register new field to hack model cls
    :param model:
    :param name:
    :param field_class:
    :param kwargs:
    :return:
    """
    if not hasattr(model, name):
        field = field_class(**kwargs)
        field.contribute_to_class(model, name)


def replace_attr_value(model, attr, value):
    if hasattr(model, attr):
        setattr(model, attr, value)
    elif hasattr(model, '_meta') and hasattr(model._meta, attr):
        setattr(model._meta, attr, value)


def replace_model_verbose_name(model, verbose_name_field, verbose_name_plural_field):
    model_verbose_name = getattr(settings, verbose_name_field, None)
    model_verbose_name_plural = getattr(settings, verbose_name_plural_field, None)

    if model_verbose_name:
        replace_attr_value(model, 'verbose_name', model_verbose_name)

    if model_verbose_name_plural:
        replace_attr_value(model, 'verbose_name_plural', model_verbose_name_plural)


# 覆盖 Django User 的 verbose_name
replace_model_verbose_name(User, 'USER_MODEL_VERBOSE_NAME', 'USER_MODEL_VERBOSE_NAME_PLURAL')


# 覆盖 Django Group 的 verbose_name
replace_model_verbose_name(Group, 'GROUP_MODEL_VERBOSE_NAME', 'GROUP_MODEL_VERBOSE_NAME_PLURAL')


# 禁止删除超级管理员权限组
def group_delete(self, using=None, keep_parents=False):
    if self == Group.objects.first():
        return
    return super(Group, self).delete(using, keep_parents)


setattr(Group, 'delete', group_delete)
