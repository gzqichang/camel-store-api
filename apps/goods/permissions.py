from rest_framework.permissions import BasePermission


class CreateTemplatePermission(BasePermission):

    def has_permission(self, request, view):
        if request.method == 'POST':
            if not request.user or not request.user.is_staff:
                return False
            if 'is_template' in request.data.keys():
                return request.user.has_perm('goods.create_template')
            else:
                return True
        else:
            return True

class UpdatePermission(BasePermission):

    def has_permission(self, request, view):
        if request.method in ['PUT', 'PATCH']:
            if not request.user or not request.user.is_staff:
                return False
            if 'rebate' in request.data.keys() or 'bonus' in request.data.keys():
                return request.user.has_perm('goods.change_rebate_bonus')
            else:
                return True
        else:
            return True