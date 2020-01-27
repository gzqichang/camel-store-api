from django.conf import settings

STATIC_URL = settings.STATIC_URL
MEDIA_URL = settings.MEDIA_URL

SAVE_LOCAL = getattr(settings, "SAVE_LOCAL", False)
QFILE_JUST_ALLOW_IMG = getattr(settings, "QFILE_JUST_ALLOW_IMG", False)

QFILE_QINIU_ACCESS_KEY = getattr(settings, "QFILE_QINIU_ACCESS_KEY", "")
QFILE_SECRET_KEY = getattr(settings, "QFILE_SECRET_KEY", "")
QFILE_QINIU_BUCKET_DOMAIN = getattr(settings, "QFILE_QINIU_BUCKET_DOMAIN", "")
QFILE_QINIU_BUCKET_NAME = getattr(settings, "QFILE_QINIU_BUCKET_NAME", "")
QFILE_QINIU_SECURE_URL = getattr(settings, "QFILE_QINIU_SECURE_URL", "")

QFILE_QINIU_MEDIA_ROOT = getattr(settings, "QFILE_QINIU_MEDIA_ROOT", "media")
QFILE_QINIU_STATIC_ROOT = getattr(settings, "QFILE_QINIU_STATIC_ROOT", "static")
