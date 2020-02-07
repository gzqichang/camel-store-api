from django.conf import settings
from rest_framework import viewsets, decorators, mixins
from rest_framework.views import APIView, status
from rest_framework.response import Response

from quser.permissions import CURDPermissions
from apps.trade.models import UserAddress, Orders, Items
from apps.feedback.models import FeedBack
from wxapp.permissions import OnlyWxUser
from apps.utils.lbs import lbs
from apps.utils.send_email import send_email
from apps.sms.models import SmsSwitch
from apps.sms.send_sms import send_sms
from .models import Shop
from .serializers import ShopSerializer
from .filters import ShopFilter

class ShopViewSet(viewsets.ModelViewSet):
    serializer_class = ShopSerializer
    queryset = Shop.objects.all()
    permission_classes = (CURDPermissions, )
    filterset_class = ShopFilter

    def get_queryset(self):

        user = self.request.user
        if not user:
            return Shop.objects.none()
        if user.has_perm('shop.view_all_shop'):
            return Shop.objects.all().order_by('-status')
        else:
            return user.shop.all().order_by('-status')

    def create(self, request, *args, **kwargs):
        if Shop.objects.count() >= getattr(settings, 'NUMBER_OF_SHOP', 1):
            return Response('店铺数量达到最大设置', status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if 'status' in request.data.keys() and request.data.get('status') == Shop.CLOSE:
            instance = self.get_object()
            if Shop.objects.filter(entrust=instance):
                return Response('该店受其他店铺委托，无法改为休息状态，请先解除委托关系再修改', status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if Shop.objects.filter(entrust=instance):
            return Response('该店与其他店铺有委托关系，请先解除委托关系后再删除', status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)

    @decorators.action(['GET'], detail=False, permission_classes=[OnlyWxUser,])
    def is_range(self, request, *args, **kwargs):
        '''
        根据地区和店铺id，校验是否在配送范围，如果在，返回ID，如果不在，判断是否在其他店的范围，如果有，返回第一店，没有返回None
        {\n
            /api/shop/shop/is_range/?address=广东省广州市天河区&shop=1
        }
        '''
        address = request.query_params.get('address', None)
        shop_id = request.query_params.get('shop', None)
        if not address:
            return Response('缺少地理位置信息', status=status.HTTP_400_BAD_REQUEST)
        coordinate = lbs.get_longitude_and_latitude(address)
        if not isinstance(coordinate, dict):
            return Response('地理位置信息获取失败，请稍后重试', status=status.HTTP_400_BAD_REQUEST)
        if shop_id:
            shop = Shop.objects.get(id=shop_id, status=Shop.OPEN)
            if shop and shop.is_range(coordinate):
                return Response(shop.id)
        for shop in Shop.objects.filter(status=Shop.OPEN):
            if shop.is_range(coordinate):
                return Response(shop.id)
        return Response('null')

    @decorators.action(['GET'], detail=False, permission_classes=[])
    def shop_list(self, request, *args, **kwargs):
        '''
        根据坐标，返回店铺距离及信息的列表
        {\n
            /api/shop/shop/shop_list/?location=23.12553,113.28984
        }
        '''
        location = request.query_params.get('location', None)
        shop_list = []
        if not location:
            for shop in Shop.objects.filter(status=Shop.OPEN):
                shop_list.append({'name': shop.name, 'id': shop.id, 'distance': None, 'address': shop.address})
            return Response(shop_list)
        lat, lng = location.split(',')
        from_location = {'lat': lat, 'lng': lng}
        shop_list = Shop.get_shop_list(from_location)
        # print('shop_list:', type(shop_list), shop_list)
        # if not shop_list:
            # return Response('网络错误，请稍后重试', status=status.HTTP_400_BAD_REQUEST)
        return Response(shop_list)


    @decorators.action(['GET'], detail=False, permission_classes=[])
    def near_shop(self, request, *args, **kwargs):
        '''
        根据店铺id, 地址id，和坐标，返回合适的店铺信息
        {\n
            /api/shop/shop/ner_shop/?shop=&address=&location=23.12553,113.28984
        }
        '''
        user = request.user
        shop_id = request.query_params.get('shop', None)
        address_id = request.query_params.get('address', None)
        location = request.query_params.get('location', None)
        if not Shop.objects.filter(status=Shop.OPEN):
            return Response('非常抱歉目前没有正在营业的店', status=status.HTTP_404_NOT_FOUND)
        if shop_id:
            shop = Shop.objects.get(id=shop_id)
            return Response(self.get_serializer(instance=shop).data)
        if address_id:
            address = UserAddress.objects.get(id=address_id)
            address_location = address.location
            if not isinstance(address_location, dict):
                return Response('获取地理位置信息错误，请重试', status=status.HTTP_400_BAD_REQUEST)
            shop = Shop.get_near_shop(address_location, address.get_region)
            if isinstance(shop, Shop):
                return Response(self.get_serializer(instance=shop).data)
            else:
                return Response('获取最近店铺失败，请稍后重试', status=status.HTTP_404_NOT_FOUND)
        if request.user.is_anonymous:
            user_address = None
        else:
            user_address = request.user.address.all()
        if location:
            lat, lng = location.split(',')
            if not user_address:
                address = lbs.get_location(lat, lng)
                shop = Shop.get_near_shop({'lat': lat, 'lng': lng}, address.get('address'))
                if isinstance(shop, Shop):
                    return Response(self.get_serializer(instance=shop).data)
                else:
                    return Response('获取最近店铺失败，请稍后重试', status=status.HTTP_404_NOT_FOUND)
            address = UserAddress.get_address_by_locations(lat=lat, lng=lng, user=user)
            if not isinstance(address, UserAddress):
                return Response('没有找到合适的店铺', status=status.HTTP_404_NOT_FOUND)
            shop = Shop.get_near_shop_by_address(address)
            if not isinstance(shop, Shop):
                return Response('没有找到合适的店铺', status=status.HTTP_404_NOT_FOUND)
            return Response(self.get_serializer(instance=shop).data)
        else:
            if not user_address:
                return Response(self.get_serializer(instance=Shop.objects.filter(status=Shop.OPEN).first()).data)
            user_address = user_address.filter(is_default=True).first()
            shop = Shop.get_near_shop_by_address(user_address)
            if isinstance(shop, Shop):
                return Response(self.get_serializer(instance=shop).data)
            return Response('获取最近店铺失败，请稍后重试', status=status.HTTP_404_NOT_FOUND)


class DailyRemindAPI(APIView):
    permission_classes = []
    throttle_scope = 'daily_remind'

    def get(self, request, *args, **kwargs):
        for shop in Shop.objects.filter(status=Shop.OPEN):
            feedbackquantities = FeedBack.objects.filter(shop=shop, solve=False).count()
            orderquantities = Items.objects.filter(order__shop=shop, send_type=Items.SENDING).count()
            data = {
                'business': getattr(settings, 'SHOP_NAME'),
                'orderquantities': orderquantities,
                'feedbackquantities': feedbackquantities,
            }
            manage = []
            for admin in shop.admin.all():
                if admin.phone and SmsSwitch.get('daily_remind'):
                    send_sms(admin.phone, data, 'SMS_157276765')
                if admin.email:
                    manage.append(admin.email)
            if manage:
                subject = '每日未处理订单和客户反馈提醒'
                store = getattr(settings, 'SHOP_NAME')
                text_content = html = \
                    f"尊敬的{store}商家你好，您的小店有{orderquantities}个订单" \
                    f"和{feedbackquantities}个客户反馈正在等待处理，" \
                    f"请登录管理后台及时处理。"
                send_email(subject, text_content, html, manage)
        return Response('success')
