from rest_framework import status, viewsets, decorators, views
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from wxapp.permissions import ReadOnly
from wxapp.models import WxUser
from apps.config.models import BoolConfig
from .permissions import VideoPermission
from .models import ShortVideo, BlockWxUser
from .serializers import ShortVideoSerializer, UploadVideoSerializer
from .filters import ShortVideoFilter
# Create your views here.


class ShortVideoViewSet(viewsets.ModelViewSet):

    queryset = ShortVideo.objects.all()
    serializer_class = ShortVideoSerializer
    permission_classes = [VideoPermission]
    filterset_class = ShortVideoFilter

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            queryset = self.queryset.order_by('-create_time')
        else:
            queryset = self.queryset.filter(is_open=True).exclude(user_id__in=BlockWxUser.block_list()).order_by('-create_time')
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return UploadVideoSerializer
        return ShortVideoSerializer

    def create(self, request, *args, **kwargs):
        if getattr(self.request.user, 'is_wechat', False) \
            and (request.user.upload_perm or BoolConfig.get_bool('video_switch')) \
                and not BlockWxUser.objects.filter(user=request.user):
            return super().create(request, *args, **kwargs)
        return Response('没有权限上传短视频', status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if getattr(request.user, 'is_staff', False) or instance.user == request.user:
            return super().destroy(request, *args, **kwargs)
        return Response('没有权限删除', status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(methods=['GET'], detail=True, permission_classes=[ReadOnly])
    def browse(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.browse += 1
        instance.save()
        return Response('success')

    @decorators.action(methods=['POST'], detail=False, permission_classes=[IsAdminUser])
    def blockuser(self, request, *args, **kwargs):
        """
        {
            "user": 1
        }
        """
        try:
            user_id = request.data.get('user', None)
            user = WxUser.objects.get(id=int(user_id))
        except TypeError:
            return Response('参数错误', status=status.HTTP_400_BAD_REQUEST)
        except WxUser.DoesNotExist:
            return Response('未找到该用户', status=status.HTTP_400_BAD_REQUEST)
        BlockWxUser.objects.update_or_create(user=user)
        return Response('账号已封禁')

    @decorators.action(methods=['GET'], detail=False, permission_classes=[ReadOnly])
    def personal(self, request, *args, **kwargs):
        """
        /api/video/video/personal/?user=1
        """
        try:
            user_id = request.query_params.get('user', None)
            user = WxUser.objects.get(id=int(user_id))
        except TypeError:
            return Response('参数错误', status=status.HTTP_400_BAD_REQUEST)
        except WxUser.DoesNotExist:
            return Response('未找到该用户', status=status.HTTP_400_BAD_REQUEST)
        if BlockWxUser.objects.filter(user=user):
            return Response('该账号已被封禁', status=status.HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset.filter(user=user))
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SwitchViews(views.APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        switch = BoolConfig.get_bool('video_switch')
        return Response({'video_switch': switch})

    def post(self, request, *args, **kwargs):
        switch = request.data.get('video_switch')
        if switch not in ['true', 'false']:
            return Response('参数错误', status=status.HTTP_400_BAD_REQUEST)
        BoolConfig.objects.update_or_create(name='video_switch', defaults={'content': switch})
        return Response('短视频设置修改成功')
