"""
Utility classes to define a JSON schema.  http://json-schema.org/

The class definitions given below mirror the tutotial in
https://spacetelescope.github.io/understanding-json-schema/index.html
"""

import decimal
import inspect
from typing import Any

import jsonschema
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class Type:
    """
    The base class to declare a JSON type.
    """

    UNUSED = object()
    NAME = property()
    FIELDS = property()

    def __init__(self, *args, **kwargs):  # pylint: disable=unused-argument
        self.kwargs = kwargs

    @classmethod
    def _construct_dict(cls, obj):
        # type: (dict) -> dict
        """
        The construct method for a dict.
        """
        if not all(isinstance(key, str) for key in obj.keys()):
            raise TypeError("The keys of dictionary must be strings.")
        return {key: cls.construct(value) for (key, value) in obj.items()}

    @classmethod
    def _construct_list(cls, obj: list | tuple) -> list:
        """
        The construct method for a list.
        """
        return [cls.construct(i) for i in obj]

    @classmethod
    def construct(cls, obj, definitions=None):
        """
        The construct method handling different types of objects.

        :param: definitions - Any definitions to attach
        """
        if inspect.isclass(obj) and issubclass(obj, Type):
            obj = obj()
        if isinstance(obj, int):
            return obj
        elif isinstance(obj, str):
            return obj
        elif isinstance(obj, decimal.Decimal):
            return obj
        elif isinstance(obj, Type):
            return obj.construct_type(definitions=definitions)
        elif isinstance(obj, dict):
            return cls._construct_dict(obj)
        elif isinstance(obj, (list, tuple)):
            return cls._construct_list(obj)
        else:
            raise TypeError("Unsupported type")

    def construct_type(self, definitions=None):
        """
        Construct the schema object of this type.

        :param: definitions - Any definitions to attach
        """
        obj = {}
        if self.NAME is not self.UNUSED:
            obj["type"] = self.NAME
        if definitions:
            obj["definitions"] = self.construct(definitions)
        for field in self.FIELDS:
            value = self.kwargs.get(field, None)
            if value is not None:
                obj[field] = self.construct(value)
        return obj


class Null(Type):
    """
    A JSON object of type null.

    https://spacetelescope.github.io/understanding-json-schema/reference/null.html
    """

    NAME = "null"
    FIELDS = []


class Boolean(Type):
    """
    A JSON object of type bool.

    https://spacetelescope.github.io/understanding-json-schema/reference/boolean.html
    """

    NAME = "boolean"
    FIELDS = []


class String(Type):
    """
    A JSON object of type string.

    https://spacetelescope.github.io/understanding-json-schema/reference/string.html
    """

    NAME = "string"
    FIELDS = [
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "enum",
        "const",
    ]


class Numeric(Type):
    """
    A JSON object of type numeric.

    https://spacetelescope.github.io/understanding-json-schema/reference/numeric.html
    """

    FIELDS = [
        "multipleOf",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "const",
    ]


class Integer(Numeric):
    """
    A JSON object of type integer.

    https://spacetelescope.github.io/understanding-json-schema/reference/numeric.html#integer
    """

    NAME = "integer"


class Number(Numeric):
    """
    A JSON object of type number.

    https://spacetelescope.github.io/understanding-json-schema/reference/numeric.html#number
    """

    NAME = "number"


class Decimal(Number):
    def __init__(self, numdigits, numdecimalplaces):
        super().__init__(
            multipleOf=decimal.Decimal(decimal.Decimal(10) ** -numdecimalplaces),
            maximum=(10 ** (numdigits - numdecimalplaces)),
            minimum=0,
        )


class Object(Type):
    """
    A JSON object of type 'object' (mapping).

    https://spacetelescope.github.io/understanding-json-schema/reference/object.html
    """

    NAME = "object"
    FIELDS = [
        "properties",
        "required",
        "minProperties",
        "maxProperties",
        "dependencies",
        "patternProperties",
        "additionalProperties",
        "definitions",  # Used only in outer-most object
    ]


class StrictObject(Object):
    """
    A stricter definition of Object
    """

    def __init__(self, properties):
        super().__init__(properties=properties, required=list(properties.keys()), additionalProperties=False)


class Array(Type):
    """
    A JSON object of type array.

    https://spacetelescope.github.io/understanding-json-schema/reference/array.html
    """

    NAME = "array"
    FIELDS = [
        "items",
        "additionalItems",
        "minItems",
        "maxItems",
        "uniqueItems",
        "definitions",  # Used only in outer-most object
    ]


class Tuple(Array):
    """
    Tuple - A special case of JSON array type.

    https://spacetelescope.github.io/understanding-json-schema/reference/array.html#tuple-validation
    """

    def __init__(self, *args, **kwargs):
        kwargs["items"] = args
        super().__init__(*args, **kwargs)


class Dict(Type):
    NAME = Type.UNUSED


class Ref(Dict):
    FIELDS = ["description"]

    def __init__(self, ref, *args, **kwargs):  # pylint: disable=unused-argument
        self.ref = ref
        super().__init__(*args, **kwargs)

    def construct_type(self, definitions=None):
        obj = super().construct_type(definitions=definitions)
        obj["$ref"] = f"#/definitions/{self.ref}"
        return obj


class AllOf(Dict):
    FIELDS = []

    def __init__(self, choices, *args, **kwargs):  # pylint: disable=unused-argument
        self.choices = choices
        super().__init__(*args, **kwargs)

    def construct_type(self, definitions=None):
        obj = super().construct_type(definitions=definitions)
        obj["allOf"] = Type.construct(self.choices)
        return obj


class AnyOf(Dict):
    FIELDS = []

    def __init__(self, choices, *args, **kwargs):  # pylint: disable=unused-argument
        self.choices = choices
        super().__init__(*args, **kwargs)

    def construct_type(self, definitions=None):
        obj = super().construct_type(definitions=definitions)
        obj["anyOf"] = Type.construct(self.choices)
        return obj


class Optional(AnyOf):
    """
    Either X or Null
    """

    def __init__(self, value, *args, **kwargs):  # pylint: disable=unused-argument
        choices = [value, Null]
        super().__init__(choices, *args, **kwargs)


def define_schema(type_):
    # type: (Type) -> dict
    """
    Define a JSON Schema.

    http://json-schema.org/
    https://spacetelescope.github.io/understanding-json-schema/index.html
    """
    schema = Type.construct(type_)
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    jsonschema.Draft7Validator.check_schema(schema)
    return schema


@deconstructible
class JsonValidator:
    def __init__(self, type_):
        # type: (Type)
        self.schema = define_schema(type_)
        self.validator = jsonschema.Draft4Validator(self.schema)

    def __call__(self, value):
        """
        Validates that the input matches the schema
        """
        if not value:
            return
        try:
            self.validator.validate(value)
        except jsonschema.ValidationError as ex:
            raise ValidationError(ex.message)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, JsonValidator) and (self.schema == other.schema)

    def __ne__(self, other: Any) -> bool:
        return not (self == other)
