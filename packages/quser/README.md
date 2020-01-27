# quser 文档



## 安装

先用 `git clone` 下载源代码，然后执行 `python setup.py develop` 安装。



## 配置

在 django project 的 `settings.py` 文件的 `INSTALLED_APPS` 中加入 `quser` 即可。



## 说明

- 每个 models 都拥有 默认的权限 view_%(model_name)s 表示允许查看
- 设置了自定义权限 `can_reset_password` 可用于重置用户的密码
-  限制删除超级管理员权限组
- 限制修改超级管理员权限




##  settings 相关配置说明

```
# 管理员默认密码设置 默认为123456
DEFAULT_ADMIN_PASSWORD = '123456'

# 重写 Django get_user_model() 的 verbose_name 和 verbose_name_plural
USER_MODEL_VERBOSE_NAME = '管理员'
USER_MODEL_VERBOSE_NAME_PLURAL = '管理员'

# 重写 Django auth.models.Group 的 verbose_name 和 verbose_name_plural
GROUP_MODEL_VERBOSE_NAME = '角色'
GROUP_MODEL_VERBOSE_NAME_PLURAL = '角色'

# 限定一个用户只能有一个角色
USER_JUST_ONE_GROUP = True

# 接口开放可编辑的权限
# 规则：'app_label.model_name:action1|action2',
EDITABLE_PERMISSIONS = (
    'channel.Channel:view|add|change|delete',
    'article.Article:view|add|change|delete',
    'team.Team:view|add|change|delete',
    'tools.Tool:view|add|change|delete',
    'index.Banner:view|add|change|delete',
    'auth.User:view|add|change|delete|can_reset_password',
    'auth.Group:view|add|change|delete',
)

# 添加自定义的 actions 和对应的显示
# 默认的 actions 有 (view|add|change|delete)
# ⚠️注意: codename 为 %(action)s_%(model_name)s
PERMISSION_ACTIONS = {
    'reset': '重置',
    ...
}

# 给 admin 用户添加自定义权限
USER_CUSTOM_PERMISSIONS = [
    ('can_reset_password', _('Can Reset User Password')),
    ('code_name', 'human_readable_permission_name')
    ...
]


# 是否开启验证码
IS_CAPTCHA_ENABLE = True

```
## Url

- 提供了验证码接口

  `captcha-generate/`

- 提供了用户登录接口

  `login/`

- 提供密码修改和密码重置接口

  `user-reset_password/`

  `change-password/`

- 提供了用户列表接口

  `users/`

- 提供了角色类别接口

  `groups/`
```
urlpatterns = [
    ...
    path('quser/', include('quser.urls')),
    ...
]
```



## Permissions

- `quser.permissions.CURDPermissions` 根据用户权限返回 CURD 的权限
- `quser.permissions.has_perms(*codenames)` 根据 codenames 返回权限
- `quser.permissions.enable_methods(*methods)` 根据 methods 允许列表返回权限
- `quser.permissions.disable_methods(*methods)` 根据 methods 禁止列表返回权限


## Commands

```
# 用户系统初始化, 默认创建admin用户, 默认密码： 123123, 并且创建一个超级管理员权限组, 
# 注意自定义 User 需要继承 AbstractUser
python manage.py init_staff  
```