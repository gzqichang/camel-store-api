"""
    @author: 郭奕佳
    @email: gyj@gzqichang.com
"""
from __future__ import unicode_literals

import json
from collections import OrderedDict
from urllib.parse import urlparse
from django.core.exceptions import ObjectDoesNotExist
from django.utils.encoding import uri_to_iri
from django.urls import NoReverseMatch, Resolver404, get_script_prefix, resolve
from rest_framework import serializers


class ObjectHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    serializer_class = None

    def __init__(self, serializer_class, view_name=None, **kwargs):
        if serializer_class is not None:
            self.serializer_class = serializer_class
        assert self.serializer_class is not None, 'The `serializer_class` argument is required.'
        super().__init__(view_name, **kwargs)

    def to_internal_value(self, data):
        request = self.context.get('request', None)
        try:
            data = json.loads(data).get("url")

            http_prefix = data.startswith(('http:', 'https:'))
        except AttributeError:
            self.fail('incorrect_type', data_type=type(data).__name__)

        if http_prefix:
            # If needed convert absolute URLs to relative path
            data = urlparse(data).path
            prefix = get_script_prefix()
            if data.startswith(prefix):
                data = '/' + data[len(prefix):]

        data = uri_to_iri(data)

        try:
            match = resolve(data)
        except Resolver404:
            self.fail('no_match')

        try:
            expected_viewname = request.versioning_scheme.get_versioned_viewname(
                self.view_name, request
            )
        except AttributeError:
            expected_viewname = self.view_name

        if match.view_name != expected_viewname:
            self.fail('incorrect_match')

        try:
            return self.get_object(match.view_name, match.args, match.kwargs)
        except (ObjectDoesNotExist, TypeError, ValueError):
            self.fail('does_not_exist')

    def to_representation(self, value):
        assert 'request' in self.context, (
            "`%s` requires the request in the serializer"
            " context. Add `context={'request': request}` when instantiating "
            "the serializer." % self.__class__.__name__
        )
        value = self.queryset.get(id=value.pk)
        return self.serializer_class(value, context={'request': self.context["request"]}).data

    def get_choices(self, cutoff=None):
        queryset = self.get_queryset()
        if queryset is None:
            # Ensure that field.choices returns something sensible
            # even when accessed with a read-only field.
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict([
            (
                json.dumps(self.to_representation(item)),
                self.display_value(item)
            )
            for item in queryset
        ])
