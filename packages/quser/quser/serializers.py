from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.reverse import reverse

from captcha.models import CaptchaStore
from . import utils, models


class UserLoginSerializer(AuthTokenSerializer):
    key = serializers.CharField(label=_('Key'), required=False)
    challenge = serializers.CharField(label=_('Challenge'), required=False)

    def validate(self, attrs):
        if getattr(settings, 'IS_CAPTCHA_ENABLE', True):
            key = attrs.get('key')
            challenge = attrs.get('challenge')
            if not key or not challenge:
                raise serializers.ValidationError(_('Captcha `key` and `challenge` must be in request.data.'))
            try:
                captcha = CaptchaStore.objects.get(challenge=challenge.upper(), hashkey=key)
                captcha.delete()
            except CaptchaStore.DoesNotExist:
                raise serializers.ValidationError(_('Please input the security code.'))
        return super().validate(attrs)


class UserSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='quser:user-detail')
    groups = serializers.HyperlinkedRelatedField(
        help_text='该用户归属的组。一个用户将得到其归属的组的所有权限。',
        label='组', many=True,
        queryset=Group.objects.all(),
        required=False,
        view_name='quser:group-detail'
    )

    groups_name = serializers.SerializerMethodField()
    # groups_info = serializers.SerializerMethodField()
    reset_password_url = serializers.SerializerMethodField()

    class Meta:
        model = models.User
        fields = utils.generate_fields(
            model,
            add=['groups_name', 'reset_password_url'],
            remove=['is_superuser', 'is_staff', 'user_permissions']
        )
        extra_kwargs = {
            'password': {
                'write_only': True,
                'style': {
                    'input_type': 'password'
                },
                'trim_whitespace': False
            },
            'last_login': {
                'read_only': True
            },
            'date_joined': {
                'read_only': True
            }
        }

    def get_groups_name(self, instance):
        groups_name = list(instance.groups.values_list("name", flat=True))
        return ';'.join(groups_name)

    # def get_groups_info(self, instance):
    #     groups = instance.groups.all()
    #     serializer = GroupListSerializer(groups, many=True, context=self.context)
    #     return serializer.data

    def get_reset_password_url(self, instance):
        return reverse(
            'quser:user-reset-password',
            args=(instance.id,),
            request=self.context.get('request')
        )

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

        # 限制用户对自己账号的某些操作
        if request and self.instance and self.instance == request.user:
            if 'groups' in attrs:
                new_groups = attrs.get('groups')
                old_groups = list(self.instance.groups.all())
                if len(new_groups) != len(old_groups) or set(new_groups) != set(old_groups):
                    raise serializers.ValidationError(_('You can not change your permissions.'))

            if 'username' in attrs and attrs.get('username') != self.instance.username:
                raise serializers.ValidationError(_('You can not change your username.'))

        # 无法直接修改密码，只允许通过重置密码和修改密码接口修改
        if self.instance:
            attrs.pop('password', None)
        return attrs


class UserChangePasswordSerializer(serializers.ModelSerializer):
    old_password = serializers.CharField(
        label=_('Old Password'),
        write_only=True,
        required=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        label=_('New Password'),
        write_only=True,
        required=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )
    re_password = serializers.CharField(
        label=_('Repeat Password'),
        write_only=True,
        required=True,
        trim_whitespace=False,
        style={'input_type': 'password'}
    )

    class Meta:
        model = models.User
        fields = ('old_password', 'new_password', 're_password')

    def validate_old_password(self, value):
        if not self.instance.check_password(value):
            detail = _('The old password is incorrect. Please enter the correct old password to verify your identity.')
            raise serializers.ValidationError(detail)
        return value

    def validate(self, data):
        if data['new_password'] != data['re_password']:
            detail = _('The new password is inconsistency twice, please confirm.')
            raise serializers.ValidationError(detail)
        return data

    def save(self, **kwargs):
        self.instance.set_password(self.validated_data['new_password'])
        self.instance.save()
        return self.instance


class PermissionsField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        request = self.context.get('request')
        queryset = super().get_queryset()
        if request and request.user and request.user.is_staff:
            allow_perms = models.get_user_editable_permissions(request.user)
            allow_perm_ids = [item.id for item in allow_perms]
            return queryset.filter(pk__in=allow_perm_ids)
        return queryset


class GroupListSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='quser:group-detail')

    class Meta:
        model = Group
        fields = utils.generate_fields(Group, remove=['permissions', ])


class GroupDetailSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name='quser:group-detail')

    permissions = PermissionsField(
        label=_('Permissions'),
        queryset=models.get_editable_permissions(),
        many=True
    )
    permission_trees = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = utils.generate_fields(Group, add=['permission_trees', ])

    def validate_permissions(self, value):
        if self.instance:
            if self.instance == Group.objects.first():
                new = value
                old = models.get_group_editable_permissions(self.instance)
                if len(new) != len(old) or set(new) != set(old):
                    raise serializers.ValidationError(_('Can not change permissions for super.'))

            request = self.context.get('request')
            assert request is not None, 'request is required'
            if self.instance in request.user.groups.all():
                raise serializers.ValidationError(_('Can not change permissions for yourself'))
        return value

    def get_permission_trees(self, instance):
        request = self.context.get('request')
        permissions = list(models.get_user_editable_permissions(request.user))
        permissions.sort(key=lambda x: x.name)
        group_permissions = models.get_group_editable_permissions(instance)
        return models.get_permission_tree_from_queryset(permissions=permissions, group_permissions=group_permissions)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        permissions = set(ret['permissions'])
        editable_permissions = set([item[0] for item in models.get_editable_permissions().values_list('id')])
        ret['permissions'] = permissions & editable_permissions
        return ret
