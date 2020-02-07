import hashlib
import requests
from haversine import haversine
from requests.exceptions import SSLError, ConnectTimeout, ConnectionError

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile


class TencentLBS(object):
    key = settings.TENCENT_LBS_KEY
    geo_coder_url = 'https://apis.map.qq.com/ws/geocoder/v1/'
    static_map_url = 'https://apis.map.qq.com/ws/staticmap/v2/'

    def __init__(self, latitude=None, longitude=None, address=None, icon=None):
        self.latitude = latitude
        self.longitude = longitude
        self.address = address
        self.icon = icon

    def get_location(self, origin=False):
        params = {
            'key': self.key,
            'location': '{},{}'.format(self.latitude, self.longitude)
        }

        try:
            response = requests.get(self.geo_coder_url, params=params)
            if origin:
                return response.json()
            else:
                return self.parse_location(response)
        except (SSLError, ConnectTimeout, ConnectionError):
            return {
                "province": "上海",
                "city": "上海",
                "message": "获取区域发生错误"
            }

    def get_longitude_and_latitude(self):
        params = {
            'key': self.key,
            'address': '{}'.format(self.address)
        }

        try:
            response = requests.get(self.geo_coder_url, params=params)
            return self.parse_longitude_and_latitude(response)
        except (SSLError, ConnectTimeout, ConnectionError):
            return "获取坐标位置错误"

    def get_static_map_img(self, size="339*90", zoom=12, icon=None):
        params = {
            'key': self.key,
            'center': '{},{}'.format(self.latitude, self.longitude),
            'zoom': zoom,
            'size': size,
            'scale': 2  # 高清
        }

        off_number = 0.0055
        latitude = self.off_degree(self.latitude, off_number)
        if icon:
            params['markers'] = "icon:{}|{},{}".format(icon, latitude, self.longitude)
        else:
            params['markers'] = "color:blue|{},{}".format(latitude, self.longitude)

        try:
            response = requests.get(self.static_map_url, params=params)
        except (SSLError, ConnectTimeout, ConnectionError):
            return "保存静态坐标图失败"

        img_file = self.write_image(response.content)
        return img_file

    def write_image(self, img_content):
        file_name = "{}_{}.png".format(self.latitude, self.longitude)
        img_file = ContentFile(content=img_content, name=file_name)
        return img_file

    @staticmethod
    def parse_location(response):
        if response.status_code == 200:
            response_data = response.json()
            status = response_data.get('status')
            result = response_data.get('result')
            if status == 0 and result:
                address_component = result.get('address_component', {})
                if address_component.get("city", ""):
                    province = address_component.get('province', '')
                    city = address_component.get('city', '').replace("市", "")
                    return {
                        "province": province,
                        "city": city,
                        "message": "success"
                    }

        return {
            "province": "上海",
            "city": "上海",
            "message": "获取区域发生错误"
        }

    @staticmethod
    def parse_longitude_and_latitude(response):
        if response.status_code == 200:
            response_data = response.json()
            status = response_data.get('status')
            result = response_data.get('result')
            if status == 0 and result:
                location = result.get('location', {})

                if all(location.values()):
                    longitude = location.get('lng')
                    latitude = location.get('lat')
                    return {
                        "latitude": latitude,
                        "longitude": longitude
                    }

            return "获取坐标位置错误({})".format(response_data.get("message"))

        return "获取坐标位置错误({})".format(response.status_code)

    @staticmethod
    def off_degree(degree, number):
        return degree if degree < number else float("{0:.6f}".format(degree - number))

    def get_address(self):
        key = "address-{}".format(self.address)
        data = cache.get(key)

        if not data:
            data = self.get_longitude_and_latitude()
            if not isinstance(data, str):
                cache.set(key, data, 60 * 60 * 12)

        return data


class TencentLBS2(object):

    def __init__(self):
        self.key = settings.TENCENT_LBS_KEY
        self.sk = settings.TENCENT_LBS_SK

    def gen_sig(self, params):
        alist = []
        for k in sorted(params.keys()):
            alist.append('='.join((k, params[k])))
        params_str = '/ws/geocoder/v1/?' + '&'.join(alist) + self.sk
        result = hashlib.md5(params_str.encode()).hexdigest()
        return result

    def get_location(self, lat, lng):
        url = 'https://apis.map.qq.com/ws/geocoder/v1/'
        params = {
            'key': self.key,
            'location': '{},{}'.format(lat, lng)
        }
        params['sig'] = self.gen_sig(params)
        
        try:
            response = requests.get(url, params=params)
            return self.parse_location(response)
        except (SSLError, ConnectTimeout, ConnectionError):
            return "message: 获取区域发生错误"

    def one_to_one_distance(self, from_location, to_location):
        '''
            因为腾讯地图的距离计算api有直径10公里限制， 所以暂时使用经纬度计算距离
        :param from_location: {'lat': lat, 'lng': lng}
        :param to_location: {'lat': lat, 'lng': lng}
        :return: distance(单位：km)
        '''
        from_location = (from_location.get('lat'), from_location.get('lng'))
        to_location = (to_location.get('lat'), to_location.get('lng'))
        distance = haversine(from_location, to_location)
        return round(distance, 2)

    def get_longitude_and_latitude(self, address):
        url = 'https://apis.map.qq.com/ws/geocoder/v1/'
        params = {
            'key': self.key,
            'address': address,
        }
        params['sig'] = self.gen_sig(params)

        try:
            response = requests.get(url, params=params)
            return self.parse_longitude_and_latitude(response)
        except (SSLError, ConnectTimeout, ConnectionError):
            return "获取坐标位置错误"

    # def one_to_many_distance(self, from_location, to_location):
    #     # 一对多距离计算
    #     '''
    #
    #     :param from_location:  'lat,lng'
    #     :param to_location: ['lat,lng', 'lat,lng',...]
    #     :return:
    #     '''
    #     distance_url = 'https://apis.map.qq.com/ws/distance/v1/'
    #     data = {
    #         'from': from_location,
    #         'to': ';'.join(to_location),
    #         'key': self.key,
    #     }
    #     try:
    #         response = requests.get(distance_url, params=data)
    #         return self.parse_distance(response.json())
    #     except (SSLError, ConnectTimeout, ConnectionError):
    #         return "获取距离信息发生错误"

    def one_to_many_distance(self, from_location, to_location):
        # 一对多距离计算
        '''
         因为腾讯地图的距离计算api有直径10公里限制， 所以暂时使用经纬度计算距离
        :param from_location:  'lat,lng'
        :param to_location: ['lat,lng', 'lat,lng',...]
        :return:
        '''
        distance_list = []
        from_location = tuple(float(i) for i in from_location.split(','))
        for index, to in enumerate(to_location):
            to_ = tuple(float(i) for i in to.split(','))
            distance = haversine(from_location, to_)
            distance_list.append({'index': index, 'distance': round(distance, 2)})
        distance_list = sorted(distance_list, key=lambda x: x.get('distance'))
        return distance_list

    @staticmethod
    def parse_distance(response):
        if response.get('status') == 0:
            result = response.get('result')
            elements = result.get('elements')
            distance_list = []
            for index, element in enumerate(elements):
                if element.get('distance') >= 0:
                    distance_list.append({'index': index, 'distance': element.get('distance')})
            distance_list = sorted(distance_list, key=lambda x: x.get('distance'))
            return distance_list
        print(response)
        return f"获取距离信息发生错误:{response.get('message')}"

    @staticmethod
    def parse_location(response):
        if response.status_code == 200:
            response_data = response.json()
            status = response_data.get('status')
            result = response_data.get('result')
            if status == 0 and result:
                address_component = result.get('address_component', {})
                if address_component.get("city", ""):
                    province = address_component.get('province', '')
                    city = address_component.get('city', '')
                    district = address_component.get('district', '')
                    return {
                        "province": province,
                        "city": city,
                        "district": district,
                        "message": "success",
                        "address": province+city+district
                    }
        return "message: 获取区域发生错误"

    @staticmethod
    def parse_longitude_and_latitude(response):
        if response.status_code == 200:
            response_data = response.json()
            status = response_data.get('status')
            result = response_data.get('result')
            if status == 0 and result:
                location = result.get('location', {})
                if all(location.values()):
                    longitude = location.get('lng')
                    latitude = location.get('lat')
                    return {
                        "lat": latitude,
                        "lng": longitude
                    }
            return "获取坐标位置错误({})".format(response_data.get("message"))
        return "获取坐标位置错误({})".format(response.status_code)


lbs = TencentLBS2()