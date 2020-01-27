# usr/bin/env python
# -*- coding: utf-8 -*-
from rest_framework.permissions import BasePermission, SAFE_METHODS


class ReadOnly(BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class CannotDelete(BasePermission):
    """
    Can not to delete
    """

    def has_permission(self, request, view):
        return request.method != 'DELETE'

    def has_object_permission(self, request, view, obj):
        return request.method != 'DELETE'
