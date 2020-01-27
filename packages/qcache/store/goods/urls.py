from django.urls import include, path

from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'tags', views.TagViewSet)
router.register(r'people', views.PeopleViewSet)
router.register(r'goods', views.GoodsViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
]