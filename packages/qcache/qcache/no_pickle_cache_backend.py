from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.locmem import LocMemCache

class NoPickleLocMemCache(LocMemCache):
    '''对LocMemCache进行改造，不再pickle存储的值。
    因为qcache仅存储Serializer.to_representation()的返回值，该值已经和业务代码无关，长时间存储也不会
    大量增加内存用量。但不可用于其它业务代码。
    '''
    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        # pickled = pickle.dumps(value, self.pickle_protocol)
        with self._lock:
            if self._has_expired(key):
                # self._set(key, pickled, timeout)
                self._set(key, value, timeout)
                return True
            return False

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        with self._lock:
            if self._has_expired(key):
                self._delete(key)
                return default
            # pickled = self._cache[key]
            value = self._cache[key]
            self._cache.move_to_end(key, last=False)
        # return pickle.loads(pickled)
        return value

    def _set(self, key, value, timeout=DEFAULT_TIMEOUT):
        if len(self._cache) >= self._max_entries:
            self._cull()
        self._cache[key] = value
        self._cache.move_to_end(key, last=False)
        self._expire_info[key] = self.get_backend_timeout(timeout)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        # pickled = pickle.dumps(value, self.pickle_protocol)
        with self._lock:
            # self._set(key, pickled, timeout)
            self._set(key, value, timeout)

    def incr(self, key, delta=1, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        with self._lock:
            if self._has_expired(key):
                self._delete(key)
                raise ValueError("Key '%s' not found" % key)
            # pickled = self._cache[key]
            # value = pickle.loads(pickled)
            # new_value = value + delta
            # pickled = pickle.dumps(new_value, self.pickle_protocol)
            # self._cache[key] = pickled
            self._cache[key] += delta
            self._cache.move_to_end(key, last=False)
        return new_value
