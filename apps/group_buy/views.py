from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, decorators
from rest_framework.views import APIView, status
from rest_framework.response import Response

from quser.permissions import CURDPermissionsOrReadOnly
from wxapp.permissions import OnlyWxUser
from .models import PtGroup, GroupBuyInfo
from .serializers import PtGroupSeriazlizers, GroupBuyInfoSeriazlizers, PtGroupListSeriazlizers, BuildPtGroups
from .filters import PtGroupFilter
from .utils import ptgroup_settlement

# Create your views here.


class GroupBuyInfoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GroupBuyInfoSeriazlizers
    queryset = GroupBuyInfo.objects.all()
    permission_classes = []


class PtGroupViewSet(viewsets.ModelViewSet):
    serializer_class = PtGroupSeriazlizers
    queryset = PtGroup.objects.all().order_by('status')
    permission_classes = [CURDPermissionsOrReadOnly, ]
    filterset_class = PtGroupFilter

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if getattr(user, 'is_staff', False):
            return PtGroup.objects.all().order_by('status')
        return PtGroup.objects.filter(status=PtGroup.BUILD)

    def get_serializer_class(self):
        user = getattr(self.request, 'user', None)
        if getattr(user, 'is_staff', False):
            return PtGroupSeriazlizers
        return PtGroupListSeriazlizers

    @decorators.action(['POST'], detail=False, permission_classes=[OnlyWxUser, ],
                       serializer_class=BuildPtGroups)
    def build_ptgroup(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(instance)


class Settlement(APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        ptgroups = PtGroup.objects.filter(status=PtGroup.BUILD, end_time__lte=timezone.now())
        if not ptgroups:
            return Response('success', status=status.HTTP_200_OK)
        for ptgroup in ptgroups:
            ptgroup_settlement(ptgroup)
        return Response('success', status=status.HTTP_200_OK)


