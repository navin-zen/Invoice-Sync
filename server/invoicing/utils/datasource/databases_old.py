"""
Utilities related to database data sources
"""

import psycopg2

CONNECTION_PARAMS = [
    "host",
    "dbname",
    "port",
    "username",
    "password",
]


def postgresql_connect(**kwargs):
    kwargs = {k: v for (k, v) in kwargs.items() if (v and (k in CONNECTION_PARAMS))}
    dsn = psycopg2.extensions.make_dsn(**kwargs)
    try:
        return bool(psycopg2.connect(dsn))
    except Exception:
        return False


# def mysql_connect():


