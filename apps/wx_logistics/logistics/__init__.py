from .config import (
    BASE_URL,
    URL_SET,
    AccountAction,
    PrinterAction,
    OrderSource,
)

from .decorators import with_access_token

from .logistics import WXLogistics


wx_logistics = WXLogistics(base_url=BASE_URL, url_set=URL_SET)
