from io import BytesIO
from PIL import Image
import zipfile

from django import forms
from django.core.files.base import ContentFile

from . import models, settings
from .utils import functions


class UploadZipForm(forms.Form):
    zip_file = forms.FileField(label='zip 文件')
    prefix = forms.CharField(
        label='文件前缀', max_length=25, required=False, help_text="请输入文件前缀名，文件名将随机生成"
    )

    def clean_zip_file(self):
        zip_file = self.cleaned_data['zip_file']

        try:
            with zipfile.ZipFile(zip_file, "r") as f:
                self.test_zip_is_bad(f)
        except zipfile.BadZipFile as e:
            raise forms.ValidationError(str(e))

        return zip_file

    def save(self, zip_file=None):
        if zip_file is None:
            zip_file = self.cleaned_data['zip_file']

        try:
            with zipfile.ZipFile(zip_file, "r") as f:
                self.test_zip_is_bad(f)

                for filename in f.namelist():
                    try:
                        data = f.read(filename)
                    except TypeError:
                        raise TypeError("读取文件失败")
                    filename = functions.encode(filename)
                    prefix = self.cleaned_data.get("prefix", "")
                    name = functions.generate_file_name(prefix, filename)
                    self.save_file(name, data)

        except zipfile.BadZipFile as e:
            raise forms.ValidationError(str(e))

    @staticmethod
    def test_zip_is_bad(zip_file):
        bad_zip_file = zip_file.testzip()
        if bad_zip_file:
            raise forms.ValidationError('{} in the .zip archive is corrupt.'.format(bad_zip_file))

    def check_is_img(self):
        return settings.QFILE_JUST_ALLOW_IMG

    def save_file(self, name, data):
        if self.check_is_img():
            try:
                file = BytesIO(data)
                opened = Image.open(file)
                opened.verify()
            except (Exception,):
                raise OSError("无法打开非图片文件")

        content_file = ContentFile(content=data, name=name)
        return models.File.objects.create(label=name, file=content_file)
