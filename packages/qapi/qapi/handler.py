"""
    @author: Wilslee
    @email: lwf@gzqichang.com
"""
from __future__ import unicode_literals

from django.db.models.fields import Field
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.core.exceptions import PermissionDenied, FieldDoesNotExist
from django.http import Http404
from django.utils import six
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.serializers import ModelSerializer
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList

# restframework 3.7.7 开始有些函数有变化
try:
    from rest_framework.compat import set_rollback
except ImportError:
    from rest_framework.views import set_rollback


def handle_error_detail(detail):
    serializer = detail.serializer if hasattr(detail, 'serializer') else None
    serializer_fields = serializer.fields if serializer else {}

    if isinstance(detail, (dict, ReturnDict)):
        for field_name, error in detail.items():

            verbose_name = field_name
            # 直接从 serializer 拿 verbose_name
            if serializer_fields and serializer_fields.get(field_name):
                verbose_name = serializer_fields.get(field_name).label
            # elif isinstance(serializer, ModelSerializer):
            #     model_meta = serializer.Meta.model._meta
            #     try:
            #         field = model_meta.get_field(field_name)
            #         if isinstance(field, Field):
            #             verbose_name = getattr(field, 'verbose_name', field_name)
            #         elif isinstance(field, ForeignObjectRel):
            #             verbose_name = field.field.verbose_name
            #     except FieldDoesNotExist:
            #         pass

            if verbose_name == api_settings.NON_FIELD_ERRORS_KEY:
                return '{}'.format(handle_error_detail(error))
            return '{}: {}'.format(verbose_name, handle_error_detail(error))

    elif isinstance(detail, (list, ReturnList)):
        for item in detail:
            if not item:
                continue
        return handle_error_detail(item)
    else:
        return detail


def exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        data = handle_error_detail(exc.detail)

        set_rollback()
        return Response(data, status=exc.status_code, headers=headers)

    elif isinstance(exc, Http404):
        msg = _('Not found.')
        data = six.text_type(msg)

        set_rollback()
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    elif isinstance(exc, PermissionDenied):
        msg = _('Permission denied.')
        data = six.text_type(msg)

        set_rollback()
        return Response(data, status=status.HTTP_403_FORBIDDEN)

    return None
