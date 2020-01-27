from django.conf import settings
from rest_framework.permissions import IsAdminUser
from rest_framework import  status, viewsets, decorators
from quser.permissions import CURDPermissionsOrReadOnly
from rest_framework.response import Response
from . import models, serializers
from .filters import FileFilter


class TagViewSet(viewsets.ModelViewSet):
    queryset = models.Tag.objects.all()
    serializer_class = serializers.TagSerializer
    permission_classes = (IsAdminUser,)


class FileViewSet(viewsets.ModelViewSet):
    queryset = models.File.objects.filter(active=True).order_by("-id")
    serializer_class = serializers.FileSerializer
    permission_classes = (CURDPermissionsOrReadOnly,)
    filterset_class = FileFilter

    def perform_destroy(self, instance):
        instance.active = False
        instance.save()

    @decorators.action(methods=['delete'], detail=False, serializer_class=serializers.BulkDestroySerializer,
                       permission_classes=(IsAdminUser,))
    def bulk_destroy(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(methods=['post',], detail=False, serializer_class=serializers.BulkUploadSerializer,
                       permission_classes=(IsAdminUser,))
    def bulk_upload(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        res = serializer.save()
        return Response(res, status=status.HTTP_201_CREATED)