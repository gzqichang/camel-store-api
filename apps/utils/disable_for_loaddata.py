"""
避免使用Django迁移数据过程中触发信号机制的装饰器
"""

from functools import wraps

def disable_for_loaddata(signal_handler):
    """
    Decorator that turns off signal handlers when loading fixture data.
    """

    @wraps(signal_handler)
    def wrapper(*args, **kwargs):
        print(kwargs.get('raw'))
        if kwargs.get('raw'):
            return
        signal_handler(*args, **kwargs)
    return wrapper