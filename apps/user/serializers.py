from django.conf import settings
from django.contrib.auth.models import Group, Permission
from rest_framework import serializers
from rest_framework.reverse import reverse
from django.contrib.auth import authenticate
from .models import User
from qapi.utils import generate_fields
from quser.serializers import UserLoginSerializer
from captcha.models import CaptchaStore


class LoginSerializer(UserLoginSerializer):

    def validate(self, attrs):
        if getattr(settings, 'IS_CAPTCHA_ENABLE', True):
            key = attrs.get('key')
            challenge = attrs.get('challenge')
            if not key or not challenge:
                raise serializers.ValidationError("验证码参数 `key` 和 `challenge` 必须传递过来")
            try:
                captcha = CaptchaStore.objects.get(challenge=challenge.upper(), hashkey=key)
                captcha.delete()
            except CaptchaStore.DoesNotExist:
                raise serializers.ValidationError("请输入正确的验证码")
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)

            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
            if not user:
                msg = "用户名或密码错误"
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = "请输入用户名和密码"
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.HyperlinkedModelSerializer):
    groups_name = serializers.SerializerMethodField()
    reset_password_url = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    shop_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = generate_fields(User, add=['permissions', 'groups_name', 'shop_name', 'reset_password_url'],
                                 remove=['is_superuser', 'is_staff', 'user_permissions', 'last_login', 'date_joined',
                                         'first_name', 'last_name'])
        extra_kwargs = {
            'password': {
                'write_only': True,
                'style': {'input_type': 'password'},
                'trim_whitespace': False
            },
        }

    def get_groups_name(self, instance):
        groups = instance.groups.all()
        return ';'.join([g.name for g in groups])

    def get_shop_name(self, instance):
        shops = instance.shop.all()
        if shops:
            return ';'.join([shop.name for shop in shops])
        return ''

    def get_reset_password_url(self, instance):
        return reverse('{}-reset-password'.format(self.Meta.model._meta.model_name.lower()), args=(instance.id, ),
                       request=self.context.get('request'))

    def get_permissions(self, instance):
        permissions = list(instance.get_all_permissions())
        permissions.sort()
        return permissions

    def create(self, validated_data):
        password = validated_data.pop('password', getattr(settings, 'DEFAULT_ADMIN_PASSWORD', '123456'))
        # 默认创建的是管理员
        validated_data.setdefault('is_staff', True)
        instance = super().create(validated_data)
        instance.set_password(password)
        instance.save()
        return instance

    def validate(self, attrs):
        request = self.context.get('request')

        if getattr(settings, 'USER_JUST_ONE_GROUP', False) and len(attrs.get('groups', [])) > 1:
            raise serializers.ValidationError(_('One user can only have one role.'))

        # 自己对自己有些动作不能操作
        if request and self.instance and self.instance == request.user:
            if 'groups' in attrs:
                new_groups = attrs.get('groups')
                old_groups = list(self.instance.groups.all())
                if len(new_groups) != len(old_groups) or set(new_groups) != set(old_groups):
                    raise serializers.ValidationError('不可以修改自己的管理员类型。')

        # 作修改时不给修改密码, 密码修改只能通过重置密码和修改密码接口修改
        if self.instance:
            attrs.pop('password', None)
        return attrs


class UserChangePasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(label='旧密码', write_only=True, required=True,
                                         trim_whitespace=False, style={'input_type': 'password'})
    new_password = serializers.CharField(label='新密码', write_only=True, required=True,
                                         trim_whitespace=False, style={'input_type': 'password'})
    re_password = serializers.CharField(label='确认新密码', write_only=True, required=True,
                                        trim_whitespace=False, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('old_password', 'new_password', 're_password')

    def validate_old_password(self, value):
        if not self.instance.check_password(value):
            raise serializers.ValidationError('旧密码错误，请确认后重试')
        return value

    def validate(self, data):
        if data['new_password'] != data['re_password']:
            raise serializers.ValidationError(_('The new password is inconsistency twice, please confirm.'))
        return data

    def save(self, **kwargs):
        self.instance.set_password(self.validated_data['new_password'])
        self.instance.save()
        return self.instance


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = Group
        fields = generate_fields(Group, remove=["permissions"])