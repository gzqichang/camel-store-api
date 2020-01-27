from django.conf import settings
from django.contrib.auth.models import Group

from rest_framework import views, viewsets, decorators
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from captcha.models import CaptchaStore
from captcha.views import captcha_image_url

from .permissions import has_perms
from . import models, serializers, permissions


class CaptchaView(views.APIView):
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        new_key = CaptchaStore.pick()
        response = {
            'key': new_key,
            'image_url': request.build_absolute_uri(location=captcha_image_url(new_key)),
        }
        return Response(response)


class UserLoginView(ObtainAuthToken):
    serializer_class = serializers.UserLoginSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    + 获取或修改用户自身信息: `(get|post) ==> /users/info/`
    + 获取用户权限列表: `(get) ==> /users/permissions/`

            - permissions: (set) 给出当前登录用户的权限集合
            - permission_trees: (list) 给出当前登录用户可编辑的权限, 如果用户没有添加组的权限则为空列表
                - id: 权限 ID
                - model: 权限所属数据表
                - name: 权限名称
                - code: 权限的唯一 code
                - codename: 权限 codename, 用于排序用, 不唯一
                - in_group: 是否在组内, 判断是否在权限组内, 在权限组 (Group) 编辑时可以用于判断权限是否在组内.

    + 重置密码: `(post) ==> /users/<pk>/reset_password/`

    """
    serializer_class = serializers.UserSerializer
    queryset = models.User.objects.all().order_by('-id')
    permission_classes = (IsAdminUser, permissions.CURDPermissions)

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.exclude(pk=self.request.user.pk)

    @decorators.action(['GET', 'POST'], detail=False, permission_classes=(IsAdminUser,))
    def info(self, request, *args, **kwargs):
        """ 获取或修改用户信息 """
        if request.method == 'GET':
            serializer = self.get_serializer(self.request.user)
        elif request.method == 'POST':
            serializer = self.get_serializer(instance=self.request.user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        else:
            raise MethodNotAllowed(request.method)
        return Response(serializer.data)

    @decorators.action(['GET'], detail=False, permission_classes=(IsAdminUser,))
    def permissions(self, request, *args, **kwargs):
        """ 获取用户可编辑权限 """
        user_permissions = models.get_user_editable_permissions(request.user)
        permissions_tree = models.get_permission_tree_from_queryset(user_permissions)
        return Response({
            'permissions': models.get_user_permissions_code_set(request.user),
            'permission_trees': permissions_tree if request.user.has_perm('auth.add_group') else [],
        })

    @decorators.action(
        ['POST', ],
        detail=True,
        permission_classes=(IsAdminUser, has_perms('can_reset_password'),)
    )
    def reset_password(self, request, *args, **kwargs):
        """ 管理员密码重置 """
        instance = self.get_object()

        # todo: 校验下 ID 和权限, 更安全的写法
        # user_id = str(request.data.get('user_id', 0))
        # if user_id != str(self.request.user.pk) or not self.request.user.is_staff:
        #     raise PermissionDenied('没有权限重置用户密码')

        instance.set_password(getattr(settings, 'DEFAULT_ADMIN_PASSWORD', '123123'))
        instance.save()
        return Response(dict(code=200, detail='重置成功'))


class UserChangePasswordView(views.APIView):
    """
    用户修改密码
    """
    serializer_class = serializers.UserChangePasswordSerializer
    permission_classes = (IsAdminUser,)

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            instance=self.get_object(),
            data=request.data,
            context=dict(request=request)
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(dict(code=200, detail='修改成功'))


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.GroupListSerializer
    queryset = Group.objects.all().order_by('-id', 'name')
    permission_classes = (IsAdminUser, permissions.CURDPermissions)

    def get_serializer(self, *args, **kwargs):
        if kwargs.get('many'):
            self.serializer_class = serializers.GroupListSerializer
        else:
            self.serializer_class = serializers.GroupDetailSerializer
        return super().get_serializer(*args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == Group.objects.first():
            raise PermissionDenied(detail='超级管理员权限不能删除')
        return super().destroy(request, *args, **kwargs)
