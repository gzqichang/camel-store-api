from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.include_root_view = False
router.register('category', views.GoodsCategoryViewSet)
router.register('banner', views.BannerViewSet)
router.register('hotword', views.HotWordViewSet)
router.register('goods', views.GoodsViewSet, basename='goods')
router.register('image', views.ImagesViewSet)
router.register('attach', views.AttachViewSet)
router.register('ordgoods', views.OrdGoodsViewSet)
router.register('ordtype', views.GoodsTypeViewSet)
router.register('replgoods', views.ReplGoodsViewSet)
router.register('repltype', views.ReplGoodsTypeViewSet)


urlpatterns = [
    path('search_goods/', views.SearchGoods.as_view(), name='search-goods'),
    path('search/', views.Search.as_view(), name='search'),
    path('', include(router.urls)),
]