from rest_framework.permissions import BasePermission


class OnlyWxUserCreate(BasePermission):

    def has_permission(self, request, view):
        if request.method == 'POST':
            if not request.user or not getattr(request.user, 'is_wechat', False):
                return False
            return True
        else:
            return True
