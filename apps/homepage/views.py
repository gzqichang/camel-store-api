from django.shortcuts import render
from rest_framework import viewsets, mixins
from quser.permissions import CURDPermissionsOrReadOnly

from .models import HomeBanner, Shortcut, Module
from .serializers import HomeBannerSerializers, ShortcutSerializers, ModuleSerializers
from .filters import HomeBannerFilter, ShortcutFilter, ModuleFilter
# Create your views here.


class HomeBannerViewSet(viewsets.ModelViewSet):
    serializer_class = HomeBannerSerializers
    queryset = HomeBanner.objects.all()
    permission_classes = [CURDPermissionsOrReadOnly]
    filterset_class = HomeBannerFilter


class ShortcutViewSet(viewsets.ModelViewSet):
    serializer_class = ShortcutSerializers
    queryset = Shortcut.objects.all()
    permission_classes = [CURDPermissionsOrReadOnly]
    filterset_class = ShortcutFilter


class ModuleViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = ModuleSerializers
    queryset = Module.objects.all()
    permission_classes = [CURDPermissionsOrReadOnly]
    filterset_class = ModuleFilter