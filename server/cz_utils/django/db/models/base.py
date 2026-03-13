"""
Abstract Model classes defined by CloudZen.
"""

import datetime
import re
import uuid as uuidmodule

import inflection
from django.conf import settings
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.urls.base import reverse
from django.utils.decorators import classonlymethod
from django.utils.functional import cached_property

from ....validation_utils import get_model_field, validate_equal
from ..fields import CzForeignKey

__all__ = (
    "UuidModel",
    "TimeStampedModel",
    "ByLineModel",
    "WithUrlsModel",
    "CloudZenModel",
    "CloudZenUuidPkModel",
    "DateVersionedModel",
)


class DateVersionedModel(models.Model):
    """
    DateVersionedModel

    An abstract base class model that provides "birthdate" and "deathdate"
    fields to be used to version a model by date.

    An object is valid at date 'd' if ((birthdate <= t) and (deathdate > t)).

    This can be used to store historical values that change over time, and
    more importantly do not change intra-day. An example would be a tax
    rate. The government could announce a new tax rate starting on a
    particular date.
    """

    class Meta:
        abstract = True

    birthdate = models.DateField(editable=False, db_index=True)
    deathdate = models.DateField(editable=False, null=True, db_index=True)

    def _check_dates_in_order(self):
        """
        Check that birthdate < deathdate.
        """
        if self.birthdate > self.deathdate:
            raise ValueError("birthdate is greater than deathdate")

    def delete(self, using=None, keep_parents=False, change_date=None):
        if change_date is None:
            raise ValueError(f"Call to {self.__class__.__name__}.delete is missing required argument 'change_date'")
        assert isinstance(change_date, datetime.date)
        if self.deathdate is not None:
            raise ValueError("Cannot delete an object that is already updated.")
        self.deathdate = change_date
        self._check_dates_in_order()
        super().save()

    def save(self, *args, **kwargs):
        """
        We might want to save a new object or an existing one.

        For a new object, set birthdate = change_date and save it.

        For an existing object, don't change any of its fields. Set only
        the deathdate field to change_date. Instead, create a new object with the
        exact field values and save it.

        WARNING: If there is a 'uuid' field in this model whose value
        should be unique, we might want to set it for the newly created
        object as well.

        Requires a keyword argument 'change_date', that specifies that date on
        which the object changed or will change.
        """
        try:
            change_date = kwargs.pop("change_date")
        except KeyError:
            raise ValueError(f"Call to {self.__class__.__name__}.save is missing required argument 'change_date'")
        assert isinstance(change_date, datetime.date)
        assert self.deathdate is None
        if self.pk is not None:
            # Save the old version
            old = type(self)._default_manager.get(pk=self.pk)
            old.deathdate = change_date
            old._check_dates_in_order()
        else:
            old = None
        # Save the new version
        new = self
        new.pk = None
        new.birthdate = change_date
        new.deathdate = None
        self.date_versioned_pre_save(old, new)
        if old is not None:
            super(DateVersionedModel, old).save(*args, **kwargs)
        super(DateVersionedModel, new).save(*args, **kwargs)
        self.date_versioned_post_save(old, new)

    def date_versioned_pre_save(self, old, new):
        """
        Override this method to perform any action just *before* saving the
        old and the new versions of the object.
        """
        pass

    def date_versioned_post_save(self, old, new):
        """
        Override this method to perform any action just *after* saving the
        old and the new versions of the object.
        """
        pass


class UuidModel(models.Model):
    """
    UuidModel

    An abstract base class model that provides an "uuid" field.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        abstract = True

    uuid = models.UUIDField(default=uuidmodule.uuid4, editable=False, unique=True)

    @classmethod
    def _has_uuid_field(cls, model):
        try:
            return bool(model._meta.get_field("uuid"))
        except FieldDoesNotExist:
            return False

    def full_clean(self, exclude=None, validate_unique=True):
        if (exclude is None) and self._has_uuid_field(self):
            exclude = ["uuid"]
        return super().full_clean(exclude=exclude, validate_unique=validate_unique)


class TimeStampedModel(models.Model):
    """
    TimeStampedModel

    An abstract base class model that provides "create_date" and
    "modify_date" fields.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        abstract = True

    create_date = models.DateTimeField(auto_now_add=True)
    modify_date = models.DateTimeField(auto_now=True)


class ByLineModel(models.Model):
    """
    A model that stores who created/modified it.

    An abstract base class model that provides "created_by" and
    "modified_by" fields.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        abstract = True

    created_by = CzForeignKey(settings.AUTH_USER_MODEL, null=True, editable=False, related_name="+")
    modified_by = CzForeignKey(settings.AUTH_USER_MODEL, null=True, editable=False, related_name="+")


class WithUrlsModel(models.Model):
    """
    WithUrlsModel

    An abstract base class customized for CloudZen's apps. Our conventions
    are:
        * We define get_absolute_url(), get_update_url(), and
          get_delete_url() functions. These functions rely on the URL names
          following a specific format. For example, with a model named
          MyModel, the three URL names are `my_model_detail`,
          `my_model_update`, and `my_model_delete` respectively.
    """

    class Meta:
        abstract = True

    @classonlymethod
    def _check_model_class_name(cls, **kwargs):  # pylint: disable=unused-argument
        """
        Check that the model's name is in CamelCase.
        """
        if re.search(r"[A-Z][A-Z]", cls.__name__):
            return [
                checks.Error(
                    "Model class name should be strictly in CamelCase",
                    hint="Rename the class to not have consecutive upper case characters",
                    obj=cls,
                    id="cz_utils.E001",
                )
            ]
        return []

    @classonlymethod
    def check(cls, **kwargs):
        """
        All the checks for our model
        """
        errors = super().check(**kwargs)
        errors.extend(cls._check_model_class_name(**kwargs))
        return errors

    def _get_url_with_suffix(self, suffix, has_args=True):
        """Get a URL for this model."""
        url_name = "{}:{}{}".format(
            self._meta.app_label, inflection.underscore(self._meta.concrete_model.__name__), suffix
        )
        args = (self.uuid,) if has_args else ()
        # args = (self.pk,) if has_args else ()
        return reverse(url_name, args=args)

    def get_create_url(self):
        """The URL to create an instance of this model."""
        return self._get_url_with_suffix("_create", has_args=False)

    def get_absolute_url(self):
        """The URL to show details of this model."""
        return self._get_url_with_suffix("_detail")

    def get_pdf_url(self):
        """The URL to show details of this model in PDF format."""
        return self._get_url_with_suffix("_detail_pdf")

    def get_update_url(self):
        """The URL to update this model."""
        return self._get_url_with_suffix("_update")

    def get_delete_url(self):
        """The URL to delete this model."""
        return self._get_url_with_suffix("_delete")


class RestrictedFieldNamesModel(models.Model):
    """
    Disallow certain field names in models.

    We do not want to allow certain "reserved" field names in models.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        abstract = True

    @classonlymethod
    def _check_model_field_names(cls, **kwargs):  # pylint: disable=unused-argument
        """
        Check that the names of a model's fields are not restricted.
        """
        disallowed_field_names = [
            "history",  # Used by SimpleHistory
            "content",  # Used by Haystack
            "content_auto",  # Used by Haystack
            "text",  # Used by Haystack
        ]
        for field in cls._meta.get_fields():
            name = field.name
            if name in disallowed_field_names:
                yield checks.Error(
                    "Model contains a prohibitted field name",
                    hint=f"Rename the field '{name}'",
                    obj=cls,
                    id="cz_utils.E002",
                )

    @classonlymethod
    def _check_unallowed_methods(cls, **kwargs):  # pylint: disable=unused-argument
        """
        Guard against mistakes in the naming of model methods.

        For instance, we should name a method __unicode__ (This was a
        Python 2 usage).
        """
        disallowed_method_names = ["__unicode__"]
        for name in disallowed_method_names:
            if hasattr(cls, name):
                yield checks.Error(
                    "Model contains a prohibitted method name",
                    hint=f"Rename or remove the method '{name}'",
                    obj=cls,
                    id="cz_utils.E003",
                )

    @classonlymethod
    def check(cls, **kwargs):
        """
        All the checks for our model
        """
        errors = super().check(**kwargs)
        errors.extend(cls._check_model_field_names(**kwargs))
        # errors.extend(cls._check_unallowed_methods(**kwargs))
        return errors


class CloudZenModel(
    WithUrlsModel,
    RestrictedFieldNamesModel,
    # ByLineModel,
    TimeStampedModel,
    UuidModel,
):
    """
    CloudZenModel

    An abstract base class customized for CloudZen's apps.

    We define CzMeta. Refer to its documentation for further details.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        abstract = True

    class CzMeta:
        """
        Metadata as per the conventions of a CloudZen model.

        CzMeta has only attribute.
            * validate_equal_spec: This is a list of 3-tuples. Each tuple
              is of the form (field1, field2, message) and passed as
              arguments to validate_equal. This spec validates that field1
              and field2 are equal. The fields can have double underscores
              in them to traverse foreign keys. An example spec entry:
                    ('purchaseorder__project', 'invoice__project',
                        "The invoice's project should be equal to the
                        purchase order's project")
        """

        validate_equal_spec = []

    def _clean_validate_equal(self):
        for f1, f2, message in self.CzMeta.validate_equal_spec:
            validate_equal(self, f1, f2, message)

    def clean(self):
        self._clean_validate_equal()
        return super().clean()

    @classonlymethod
    def _check_czmeta(cls, **kwargs):
        if not issubclass(cls.CzMeta, CloudZenModel.CzMeta):
            yield checks.Error(
                "Model's CzMeta should inherit from CloudZenModel.CzMeta",
                hint="Use CzMeta(CloudZenModel.CzMeta) in the model's definition",
                obj=cls,
                id="cz_utils.E002",
            )
        for name in dir(cls.CzMeta):
            if name.startswith("_"):
                continue
            if name not in dir(CloudZenModel.CzMeta):
                yield checks.Error(
                    f"Unexpected field '{name}' in CzMeta definition",
                    hint="Check for typos in CzMeta",
                    obj=cls,
                    id="cz_utils.E003",
                )

    @classonlymethod
    def _check_validate_equal_spec(cls, **kwargs):
        def invalid_field_spec_error(fname):
            return checks.Error(
                f"Field '{fname}' in validate_equal_spec is incorrect",
                hint="Check for typos in the field specification",
                obj=cls,
                id="cz_utils.E004",
            )

        def invalid_field_type(fname):
            return checks.Error(
                f"Field '{fname}' in validate_equal_spec should be a ForeignKey or OneToOneField",
                obj=cls,
                id="cz_utils.E005",
            )

        for fname1, fname2, _ in cls.CzMeta.validate_equal_spec:
            field1 = get_model_field(cls, fname1)
            field2 = get_model_field(cls, fname2)
            if not field1:
                yield invalid_field_spec_error(fname1)
                continue
            if not field2:
                yield invalid_field_spec_error(fname2)
                continue
            if not isinstance(field1, (models.ForeignKey, models.OneToOneField)):
                yield invalid_field_type(fname1)
                continue
            if not isinstance(field2, (models.ForeignKey, models.OneToOneField)):
                yield invalid_field_type(fname2)
                continue
            if field1.related_model != field2.related_model:
                yield checks.Error(
                    f"Incompatible types for '{fname1}' and '{fname2}' in validate_equal_spec",
                    hint="Are the two fields of the same type?",
                    obj=cls,
                    id="cz_utils.E006",
                )

    @classonlymethod
    def _check_model_meta(cls, **kwargs):
        """
        Ensure that 'ordering' and 'unique_together' are properly defined
        in a module.
        """
        ordering = cls._meta.ordering
        if ordering:
            if not (isinstance(ordering, tuple) and all(isinstance(s, str) for s in ordering)):
                return [
                    checks.Error(
                        "Meta.ordering should be a tuple of strings",
                        hint="Check the definition of Meta.ordering",
                        obj=cls,
                        id="cz_utils.E008",
                    )
                ]
        unique_together = cls._meta.unique_together
        if unique_together:
            if not isinstance(unique_together, tuple):
                return [
                    checks.Error(
                        "Meta.unique_together should be a tuple",
                        hint="Check the definition of Meta.unique_together",
                        obj=cls,
                        id="cz_utils.E009",
                    )
                ]
            for unique in unique_together:
                if not (isinstance(unique, tuple) and all(isinstance(s, str) for s in unique)):
                    return [
                        checks.Error(
                            "Meta.unique_together should be a tuple of tuple of strings",
                            hint="Check the definition of Meta.unique_together",
                            obj=cls,
                            id="cz_utils.E010",
                        )
                    ]
        return []

    @classonlymethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_czmeta(**kwargs))
        errors.extend(cls._check_validate_equal_spec(**kwargs))
        return errors

    @cached_property
    def pusher_channel(self):
        return f"private-{self.uuid.hex}"


class CloudZenUuidPkModel(CloudZenModel):
    """
    A model that uses uuid as the primary key
    """

    class Meta:  # pylint: disable=too-few-public-methods
        abstract = True

    uuid = models.UUIDField(default=uuidmodule.uuid4, editable=False, unique=True, primary_key=True)
