from django.shortcuts import render
from rest_framework import viewsets, mixins, decorators, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from .permissions import OnlyWxUserCreate
from .models import FeedBack, FeedbackOperationLog
from .serializers import FeedBackSerializer
from .filters import FeedbackFilter


# Create your views here.


class NotDeleteViewSet(mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.CreateModelMixin,
                       mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    pass


class FeedBackViewSet(NotDeleteViewSet):
    serializer_class = FeedBackSerializer
    queryset = FeedBack.objects.all()
    permission_classes = [IsAuthenticated, OnlyWxUserCreate]
    filterset_class = FeedbackFilter

    def get_queryset(self):
        if getattr(self.request.user, 'is_wechat', False):
            return FeedBack.objects.filter(user=self.request.user)
        if getattr(self.request.user, 'is_staff', False):
            return FeedBack.objects.all()
        return FeedBack.objects.none()

    @decorators.action(methods=['POST', ], detail=True, permission_classes=[IsAdminUser, ])
    def solve(self, request, *args, **kwargs):
        """
        Post:
        {\n
            "solve":  "true" 或 "false" (true 已解决， 2 再次打开为未解决)
        }
        """
        instance = self.get_object()
        solve = request.data.get('solve', None)
        if not solve:
            Response('参数错误', status=status.HTTP_400_BAD_REQUEST)
        admin = request.user
        if instance.solve and solve == 'false':
            FeedbackOperationLog.create(admin, instance, '再次打开为未解决')
            instance.solve = False
        if not instance.solve and solve == 'true':
            FeedbackOperationLog.create(admin, instance, '状态变更为已解决')
            instance.solve = True
        instance.save()
        return Response('状态已变更')
