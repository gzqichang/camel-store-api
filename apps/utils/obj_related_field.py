# coding: utf-8
from __future__ import unicode_literals

from collections import OrderedDict
import simplejson as json

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.urls import Resolver404, get_script_prefix, resolve
from django.utils.encoding import uri_to_iri
from urllib.parse import urlparse
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers


class ObjectHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    serializer_class = None

    default_error_messages = {
        'required': _('This field is required.'),
        'no_match': _('Invalid hyperlink - No URL match.'),
        'incorrect_match': _('Invalid hyperlink - Incorrect URL match.'),
        'does_not_exist': _('Invalid hyperlink - Object does not exist.'),
        'incorrect_type': _('Incorrect type. Expected URL string, received {data_type}.'),
        'match_multi': _('Multiple returned - Object match too much'),
    }

    def __init__(self, serializer_class=None, is_save=False, **kwargs):
        if serializer_class is not None:
            self.serializer_class = serializer_class
        assert self.serializer_class is not None, 'The `serializer_class` argument is required.'

        self.is_save = is_save

        super().__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            data = json.loads(data)
        except (TypeError, json.JSONDecodeError):
            pass

        if self.lookup_field == "pk" and "url" in data:
            return self.to_internal_value_by_url(data)
        else:
            try:
                return self.queryset.get(
                    **{self.lookup_field: data.get(self.lookup_field)}
                )
            except (ObjectDoesNotExist, AttributeError):
                if self.is_save:
                    serializer = self.serializer_class(data=data, context={'request': self.context["request"]})
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    return serializer.instance
                else:
                    self.fail('does_not_exist')
            except MultipleObjectsReturned:
                self.fail('match_multi')
            except (TypeError, ValueError):
                self.fail('does_not_exist')

    def to_internal_value_by_url(self, origin_data):
        request = self.context.get('request', None)
        try:
            data = origin_data.get("url")
            http_prefix = data.startswith(('http:', 'https:'))
        except AttributeError:
            self.fail('incorrect_type', data_type=type(origin_data).__name__)

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
            obj = self.get_object(match.view_name, match.args, match.kwargs)
            if self.is_save:
                serializer = self.serializer_class(obj, data=origin_data, context={'request': self.context["request"]})
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return serializer.instance
            else:
                return obj
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
