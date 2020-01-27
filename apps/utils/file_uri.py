import os
import requests
from django.conf import settings
from urllib.parse import urljoin, urlparse
from django.core.files.base import ContentFile
from rest_framework import exceptions

from PIL import Image


def file_uri(request, path):
    media_root = getattr(settings, 'MEDIA_URL', 'media')  #本地media url路径
    uri = getattr(settings, 'QFILE_QINIU_BUCKET_DOMAIN', '')
    cdn_media_root = getattr(settings, 'QFILE_QINIU_MEDIA_ROOT', 'media') # 七牛云cdn的media路径
    secure_url = getattr(settings, 'QFILE_QINIU_SECURE_URL', False)
    protocol = 'https://' if secure_url else 'http://'

    if uri:
        return urljoin(protocol + uri, os.path.join(cdn_media_root, path))
    else:
        return request.build_absolute_uri(urljoin(media_root, path))


def download_img(image_url, image_path):
    save_path = '/'.join(str(image_path).split('/')[:-1])
    if not os.path.isdir(save_path):
        os.mkdir(save_path)

    try:
        img_resp = requests.get(image_url, timeout=10)
        img_content = img_resp.content
        img_content_file = ContentFile(img_content)
        with Image.open(img_content_file) as f:
            pass

        with open(image_path, "wb") as f:
            f.write(img_content)
    except (Exception,) as e:
        raise exceptions.APIException('图片加载失败...')