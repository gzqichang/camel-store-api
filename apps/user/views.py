from django.shortcuts import render
from django.contrib.auth.models import Group
from rest_framework import views, viewsets, decorators, mixins
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from quser.permissions import CURDPermissions, has_perms
from django.conf import settings

from .models import User
from .serializers import UserSerializer, UserChangePasswordSerializer, GroupSerializer, LoginSerializer
from .filters import UserFilter


class UserLoginView(ObtainAuthToken):
    serializer_class = LoginSerializer


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by('-id')
    permission_classes = (IsAdminUser, CURDPermissions)
    filterset_class = UserFilter

    @decorators.action(['GET', 'POST'], detail=False, permission_classes=(IsAdminUser, ))
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

    @decorators.action(['POST', ], detail=True,
                             permission_classes=(IsAdminUser, has_perms('can_reset_password'), ))
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
    serializer_class = UserChangePasswordSerializer
    permission_classes = (IsAdminUser,)

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(instance=self.get_object(),
                                           data=request.data,
                                           context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(dict(code=200, detail='修改成功'))


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GroupSerializer
    queryset = Group.objects.filter(name__contains='管理员')
    permission_classes = (IsAdminUser, CURDPermissions)