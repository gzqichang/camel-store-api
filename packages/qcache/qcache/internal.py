from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import caches
# version_timestamp 字段用的是这个 now，要保持一致
from django.utils.timezone import now

try:
    cache = caches['qcache']
except LookupError:
    cache = caches['default']

def update_cache(key, timestamp, serialized_data):
    # Passing in None for timeout will cache the value forever.
    cache.set(key, (timestamp, serialized_data), timeout=None)
    return serialized_data

def version_based_cache(serializer_class):
    from .models import VersionedMixin, is_expired
    orig_to_representation = serializer_class.to_representation

    def _to_representation(serializer_instance, model_instance):
        request = serializer_instance.context['request']
        try:
            admin_no_cache = request.META.get('HTTP_QCACHE_CACHE_CONTROL', None) == 'admin-no-cache'
        except AttributeError:
            admin_no_cache = False
        if admin_no_cache and request.user.is_staff:
            return orig_to_representation(serializer_instance, model_instance)

        key = str(hash((type(serializer_instance), type(model_instance), model_instance)))
        curr_timestamp = now()

        cch = cache.get(key, None)
        # print(serializer_class, model_instance, 'cch: ', cch)
        if not cch:
            return update_cache(key, curr_timestamp, orig_to_representation(serializer_instance, model_instance))
        cache_timestamp, serialized_data = cch

        request = serializer_instance.context['request']
        interval_seconds = getattr(settings, 'QCACHE_UPDATE_INTERVAL_SECONDS', 60)
        # time is up.
        if cache_timestamp + timedelta(seconds=interval_seconds) < curr_timestamp:
            checked_model_instances = getattr(request, 'qcache_checked_model_instances', None)
            if checked_model_instances is None:
                checked_model_instances = set()
                setattr(request, 'qcache_checked_model_instances', checked_model_instances)

            if is_expired(model_instance, cache_timestamp, checked_model_instances):
                return update_cache(key, curr_timestamp, orig_to_representation(serializer_instance, model_instance))

            # 数据库没有变化，只更新时间戳
            return update_cache(key, curr_timestamp, serialized_data)

        return serialized_data

    serializer_class.to_representation = _to_representation
    return serializer_class
