from rest_framework import serializers
from .models import SmsRecord


class SmsRecordSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = SmsRecord
        fields = '__all__'