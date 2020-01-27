from rest_framework import serializers

from . import models


class FileSerializer(serializers.HyperlinkedModelSerializer):

    relative_url = serializers.SerializerMethodField()

    class Meta:
        model = models.File
        exclude = []

    def get_relative_url(self, instance):
        return instance.image.url
