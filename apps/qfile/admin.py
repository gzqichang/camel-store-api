import os

from django.conf import urls
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import render

from django.utils.safestring import mark_safe

from . import models, multi_upload, validators, settings


@admin.register(models.File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['thumbnail', 'label', 'download_btn', 'update_at']
    search_fields = ['label']

    change_form_template = 'file_change_form.html'
    list_per_page = 30
    save_as = True

    def get_urls(self):
        super_urls = super().get_urls()
        custom_urls = [
            urls.url(
                r'^file_upload_zip/$', self.admin_site.admin_view(self.upload_zip),
                name='file_upload_zip'
            )
        ]
        return custom_urls + super_urls

    def upload_zip(self, request):
        context = {
            'title': '批量上传文件',
            'app_label': self.model._meta.app_label,
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request)
        }

        if request.method == 'POST':
            form = multi_upload.UploadZipForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect('..')
        else:
            form = multi_upload.UploadZipForm()

        context['form'] = form
        context['adminform'] = admin.helpers.AdminForm(
            form=form,
            fieldsets=list([(None, {'fields': form.base_fields})]),
            prepopulated_fields={}
        )
        return render(request, 'admin/qfile/file/upload_zip.html', context)

    def thumbnail(self, obj):
        attr = validators.FileValidator.get_file_attr(validators.FileValidator.get_file_suffix(str(obj.file.name)))
        if attr == 'image':
            src = obj.get_file_url
        else:
            src = os.path.join(settings.STATIC_URL, "{}.jpg".format(attr))

        return mark_safe('<img height="35" width="35" src="{}" />'.format(src))

    thumbnail.short_description = "缩略图"

    def download_btn(self, obj):
        return mark_safe('<a class="button" download="" href="{}">下载</a>'.format(obj.get_file_url))

    download_btn.short_description = "操作"
