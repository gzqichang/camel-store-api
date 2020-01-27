from rest_framework import viewsets, mixins


class NoDeleteViewSet(viewsets.GenericViewSet,
                      mixins.ListModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.CreateModelMixin,
                      mixins.UpdateModelMixin):
    """
        什么都可以做, 就是不能删除
    """
    pass
