# qapi

## 安装

先用 `git clone` 下载源代码，然后执行 `python setup.py develop` 安装。

## 配置

在 django project 的 `settings.py` 文件的 `INSTALLED_APPS` 中加入 `qapi` 即可。

## 使用

在 `settings` 中定义配置 `REST_FRAMEWORK`，如：

```
REST_FRAMEWORK = {
    ...
    'EXCEPTION_HANDLER': 'qapi.handler.exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'qapi.pagination.PageSizePagination',
    ...
}
```

### 方法重写

在 `settings` 的 `MIDDLEWARE` 中添加 `qpi.middleware.MethodOverrideMiddleware`, 放在 `django.middleware.csrf.CsrfViewMiddleware` 之后

```
    MIDDLEWARE = [
        ...
        'django.middleware.csrf.CsrfViewMiddleware',
        'qpi.middleware.MethodOverrideMiddleware',
        ...
    ]
```

# qapi.mixins

```
from qapi.mixins import RelationMethod

class PlayerViewSet(ModelViewSet, RelationMethod):
    ...

    @detail_route(['GET'],
                  serializer_class=MonthStepRecordSerializer)
    def month_step_records(self, request, *args, **kwargs):
        return self.detail_route_view(request, 'month_step_records',
                                      MonthStepRecordSerializer)

```

# qapi.utils
```
常用: generate_fields, generate_full_uri, 等，可以翻代码，懒得写文档
```