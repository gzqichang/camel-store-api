from django.shortcuts import render
from rest_framework import viewsets

# Create your views here.

from . import models
from . import serializers

class TagViewSet(viewsets.ModelViewSet):
    queryset = models.Tag.objects.all()
    serializer_class = serializers.TagSerializer

class PeopleViewSet(viewsets.ModelViewSet):
    queryset = models.People.objects.all()
    serializer_class = serializers.PeopleSerializer

class GoodsViewSet(viewsets.ModelViewSet):
    queryset = models.Goods.objects.select_related('maker').prefetch_related('tags')
    serializer_class = serializers.GoodsSerializer