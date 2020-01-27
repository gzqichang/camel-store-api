import os
import posixpath
from urllib.parse import urljoin

import requests

from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import force_text, filepath_to_uri

from . import local
from .. import settings


@deconstructible
class BaseStorage(Storage):
    location = ""

    def _clean_name(self, name):
        """
        Cleans the name so that Windows style paths work
        """
        # Normalize Windows style paths
        clean_name = posixpath.normpath(name).replace('\\', '/')

        # os.path.normpath() can strip trailing slashes so we implement
        # a workaround here.
        if name.endswith('/') and not clean_name.endswith('/'):
            # Add a trailing slash as it was stripped.
            return clean_name + '/'
        else:
            return clean_name

    def _normalize_name(self, name):
        """
        Normalizes the name so that paths like /path/to/ignored/../foo.txt
        work. We check to make sure that the path pointed to is not outside
        the directory specified by the LOCATION setting.
        """
        return os.path.join(force_text(self.location), name)

    def _open(self, name, mode='rb'):
        """
        read cdn file.
        """
        raise NotImplementedError

    def _save_file(self, name, content):
        """
        save cdn file.
        """
        raise NotImplementedError

    def _delete(self, name):
        """
        delete cdn file.
        """
        raise NotImplementedError

    def _exists(self, name):
        """
        delete cdn file.
        """
        raise NotImplementedError

    def _size(self, name):
        """
        size cdn file.
        """
        raise NotImplementedError

    def _get_modified_time(self, name):
        """
        get cdn file modify time.
        """
        raise NotImplementedError

    def _listdir(self, name):
        raise NotImplementedError

    def _save(self, name, content):
        if settings.SAVE_LOCAL:
            # local save
            local.save(name, content)

        cleaned_name = self._clean_name(name)
        name = self._normalize_name(cleaned_name)

        if hasattr(content, 'chunks'):
            content_str = b''.join(chunk for chunk in content.chunks())
        else:
            content_str = content.read()

        self._save_file(name, content_str)
        return cleaned_name

    def _read(self, name):
        return requests.get(self.url(name)).content

    def delete(self, name):
        name = self._normalize_name(self._clean_name(name))
        return self._delete(name)

    def exists(self, name):
        name = self._normalize_name(self._clean_name(name))
        return self._exists(name)

    def size(self, name):
        name = self._normalize_name(self._clean_name(name))
        return self._size(name)

    def get_modified_time(self, name):
        name = self._normalize_name(self._clean_name(name))
        return self._get_modified_time(name)

    def listdir(self, path):
        path = self._normalize_name(self._clean_name(path))
        return self._listdir(path)

    def url(self, name):
        name = self._normalize_name(self._clean_name(name))
        name = filepath_to_uri(name)
        protocol = 'https://' if self.secure_url else 'http://'
        return urljoin(protocol + self.bucket_domain, name)
