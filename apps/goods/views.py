import os
from django.utils import timezone
from django.db.models import Q
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.http import HttpResponse
from rest_framework import viewsets, mixins
from rest_framework.views import APIView, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from quser.permissions import CURDPermissionsOrReadOnly
from wxapp.permissions import OnlyWxUser
from wxapp.https import wxapp_client
from apps.utils.file_uri import file_uri, download_img
from .models import GoodsCategory, Goods, Banner, GoodType, HotWord, Images, OrdGoods, Attach, ReplGoods, ReplGoodsType
from .serializers import  GoodsCategorySerializer, GoodsSerializer, \
    ImagesSerializer, BannerSerializer, HotWordSerializer, CartSerializer, \
    OrdGoodsSerializer, GoodsTypeSerializer, AttachSerializer, SearchSerializer, ReplGoodsSerializer, \
    ReplGoodsTypeSerializer, ValidateReplgoods, GoodsListSerializer, GoodsListNewSerializer, SearchGoodsSerializer

from .permissions import CreateTemplatePermission, UpdatePermission
from .filters import GoodsCategoryFilter, GoodsFilter, BannerFilter
from .utils import validate_can_sell, get_delivery_data_num

# Create your views here.


class GoodsCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = GoodsCategorySerializer
    queryset = GoodsCategory.objects.all()
    permission_classes = [CURDPermissionsOrReadOnly, ]
    filterset_class = GoodsCategoryFilter

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return GoodsCategory.objects.all()
        return GoodsCategory.objects.filter(is_active=True)


class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all().order_by('index')
    serializer_class = BannerSerializer
    permission_classes = [CURDPermissionsOrReadOnly, ]
    filterset_class = BannerFilter

    def get_queryset(self):
        if getattr(self.request.user, 'is_staff', False):
            return Banner.objects.all().order_by('index')
        return Banner.objects.filter(is_active=True)


class HotWordViewSet(viewsets.ModelViewSet):
    queryset = HotWord.objects.all()
    serializer_class = HotWordSerializer
    permission_classes = [CURDPermissionsOrReadOnly, ]


class ImagesViewSet(viewsets.ModelViewSet):
    queryset = Images.objects.all()
    serializer_class = ImagesSerializer
    permission_classes = [CURDPermissionsOrReadOnly, ]


class OrdGoodsViewSet(viewsets.ModelViewSet):
    queryset = OrdGoods.objects.all()
    serializer_class = OrdGoodsSerializer
    permission_classes = [CURDPermissionsOrReadOnly, ]


class ReplGoodsViewSet(viewsets.ModelViewSet):
    queryset = ReplGoods.objects.all()
    serializer_class = ReplGoodsSerializer
    permission_classes = [CURDPermissionsOrReadOnly, ]


class GoodsTypeViewSet(viewsets.ModelViewSet):
    queryset = GoodType.objects.all()
    serializer_class = GoodsTypeSerializer
    permission_classes = [CURDPermissionsOrReadOnly, ]


class ReplGoodsTypeViewSet(viewsets.ModelViewSet):
    queryset = ReplGoodsType.objects.all()
    serializer_class = ReplGoodsTypeSerializer
    permission_classes = [CURDPermissionsOrReadOnly, ]


class AttachViewSet(viewsets.ModelViewSet):
    queryset = Attach.objects.all()
    serializer_class = AttachSerializer
    permission_classes = [CURDPermissionsOrReadOnly, ]


class GoodsViewSet(viewsets.ModelViewSet):
    queryset = Goods.objects.all()
    serializer_class = GoodsListNewSerializer
    permission_classes = [CURDPermissionsOrReadOnly, CreateTemplatePermission]
    filterset_class = GoodsFilter

    def get_queryset(self):
        related = ["banner", "detail", "ord_goods", "category"]
        queryset = self.queryset.prefetch_related(*related)
        if self.action == 'retrieve':
            # 查看详情时
            return queryset
        if getattr(self.request.user, 'is_staff', False):
            if self.request.query_params.get('is_template', 'false') == 'true':  # 查看模板
                queryset = queryset.filter(is_template=True)
            else:
                queryset = queryset.exclude(is_template=True)
        elif getattr(self.request.user, 'testers', False):
            queryset = queryset.exclude(
                is_template=True
            ).exclude(
                category__is_active=False
            ).filter(
                status__in=[Goods.IS_SELL, Goods.PREVIEW]
            )
        else:
            queryset = queryset.exclude(
                is_template=True
            ).exclude(
                category__is_active=False
            ).filter(
                status=Goods.IS_SELL
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list' and not getattr(self.request.user, 'is_staff', False):
            return GoodsListSerializer
        return GoodsSerializer

    @action(['GET', ], detail=True, permission_classes=[OnlyWxUser, ])
    def poster(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        if not instance.poster:
            return Response('该商品没有分享图', status=status.HTTP_400_BAD_REQUEST)
        data = None
        price_range = getattr(instance.ord_goods, 'price_range', "")
        back_img_path = os.path.join(settings.MEDIA_ROOT, instance.poster.file.name)
        if not os.path.exists(back_img_path):
            image_url = file_uri(request, instance.poster.file.name)
            download_img(image_url, back_img_path)
        back_img = Image.open(os.path.join(settings.MEDIA_ROOT, instance.poster.file.name)).convert('RGB')
        back_img = back_img.resize((470, int(back_img.size[1] * (470 / back_img.size[0]))))  # 将图片尺寸等比例缩放为宽度为470的
        scene = "subgoodId:" + str(instance.id) + ";shareUserId:" + str(user.id) + ";"
        code = wxapp_client.get_wxa_code(scene=scene, page=r'pages/util/index')
        qrcode = Image.open(os.path.join(settings.MEDIA_ROOT, code)).convert('RGB')
        try:
            qrcode = qrcode.resize((110, 110))
            back_img.paste(qrcode, (330, 30))
            draw = ImageDraw.Draw(back_img)
            font = ImageFont.truetype(os.path.join(settings.STATIC_ROOT, 'font/poster_font.ttf'), size=24)
            goods_font = ImageFont.truetype(os.path.join(settings.STATIC_ROOT, 'font/dengl.ttf'), size=22)
            draw.text((48, 30), getattr(settings, 'SHOP_NAME'), fill='black', font=font)
            name = instance.name if len(instance.name) < 11 else instance.name[:10] + '...'
            draw.text((48, 70), name, fill='black', font=goods_font)
            draw.text((48, 106), '¥' + price_range, fill='red', font=goods_font)
            path = os.path.join(settings.POSTER_ROOT, f'{instance.id}_{user.id}.png')
            back_img.save(path)
            with open(path, 'rb') as f:
                data = f.read()
        finally:
            back_img.close()
            qrcode.close()
        response = HttpResponse(data, content_type='image/png')
        response['Content-Disposition'] = 'inline;'
        return response

    @action(['POST', ], detail=False, permission_classes=[], serializer_class=CartSerializer)
    def validate_cart(self, request, *args, **kwargs):
        """
        post:
        {\n
            "items_list":[
                {
                    "goodsid": 1,
                    "gtypeid": 1
                },
                {
                    "goodsid": 2,
                    "gtypeid": 2
                }
            ],
            "is_pt": true,
            "address": "广东省广州市天河区建工路12号"
        }
        """
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        res = serializer.save()
        return Response(res)

    @action(['POST', ], detail=False, permission_classes=[OnlyWxUser, ], serializer_class=ValidateReplgoods)
    def validate_replgoods(self, request, *args, **kwargs):
        """
        post:
        {\n
            "replgoodsid": 1,
            "gtypeid": 1,
        }
        """
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        res = serializer.save()
        return Response(res)


class Search(APIView):
    permission_classes = []
    serializer_class = SearchSerializer

    def get(self, request, *args, **kwargs):
        data = request.query_params
        serializer = self.serializer_class(data=request.query_params, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        res = serializer.save()
        return Response(res)


class SearchGoods(APIView):
    permission_classes = [IsAdminUser, ]
    serializer_class = SearchGoodsSerializer

    def get(self, request, *args, **kwargs):
        keyword = request.query_params.get('k', None)
        goods = Goods.objects.exclude(Q(is_template=True))
        if keyword:
            goods = goods.filter(name__icontains=keyword)
        serializer = self.serializer_class(goods, many=True, context=dict(request=request))
        return Response(serializer.data)