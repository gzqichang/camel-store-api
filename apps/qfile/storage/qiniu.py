"""
use the github code.
https://github.com/glasslion/django-qiniu-storage
"""

import os

import datetime
import six

from django.core.files.base import File
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_bytes, force_text
from django.utils import timezone

from qiniu import Auth, BucketManager, put_data

from . import base
from .. import settings


class QiniuFile(File):
    def __init__(self, name, storage, mode):
        self._storage = storage
        self._name = name[len(self._storage.location):].lstrip('/')
        self._mode = mode
        self.file = six.BytesIO()
        self._is_dirty = False
        self._is_read = False
        super().__init__(self.file, self._name)

    @property
    def size(self):
        if self._is_dirty or self._is_read:
            # Get the size of a file like object
            # Check http://stackoverflow.com/a/19079887
            old_file_position = self.file.tell()
            self.file.seek(0, os.SEEK_END)
            self._size = self.file.tell()
            self.file.seek(old_file_position, os.SEEK_SET)
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self._name)
        return self._size

    def read(self, num_bytes=None):
        if not self._is_read:
            content = self._storage._read(self._name)
            self.file = six.BytesIO(content)
            self._is_read = True

        if num_bytes is None:
            data = self.file.read()
        else:
            data = self.file.read(num_bytes)

        if 'b' in self._mode:
            return data
        else:
            return force_text(data)

    def write(self, content):
        if 'w' not in self._mode:
            raise AttributeError("File was opened for read-only access.")

        self.file.write(force_bytes(content))
        self._is_dirty = True
        self._is_read = True

    def close(self):
        if self._is_dirty:
            self.file.seek(0)
            self._storage._save(self._name, self.file)
        self.file.close()


@deconstructible
class QiniuStorage(base.BaseStorage):
    def __init__(self):
        self.auth = Auth(settings.QFILE_QINIU_ACCESS_KEY, settings.QFILE_SECRET_KEY)
        self.bucket_name = settings.QFILE_QINIU_BUCKET_NAME
        self.bucket_domain = settings.QFILE_QINIU_BUCKET_DOMAIN
        self.bucket_manager = BucketManager(self.auth)
        self.secure_url = settings.QFILE_QINIU_SECURE_URL

    def _open(self, name, mode='rb'):
        name = self._normalize_name(self._clean_name(name))
        return QiniuFile(name, self, mode)

    def _save_file(self, name, content):
        name = self._normalize_name(self._clean_name(name))
        token = self.auth.upload_token(self.bucket_name)
        ret, info = put_data(token, name, content)
        if ret is None or ret['key'] != name:
            raise IOError(info)

    def _delete(self, name):
        name = self._normalize_name(self._clean_name(name))
        ret, info = self.bucket_manager.delete(self.bucket_name, name)
        if ret is None or info.status_code == 612:
            raise IOError(info)
        else:
            return True

    def _exists(self, name):
        name = self._normalize_name(self._clean_name(name))
        ret, info = self.bucket_manager.stat(self.bucket_name, name)
        return True if ret else False

    def _size(self, name):
        name = self._normalize_name(self._clean_name(name))
        ret, info = self.bucket_manager.stat(self.bucket_name, name)
        return ret['fsize']

    def _get_modified_time(self, name):
        name = self._normalize_name(self._clean_name(name))
        ret, info = self.bucket_manager.stat(self.bucket_name, name)
        time_stamp = float(ret['putTime']) / 10000000
        return datetime.datetime.fromtimestamp(time_stamp, tz=timezone.get_current_timezone())

    def _listdir(self, name):
        name = self._normalize_name(self._clean_name(name))
        if name and not name.endswith('/'):
            name += '/'

        dir_list = self._bucket_lister(self.bucket_manager, self.bucket_name, prefix=name)
        files = []
        dirs = set()
        base_parts = name.split("/")[:-1]
        for item in dir_list:
            parts = item['key'].split("/")
            parts = parts[len(base_parts):]
            if len(parts) == 1:
                # File
                files.append(parts[0])
            elif len(parts) > 1:
                # Directory
                dirs.add(parts[0])
        return list(dirs), files

    @staticmethod
    def _bucket_lister(manager, bucket_name, prefix=None, marker=None, limit=None):
        """
        A generator function for listing keys in a bucket.
        """
        ret, eof, info = manager.list(bucket_name, prefix=prefix, limit=limit, marker=marker)

        if ret is None:
            raise IOError(info)

        return [item for item in ret.get("items", [])]


class QiniuMediaStorage(QiniuStorage):
    location = settings.QFILE_QINIU_MEDIA_ROOT


class QiniuStaticStorage(QiniuStorage):
    location = settings.QFILE_QINIU_STATIC_ROOT
