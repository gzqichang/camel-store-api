from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers


class ModelSerializer(serializers.HyperlinkedModelSerializer):
    """
        自动在返回给前端的 data 中添加选项的显示内容
        readonly_fields: 可以指定只读字段, 自动加入只读字段, 即使在 fields 中没有定义
    """
    exclude_id_field = True
    readonly_fields = ()
    file_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save_user(self, instance, foreign_key):
        request = self.context.get('request')
        try:
            foreign_fields = instance._meta.get_field(foreign_key)
            if request and isinstance(request.user, foreign_fields.related_model):
                setattr(instance, foreign_key, request.user)
                instance.save()
        except FieldDoesNotExist:
            pass

    def create(self, validated_data):
        instance = super().create(validated_data)
        self.save_user(instance, 'create_user')
        self.save_user(instance, 'modify_user')
        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self.save_user(instance, 'modify_user')
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if self.exclude_id_field:
            ret.setdefault('id', instance.id)

        fields = self.get_fields()

        for field_name, field in fields.items():
            if isinstance(field, serializers.ChoiceField):
                ret['{}_display'.format(field_name)] = field.choices.get(ret[field_name])

        for field_name in self.readonly_fields:
            if field_name not in ret:
                ret[field_name] = getattr(instance, field_name)

        return ret
