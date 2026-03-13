import functools

from django.db.models import DecimalField, Func, Sum

SumDecimal = functools.partial(Sum, output_field=DecimalField())


class Round(Func):
    """
    Django wrapper around PostgresqlSQL ROUND() function.
    https://www.postgresql.org/docs/9.5/static/functions-math.html
    """

    function = "ROUND"
    arity = 2


class Round0(Round):
    def __init__(self, *expressions, **extra):
        expressions = list(expressions) + [0]
        super().__init__(*expressions, **extra)


class Round2(Round):
    def __init__(self, *expressions, **extra):
        expressions = list(expressions) + [2]
        super().__init__(*expressions, **extra)
