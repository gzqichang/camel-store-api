import os
import zipfile
from io import BytesIO
from PIL import Image
from rest_framework import serializers
from django.core.files.base import ContentFile
from qcache.contrib.drf import version_based_cache

from . import models, settings
from .utils import functions


@version_based_cache
class TagSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = models.Tag
        fields = ('url', 'id', 'content')

@version_based_cache
class FileSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.File
        exclude = ['active', ]
        extra_kwargs = {
            'file_type': {'read_only': True},
            'tag': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        file = attrs.get('file')
        if file:
            suffix = os.path.splitext(file.name)[-1].replace('.', '')
            suffix = suffix.lower()
            if suffix not in models.File.type_mapping.keys():
                raise serializers.ValidationError(f"请上传文件后缀为{','.join(models.File.type_mapping.keys())}的素材")
        return attrs


class BulkDestroySerializer(serializers.Serializer):
    ids = serializers.ListSerializer(child=serializers.IntegerField(), label='id列表', required=True, allow_null=False)

    def save(self, **kwargs):
        qs = models.File.objects.filter(id__in=self.validated_data.get('ids'))
        qs.update(active=False)
        return


class BulkUploadSerializer(serializers.Serializer):
    zip_file = serializers.FileField(label='zip 文件', required=True, allow_null=False)
    tag = serializers.HyperlinkedRelatedField(allow_null=True, many=True, queryset=models.Tag.objects.all(), required=False,
                                  view_name='tag-detail', write_only=True)

    def validate(self, attrs):
        zip_file = attrs['zip_file']
        try:
            with zipfile.ZipFile(zip_file, "r") as f:
                self.test_zip_is_bad(f)
        except zipfile.BadZipFile as e:
            raise serializers.ValidationError(str(e))
        return attrs

    def is_system_files(self, filename):
        for keyword in ["__MACOSX/"]:
            if filename.startswith(keyword):
                return True
            return False

    def validated_suffix(self, filename):
        """ 校验后缀名是否是图片 """
        suffix = os.path.splitext(filename)[-1].replace('.', '')
        suffix = suffix.lower()
        if suffix not in models.File.type_mapping.keys():
            return False
        return True

    def save(self, **kwargs):
        zip_file = self.validated_data['zip_file']
        tag = self.validated_data.get('tag', [])
        queryset = []
        try:
            with zipfile.ZipFile(zip_file, "r") as f:
                self.test_zip_is_bad(f)
                for filename in f.namelist():
                    if self.is_system_files(filename):       # 系统文件跳过
                        continue
                    if not self.validated_suffix(filename):  # 后缀不是图片的跳过
                        continue
                    try:
                        data = f.read(filename)
                    except TypeError:
                        raise TypeError("读取文件失败")
                    filename = functions.encode(filename)
                    instance = self.save_file(filename, data)
                    if instance:
                        queryset.append(instance)
                        if tag:
                            instance.tag.add(*tag)
        except zipfile.BadZipFile as e:
            raise serializers.ValidationError(str(e))

        return FileSerializer(instance=queryset, many=True, context=self.context).data

    @staticmethod
    def test_zip_is_bad(zip_file):
        bad_zip_file = zip_file.testzip()
        if bad_zip_file:
            raise serializers.ValidationError('{} in the .zip archive is corrupt.'.format(bad_zip_file))

    def check_is_img(self):
        return settings.QFILE_JUST_ALLOW_IMG
        # return False

    def save_file(self, name, data):
        if self.check_is_img():
            try:
                file = BytesIO(data)
                opened = Image.open(file)
                opened.verify()

            except (Exception,):
                print("无法打开非图片文件")
                return
        content_file = ContentFile(content=data, name=name)
        return models.File.objects.create(file=content_file)
