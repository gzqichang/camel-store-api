from rest_framework.pagination import PageNumberPagination


class PageSizePagination(PageNumberPagination):
    """ 可以控制每一个数量大小的分页 """
    page_size_query_param = 'page_size'
