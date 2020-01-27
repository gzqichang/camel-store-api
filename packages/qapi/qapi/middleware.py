"""
    @author: 郭奕佳
    @email: gyj@gzqichang.com

    前端添加 Header 头:
    X_HTTP_METHOD_OVERRIDE: ['GET', 'POST', 'PATCH', 'DELETE', 'PUT', 'HEAD', 'OPTION']
"""
from django.utils.deprecation import MiddlewareMixin


METHOD_OVERRIDE_HEADER = 'HTTP_X_HTTP_METHOD_OVERRIDE'
METHODS = ['GET', 'POST', 'PATCH', 'DELETE', 'PUT', 'HEAD', 'OPTION']


class MethodOverrideMiddleware(MiddlewareMixin):
    """
    中间件添加顺序:
    'django.middleware.csrf.CsrfViewMiddleware',
    'qpi.middleware.MethodOverrideMiddleware',
    """
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if METHOD_OVERRIDE_HEADER not in request.META:
            return
        if request.META[METHOD_OVERRIDE_HEADER] not in METHODS:
            return
        request.method = request.META[METHOD_OVERRIDE_HEADER]
