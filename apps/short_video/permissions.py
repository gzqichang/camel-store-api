from rest_framework.permissions import BasePermission, SAFE_METHODS


class VideoPermission(BasePermission):
    """Just WxUser"""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.method == 'POST':
            return getattr(request.user, 'is_wechat', False)
        if request.method in ['PUT', 'PATCH']:
            return getattr(request.user, 'is_staff', False)
        if request.method == 'DELETE':
            return getattr(request.user, 'is_wechat', False) or getattr(request.user, 'is_staff', False)