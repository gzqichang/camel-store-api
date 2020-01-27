from django.apps import AppConfig


class ToolsConfig(AppConfig):
    name = 'apps.tools'

    def ready(self):
        from django.http import request
        from apps.utils.middleware.common import get_host
        request.HttpRequest.get_host = get_host
