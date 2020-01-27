from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.generics import get_object_or_404


def filter_queryset_by_user(request, queryset, **kwargs):
    if not request.user.is_staff:
        return queryset.filter(**kwargs)
    return queryset


class RelationMethod(object):
    def get_object_without_filter(self):

        queryset = self.get_queryset()

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def detail_route_view(self, request, related_name, serializer_class,
                          filter_class=None, filter_kwargs=None, filter_func=None):
        instance = self.get_object_without_filter()
        filter_kwargs = filter_kwargs or {}
        if request.method == 'GET':
            queryset = getattr(instance, related_name).all()

            if filter_class:
                queryset = filter_class(request.query_params, queryset=queryset, request=request).qs

            if filter_kwargs:
                queryset = filter_queryset_by_user(request, queryset, **filter_kwargs)

            if filter_func and callable(filter_func):
                queryset = filter_func(request, queryset)

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = serializer_class(page, many=True, context=self.get_serializer_context())
                return self.get_paginated_response(serializer.data)
            serializer = serializer_class(queryset, many=True, context=self.get_serializer_context())

        elif request.method == 'POST':
            serializer = serializer_class(data=request.data, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            serializer.save()

        else:
            raise MethodNotAllowed(request.method)

        return Response(serializer.data)
