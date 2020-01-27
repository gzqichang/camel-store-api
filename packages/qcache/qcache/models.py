from django.db import models
from django.db.models.fields.reverse_related import ForeignObjectRel
from qcache.contrib import now

RELATED_ARGS = {}

def get_related_args(model):
    select_args = []
    prefetch_args = []
    for fld in model._meta.get_fields():
        if not fld.is_relation:
            continue
        if isinstance(fld, ForeignObjectRel):
            continue
        if fld.many_to_many:
            prefetch_args.append(fld.name)
        else:
            select_args.append(fld.name)
    return select_args, prefetch_args

def auto_related(model, queryset):
    if model in RELATED_ARGS:
        select_args, prefetch_args = RELATED_ARGS[model]
    else:
        select_args, prefetch_args = get_related_args(model)
        RELATED_ARGS[model] = select_args, prefetch_args

    if select_args:
        queryset = queryset.select_related(*select_args)
    if prefetch_args:
        queryset = queryset.prefetch_related(*prefetch_args)
    return queryset

def is_expired(model_instance, cache_timestamp, checked_model_instances):
    if not isinstance(model_instance, VersionedMixin):
        cls = model_instance.__class__
        print(f'WARN: {cls.__module__}.{cls.__name__} is unversioned.')
        return False
    
    key = (type(model_instance), model_instance.pk)
    # print('key:', hash(key))
    if key in checked_model_instances:
        return False
    is_expired_ = model_instance.cache_is_expired(cache_timestamp, checked_model_instances)
    if not is_expired_:
        checked_model_instances.add(key)
    return is_expired_

class VersionedMixin(models.Model):
    class Meta:
        abstract = True

    version_timestamp = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    def cache_is_expired(self, cache_timestamp, checked_model_instances):
        if self.version_timestamp > cache_timestamp:
            return True

        for fld in self._meta.get_fields():
            if not fld.is_relation:
                continue
            if isinstance(fld, ForeignObjectRel):
                continue
            # one_to_many, many_to_one, one_to_one
            if not fld.many_to_many:
                related = getattr(self, fld.name)
                if related and is_expired(related, cache_timestamp, checked_model_instances):
                    return True
            else:
                # many_to_many
                related_objects = auto_related(fld.related_model, getattr(self, fld.name).all())
                for related in related_objects:
                    if related and is_expired(related, cache_timestamp, checked_model_instances):
                        return True
        return False
