from rest_framework import exceptions
from rest_framework.permissions import SAFE_METHODS, BasePermission


def _queryset(self, view):
    assert hasattr(view, 'get_queryset') \
           or getattr(view, 'queryset', None) is not None, (
        'Cannot apply {} on a view that does not set '
        '`.queryset` or have a `.get_queryset()` method.'
    ).format(self.__class__.__name__)

    if hasattr(view, 'get_queryset'):
        queryset = view.get_queryset()
        assert queryset is not None, (
            '{}.get_queryset() returned None'.format(view.__class__.__name__)
        )
        return queryset
    return view.queryset


class CURDPermissions(BasePermission):
    """
    Permission for CURD
    """

    perms_map = {
        'GET': '%(app_label)s.view_%(model_name)s',
        'POST': '%(app_label)s.add_%(model_name)s',
        'PUT': '%(app_label)s.change_%(model_name)s',
        'PATCH': '%(app_label)s.change_%(model_name)s',
        'DELETE': '%(app_label)s.delete_%(model_name)s',
    }

    authenticated_users_only = True

    _queryset = _queryset

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }

        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)

        return self.perms_map[method] % kwargs

    def has_permission(self, request, view):
        # Workaround to ensure DjangoModelPermissions are not applied
        # to the root view when using DefaultRouter.
        if getattr(view, '_ignore_model_permissions', False):
            return True

        # 如果非管理员用户进入直接返回 False
        try:
            if not request.user or not request.user.is_authenticated or not request.user.is_staff:
                return False
        except AttributeError:
            return False

        queryset = self._queryset(view)
        perms = self.get_required_permissions(request.method, queryset.model)

        return request.user.has_perm(perms)


class CURDPermissionsOrReadOnly(CURDPermissions):
    """
    Return True if request method in SAFE_METHODS
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().has_permission(request, view)


def has_perms(*codenames):
    """
    Return True/False by codenames

    :param codenames:
    :return:
    """
    default_actions = ('view', 'add', 'change', 'delete')

    class ActionsPermissions(BasePermission):

        _queryset = _queryset

        def get_required_permissions(self, code_name, model_cls):
            """
            Given a model and an HTTP method, return the list of permission
            codes that the user is required to have.
            """
            app_label = model_cls._meta.app_label
            model_name = model_cls._meta.model_name

            if code_name in default_actions:
                return '%s.%s_%s' % (app_label, code_name, model_name)
            return '%s.%s' % (app_label, code_name)

        def has_permission(self, request, view):
            if getattr(view, '_ignore_model_permissions', False):
                return True

            if not request.user or not request.user.is_authenticated or not request.user.is_staff:
                return False

            if codenames:
                queryset = self._queryset(view)
                model = queryset.model
                perms = [self.get_required_permissions(code_name, model)
                         for code_name in codenames]
                return request.user.has_perms(perms)

            return False

    return ActionsPermissions


def enable_methods(*methods):
    """
    Return True/False by allowed methods

    :param methods:
    :return:
    """

    class Permissions(BasePermission):

        def has_permission(self, request, view):
            _methods = [m.upper() for m in methods]
            if request.method in _methods:
                return True
            return False

    return Permissions


def disable_methods(*methods):
    """
    Return True/False by disable methods
    :param methods:
    :return:
    """

    class Permissions(BasePermission):
        def has_permission(self, request, view):
            _methods = [m.upper() for m in methods]
            if request.method in _methods:
                return False
            return True

    return Permissions
