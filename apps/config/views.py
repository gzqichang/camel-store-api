import os
from io import BytesIO
import base64
import requests
from django.conf import settings
from rest_framework.reverse import reverse
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView, status
from rest_framework.response import Response
from wechatpy.client import WeChatClient
import qrcode
from quser.permissions import CURDPermissionsOrReadOnly
from wxapp.permissions import ReadOnly
from apps.qfile.serializers import FileSerializer
from .models import FaqContent, Marketing, Notice, Level, RechargeType, BoolConfig, Version, StoreLogo, \
     StoreType, DatetimeConfig
from .models import StoreName as StoreNameModel
from .serializers import FaqContentSerializers, MarketingSerializers, NoticeSerializers, LevelSerializers, \
    RechargeTypeSerializers, StoreLogoSerializers, StorePosterSerializers, WeChatConfigSerializers
from .filters import NoticeFilter


class FaqContentViewSet(viewsets.ModelViewSet):
    serializer_class = FaqContentSerializers
    queryset = FaqContent.objects.all()
    permission_classes = (CURDPermissionsOrReadOnly,)

class StoreName(APIView):
    # permission_classes = [WithCloudTokenOrReadOnly]
    permission_classes = [ReadOnly]

    def get(self, request, *args, **kwargs):
        store_name = StoreNameModel.get_name()
        return Response(store_name)

    def post(self, request, *args, **kwargs):
        name = request.data.get('store_name', '')
        store_name = StoreNameModel.set_name(name=name)
        return Response(store_name)

class StoreLogoAPI(APIView):
    serializer_class = StoreLogoSerializers
    permission_classes = [IsAdminUser | ReadOnly]

    def get(self, request, *args, **kwargs):
        # res = {}
        res = {'storename': StoreNameModel.get_name()}
        square_logo = StoreLogo.get('square_logo')
        if square_logo:
            res.update({'square_logo': FileSerializer(square_logo.image, context=dict(request=request)).data})

        else:
            store_type = BoolConfig.objects.filter(name="store_type").first()
            store_type_value = getattr(store_type, "content", "camel")
            file_name = "camel-store-logo.png"

            file = request.build_absolute_uri(os.path.join(settings.STATIC_URL, 'img/{}'.format(file_name)))
            res.update({'square_logo': {'file': file}})
        rectangle_logo = StoreLogo.get('rectangle_logo')
        if rectangle_logo:
            res.update({'rectangle_logo': FileSerializer(rectangle_logo.image, context=dict(request=request)).data})
        else:
            res.update({'rectangle_logo': {}})
        return Response(res)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


class StoreInfoAPI(APIView):
    """ 小程序端获取小店名，logo等信息 """
    permission_classes = []

    def get(self, request, *args, **kwargs):
        res = {}
        square_logo = StoreLogo.get('square_logo')
        if square_logo:
            res.update(
                {'square_logo': FileSerializer(square_logo.image, context=dict(request=request)).data.get('file')})
        else:
            store_type = BoolConfig.objects.filter(name="store_type").first()
            store_type_value = getattr(store_type, "content", "camel")
            file_name = "camel-store-logo.png"

            file = request.build_absolute_uri(os.path.join(settings.STATIC_URL, 'img/{}'.format(file_name)))
            res.update({'square_logo': {'file': file}})
        rectangle_logo = StoreLogo.get('rectangle_logo')
        if rectangle_logo:
            res.update({'rectangle_logo': FileSerializer(rectangle_logo.image, context=dict(request=request)).data.get(
                'file')})
        else:
            res.update({'rectangle_logo': {}})
        return Response(res)


class StorePosterAPI(APIView):
    serializer_class = StorePosterSerializers
    permission_classes = [IsAdminUser, ]

    def get(self, request, *args, **kwargs):
        res = {}
        store_poster = StoreLogo.get('store_poster')
        if store_poster:
            res.update({'store_poster': FileSerializer(store_poster.image, context=dict(request=request)).data})
        else:
            res.update({'store_poster': None})
        return Response(res)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


class Config(APIView):
    """
    - share_switch: 显示分享设置
    - rebate_switch: 推广返利设置
    - bonus_switch: 分销返利设置
    - cart_switch: 购物车启用设置
    """
    permission_classes = []

    def get(self, request, *args, **kwargs):

        res = {
            'share_switch': BoolConfig.get_bool('share_switch'),
            'rebate_switch': BoolConfig.get_bool('rebate_switch'),
            'bonus_switch': BoolConfig.get_bool('bonus_switch'),
            'cart_switch': BoolConfig.get_bool('cart_switch'),
            'wallet_switch': BoolConfig.get_bool('wallet_switch'),
            'tradition_home': BoolConfig.get_bool('tradition_home'),
            'version': Version.get_value('version'),
            'show_copyright': BoolConfig.get_bool('show_copyright'),
            'store_type': StoreType.get_value('store_type'),
            'attach_switch': DatetimeConfig.is_valid('attach_switch'),
            'qr_pay_switch': DatetimeConfig.is_valid('qr_pay_switch'),
            'subscription_switch': DatetimeConfig.is_valid('subscription_switch'),
            'video_switch': BoolConfig.get_bool('video_switch'),
            'invoice_switch': BoolConfig.get_bool('invoice_switch'),
        }
        store_poster = StoreLogo.get('store_poster')
        if store_poster:
            res.update(
                {'store_poster': FileSerializer(store_poster.image, context=dict(request=request)).data.get('file')})
        else:
            res.update({'store_poster': ''})
        return Response(res)


class MarketingView(APIView):
    serializer_class = MarketingSerializers
    permission_classes = (IsAdminUser,)

    def get(self, request, *args, **kwargs):
        res = {
            'rebate': Marketing.get_value('rebate'),
            'bonus': Marketing.get_value('bonus'),
        }
        return Response(res)

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


class NoticeViewSet(viewsets.ModelViewSet):
    serializer_class = NoticeSerializers
    queryset = Notice.objects.all()
    permission_classes = (CURDPermissionsOrReadOnly,)
    filterset_class = NoticeFilter


class LevelViewSet(viewsets.ModelViewSet):
    serializer_class = LevelSerializers
    queryset = Level.objects.all()
    permission_classes = (CURDPermissionsOrReadOnly,)


class RechargeTypeViewSet(viewsets.ModelViewSet):
    serializer_class = RechargeTypeSerializers
    queryset = RechargeType.objects.all()
    permission_classes = (CURDPermissionsOrReadOnly,)

    def create(self, request, *args, **kwargs):
        if RechargeType.objects.count() >= 6:
            return Response('优惠充值档位数量已超过限制，请在已创建的档位中进行编辑或删除。', status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)


class WechatConfigView(APIView):
    permission_classes = [IsAdminUser]
    serializer_class = WeChatConfigSerializers

    def get(self, request):
        try:
            settings.SETTINGS_CONFIG.read(settings.CONFIG_FILE_PATH)
            settings_config_default = settings.SETTINGS_CONFIG["DEFAULT"]
        except (Exception,):
            settings_config_default = {}

        return Response({
            'wx_lite_app': getattr(settings, 'WX_PAY_WXA_APP_ID', ''),
            'wx_lite_secret': settings_config_default.get("wx_lite_secret"),
            'wx_pay_api_key': settings_config_default.get("wx_pay_api_key"),
            'wx_pay_mch_id': settings_config_default.get("wx_pay_mch_id"),
            'wx_pay_mch_cert': os.path.exists(os.path.join(settings.BASE_DIR, 'conf/cert_file/apiclient_cert.pem')),
            'wx_pay_mch_key': os.path.exists(os.path.join(settings.BASE_DIR, 'conf/cert_file/apiclient_key.pem'))
        })

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context=dict(request=request))
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        self.touch_reload()
        return Response(data)

    def touch_reload(self):
        f = open(os.path.join(settings.BASE_DIR, 'reload'), 'w')
        f.close()


class WxAppQrCodeView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        qichang_cloud_api = "http://s.qichang.online/"

        scene = request.query_params.get("scent", "from")
        page = request.query_params.get("scent", 'pages/util/index')
        wx_config = getattr(settings, 'WX_CONFIG', {})
        app_id, app_secret = wx_config.get('WXAPP_APPID'), wx_config.get('WXAPP_APPSECRET')

        public_code = self.get_public_code(app_id, app_secret, scene, page, qichang_cloud_api)
        preview_code = self.get_preview_code(app_id)

        return Response({
            'public_code': self.generate_base64_img(public_code),
            'preview_code': self.generate_base64_img(preview_code),
        })

    def get_public_code(self, app_id, app_secret, scene, page, qichang_cloud_api):
        if app_id and app_secret:
            client = WeChatClient(app_id, app_secret)

            try:
                resp = client.wxa.get_wxa_code_unlimited(scene=scene, page=page)
            except (Exception,):
                public_code = None
            else:
                content_type = resp.headers.get("Content-Type", "")
                if "image" not in content_type:
                    public_code = None
                else:
                    public_code = resp.content
        else:
            store_type = BoolConfig.objects.filter(name="store_type").first()
            if store_type and store_type.content == "cloud":
                public_code = self.get_public_code_from_cloud(app_id, scene, page, qichang_cloud_api)
            else:
                public_code = None

        return public_code

    def get_preview_code(self, app_id):
        output = BytesIO()

        url = f"https://open.weixin.qq.com/sns/getexpappinfo?appid={app_id}&iswxtpa=1#wechat-redirect"
        img = qrcode.make(url, border=2)
        img.save(output, format='png')

        data = output.getvalue()
        return data

    def get_public_code_from_cloud(self, app_id, scene, page, qichang_cloud_api):
        api = "api/wxa-qr-code/"
        url = f"{qichang_cloud_api}/{api}"

        try:
            resp = requests.post(url, data={"app_id": app_id, "scene": scene, "page": page})
        except (Exception,):
            public_code = None
        else:
            if resp.status_code == 200:
                resp_json = resp.json()
                public_code = resp_json.get("image_content", None)
            else:
                public_code = None

        return public_code

    def generate_base64_img(self, img_content):
        if img_content is not None:
            img_content = base64.b64encode(img_content)
        return img_content

