from django.utils.deprecation import MiddlewareMixin

METHOD_OVERRIDE_HEADER = 'HTTP_X_HTTP_METHOD_OVERRIDE'


class MethodOverrideMiddleware(MiddlewareMixin):
    """
    HTTP Header：
    "X-HTTP-Method-Override": method
    Middleware Setting:
    'django.middleware.csrf.CsrfViewMiddleware',
    'utils.middleware.MethodOverrideMiddleware',
    """
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if METHOD_OVERRIDE_HEADER not in request.META:
            return
        request.method = request.META[METHOD_OVERRIDE_HEADER]
