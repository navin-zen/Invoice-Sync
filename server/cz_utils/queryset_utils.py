import datetime
import operator

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Q, QuerySet, deletion
from django.db.models.functions import Coalesce
from django.utils.timezone import now

__all__ = (
    "CloudZenQuerySet",
    "DateVersionedQuerySetMixin",
    "populate_model_instances",
    "populate_generic_content_object",
)


class Collector(deletion.Collector):
    """
    Our customization of Django's delete Collector.

    Instead of looking up all fields of related objects that could be
    affected by a delete operation, we only look up the `pk` field.
    """

    def related_objects(self, related, objs):
        """
        Gets a QuerySet of objects related to ``objs`` via the relation ``related``.
        """
        return (
            related.related_model._base_manager.only("pk")
            .using(self.using)
            .filter(**{"%s__in" % related.field.name: objs})
        )


def rewrite_key(d, key, newkey):
    """
    Rewrite a key in a dictionary.
    """
    d[newkey] = d.pop(key)
    return d


def populate_model_instances(Model, iterable, key=None, idx=None, select_related=False, pk_field="pk"):
    """
    Lookup objects by primary key and populates them into iterable.

    Updates iterable in place.

    Each element of 'iterable' is either a dict or a list.

    If dict, (i.e. key is specified), populate key 'key' of each element of
    'iterable' with an object of model 'Model'

    for i in iterable:
        i[key] = Model.objects.get(pk=i[key])

    If list, (i.e. idx is specified), populate index 'idx' of each element of
    'iterable' with an object of model 'Model'

    for i in iterable:
        i[idx] = Model.objects.get(pk=i[idx])
    """
    lst = list(iterable)
    if key:
        pks = [i.get(key) for i in lst]
    else:
        pks = [i[idx] for i in lst]
    if isinstance(Model, QuerySet):
        qs = Model
    else:
        qs = Model.objects
    objects = qs.filter(**{f"{pk_field}__in": list(set(pks))})
    if select_related:
        if isinstance(select_related, bool):
            objects = objects.select_related()
        else:
            objects = objects.select_related(*select_related)
    objdict = {getattr(o, pk_field, None): o for o in objects}
    for pk, i in zip(pks, lst):
        if pk is not None:
            if key:
                i[key] = objdict.get(pk)
            else:
                i[idx] = objdict.get(pk)
    return lst


def populate_generic_content_object(
    iterable,
    target_field,
    content_type_pk_getter=None,
    object_id_getter=None,
    content_object_field="content_object",
    querysets=None,
):
    """
    Given an iterable of objects containing a `content_object`
    GenericForeignKey field, populate them with a small number of SQL
    queries. We issue one query per type of foreign model.

    Populates the `iterable` in place.

    :param: Model - The Model whose instances are in the iterable (not used right now)
    :param: iterable - The iterable (usually list) of objects
    :param: target_field - The name of the field to write the result to
    :param: content_object_field - The name of the GenericForeignKey() field
    :param: querysets - A dict mapping a foreign models to querysets for
        that model. We can use this to optimized the data we are fetching
        for the foreign model.
    """
    if content_type_pk_getter is None:
        content_type_pk_getter = operator.itemgetter("content_type_id")
    content_type_pks = {content_type_pk_getter(i) for i in iterable}
    related_models = {ct_pk: ContentType.objects.get_for_id(ct_pk).model_class() for ct_pk in content_type_pks}
    ############################################################
    # A mapping from ct_pk -> dict(pk, obj)
    if object_id_getter is None:
        object_id_getter = operator.itemgetter("object_uuid")
    related_objects = {}
    for ct_pk, model in related_models.items():  # Get objects for all related models
        qs = (querysets and querysets.get(model)) or model.objects
        pks = {object_id_getter(i) for i in iterable if (content_type_pk_getter(i) == ct_pk)}
        related_objects[ct_pk] = {i.pk: i for i in qs.filter(pk__in=pks)}
    ############################################################
    # Populate the objects
    for i in iterable:
        setattr(i, target_field, related_objects[content_type_pk_getter(i)][object_id_getter(i)])
    return iterable


class SanityCheckFailure(Exception):
    "Failure of any sanity check that we add in our code."

    pass


class CloudZenQuerySet(QuerySet):
    """
    CloudZen's extensions to QuerySet.

    Our extensions include:
        coalesce()
            Coalesce and rewrite fields.
        withannotations()
            Add certain model specific annotations to the queryset.
    """

    def __init__(self, model=None, query=None, using=None, hints=None):
        super().__init__(model, query, using, hints)
        self._cz_seen_order_by = False

    def _clone(self, **kwargs):
        """
        WARNING: This is an internal function. In fact, this function's
        definition is changed in the Development version of Django.
        https://github.com/django/django/commit/4c3bfe9053766d378999d06ec34ee5fd4e39f511#diff-5b0dda5eb9a242c15879dc9cd2121379L937
        When upgrading the new version, we should change the signature of
        _clone()
        """
        clone = super()._clone(**kwargs)
        clone._cz_seen_order_by = self._cz_seen_order_by
        return clone

    def coalesce(self, *fields, **mappings):
        """
        Coalesce and rewrite fields.

        For each field specified in 'fields', we annotate the queryset with
        the value Coalesce(field, 0). By default, the name of the annotated
        value is field_coalesed.

        'mappings' allows the user to specify a different name for the
        annotated fields.

        A few examples:

        coalesce('myfield')
            Adds a field 'myfield_coalesced' to the queryset
        coalesce(newname='myfield')
            Adds a field 'newname' to the queryset
        """
        mappings.update({f"{f}_coalesced": f for f in fields})
        annotate_spec = {name: Coalesce(F(field), 0) for (name, field) in mappings.items()}
        return self.annotate(**annotate_spec)

    model_annotation_spec = {}

    def _annotate_or_aggregate_spec_without_rewrites(self, *values, **mapping):
        spec = self.model_annotation_spec
        user_request = set(list(values) + list(mapping.values()))
        if any((u not in spec) for u in user_request):
            raise ValueError(f"In withannotations(), requested values should be one of {spec.keys()}")
        if not user_request:
            user_request = spec.keys()
        return {v: spec[v] for v in user_request}

    def _annotate_or_aggregate_spec(self, *values, **mapping):
        request_spec = self._annotate_or_aggregate_spec_without_rewrites(*values, **mapping)
        for alias, value in mapping.items():
            rewrite_key(request_spec, value, alias)
        return request_spec

    def withannotations(self, *values, **mapping):
        """
        Annotate the queryset with certain properties specific to the
        model.

        If the user wants only certain 'values', they can specify it here.
        If no 'values' is specified, the result is annotated with all those
        values mentioned in 'spec'.

        By optionally specifying a mapping, the user can rewrite the name
        of the computed value.

        A few examples:

        withannotations():
            Annotate the queryset with all the values we compute
        withannotations('weight__sum'):
            Only weight__sum will be computed
        withannotations('size__sum', requirement_weights='weight__sum')
            We compute size__sum and weight__sum, but the value of
            weight__sum will be renamed to requirement_weights.
        """
        request_spec = self._annotate_or_aggregate_spec(*values, **mapping)
        return self.annotate(**request_spec)

    def withaggregates(self, *values, **mapping):
        """
        Aggregate results similar to `withannotations`.
        """
        request_spec = self._annotate_or_aggregate_spec(*values, **mapping)
        return self.aggregate(**request_spec)

    def annotate(self, *args, **kwargs):
        if not self._cz_seen_order_by:
            if settings.DEBUG:
                raise SanityCheckFailure("annotate() should not be invoked without order_by()")
        return super().annotate(*args, **kwargs)

    def order_by(self, *field_names):
        self._cz_seen_order_by = True
        return super().order_by(*field_names)

    def date_in_range(self, datefield, start, end, reference_date=None):
        """
        Filter objects where 'datefield' falls within a range.

        This is a flexible function to filter objects by the value of a
        date field. 'start' and 'end' specify the range
            (start <= datefield < end)
        to compare against. 'start' and 'end' could either be date objects
        of integers. In case they are integers, they represent an offset
        from 'reference_date'. If 'start' or 'end' is None, that size of the range
        check is left out.

        If not specified, 'reference_date' is assumed to be "today".
        """
        reference_date = reference_date or datetime.date.today()
        if (start is not None) and not isinstance(start, datetime.date):
            start = reference_date + datetime.timedelta(days=start)
        if (end is not None) and not isinstance(end, datetime.date):
            end = reference_date + datetime.timedelta(days=end)
        filter_args = {}
        if start is not None:
            filter_args[f"{datefield}__gte"] = start
        if end is not None:
            filter_args[f"{datefield}__lt"] = end
        return self.filter(**filter_args)

    def created_or_modified_since(self, key, t):
        """
        Filter all objects created or modified since `t` or since time `t` ago.
        """
        if isinstance(t, datetime.datetime):
            value = t
        elif isinstance(t, datetime.timedelta):
            value = now() - t
        elif isinstance(t, int):
            value = now() - datetime.timedelta(seconds=t)
        else:
            raise TypeError("Invalid type of parameter `t`")
        return self.filter(**{key: value})

    def created_since(self, t):
        """
        Filter all objects created since `t` or since time `t` ago.
        """
        return self.created_or_modified_since("create_date__gte", t)

    def modified_since(self, t):
        """
        Filter all objects created since `t` or since time `t` ago.
        """
        return self.created_or_modified_since("modify_date__gte", t)

    def pks(self):
        """
        Return only the pks as a ValueListQuerySet.
        """
        return self.values_list("pk", flat=True)

    def uuids(self):
        """
        Return only the uuids as a ValueListQuerySet.
        """
        return self.values_list("uuid", flat=True)

    def as_list(self):
        """
        Return the queryset as a list.
        """
        return list(self)

    def as_set(self):
        """
        Return the queryset as a set.
        """
        return set(self)

    def as_dict(self, keyfn, valuefn=None, dict_class=dict):
        """
        Return the queryset as a dict.
        """
        if valuefn:
            return dict_class((keyfn(x), valuefn(x)) for x in self)
        else:
            return dict_class((keyfn(x), x) for x in self)

    def get_the_one_result(self, default=None):
        """
        Return the only element in the result set.

        Returns `default` if the result set is empty. Raises ValueError if the
        result set has more than one element.
        """
        count = self.count()
        if count == 0:
            return default
        elif count == 1:
            return self[0]
        else:
            raise ValueError("QuerySet has more than 1 result.")

    def alive_at(self, t):
        """
        For a TemporalVersionedModel, the list of objects alive at time
        `t`.

        If `t` is None, the list of objects alive right now.
        """
        return self.filter(birthtime__le=t).filter(Q(deathtime__isnull=True) | Q(deathtime__gt=t))

    def value(self, field):
        return self.values_list(field, flat=True)

    def youngest(self, count=None):
        """
        Returns a list of the youngest `count` objects, in ascending age order.

        If count is None, returns only the youngest object (not a list)
        """
        qs = self.order_by("-create_date")
        if count is None:
            return qs.first()
        return list(reversed(qs[:count]))

    def better_delete(self):
        """
        Deletes the records in the current QuerySet.

        Our customization of Django's QuerySet delete() method that does
        not look up all fields of related objects.
        """
        assert self.query.can_filter(), "Cannot use 'limit' or 'offset' with delete."

        if self._fields is not None:
            raise TypeError("Cannot call delete() after .values() or .values_list()")

        del_query = self._clone()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        # Disable non-supported fields.
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering(force_empty=True)

        collector = Collector(using=del_query.db)
        collector.collect(del_query)
        deleted, _rows_count = collector.delete()

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
        return deleted, _rows_count

    better_delete.alters_data = True
    better_delete.queryset_only = True

    def raw_delete(self):
        return self._raw_delete(self.db)


class DateVersionedQuerySetMixin:
    """
    QuerySet methods for DateVersionedModel.
    """

    def alive_on(self, d):
        """
        For a DateVersionedModel, the list of objects alive on date `d`.

        If `d` is None, the list of objects alive today.
        """
        d = d or datetime.date.today()
        return self.filter(Q(birthdate__lte=d) & (Q(deathdate__isnull=True) | Q(deathdate__gt=d)))

    def delete(self):
        raise RuntimeError(
            """
            DateVersionedQuerySetMixin.delete() is not allowed.
        """
        )

    delete.alters_data = True
    delete.queryset_only = True

    def update(self, **kwargs):
        """
        We don't allow updates to TimeStamped model.
        """
        raise RuntimeError(
            """
            DateVersionedQuerySetMixin.update() is not allowed.
        """
        )

    update.alters_data = True
