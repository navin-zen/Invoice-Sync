"""
Utility functions related to databases
"""

import csv
import glob
import logging
import os
from io import BytesIO

import sqlalchemy
from django.utils import timezone
from sqlalchemy import inspect
from utils.importer import CustomXls

logger = logging.getLogger(__name__)


def create_engine(
    *,
    sqlalchemy_driver,
    hostname,
    port=None,
    username=None,
    password=None,
    database=None,
    backend_driver=None,
    dsn=None,
    service_name=None,
):
    """
    Create a SQLAlchemy engine
    """
    query = {}
    if backend_driver:
        query.update(
            {
                "driver": backend_driver,
            }
        )
    if service_name:
        query["service_name"] = service_name
    url = sqlalchemy.engine.url.URL(
        drivername=sqlalchemy_driver,
        username=username,
        password=password,
        host=hostname or dsn,
        port=port or None,
        database=database or None,
        query=query,
    )
    logger.info(f"Sqlalchemy connection: URL: {url}")
    if "oracle" in sqlalchemy_driver:
        engine = sqlalchemy.create_engine(url)
    else:
        engine = sqlalchemy.create_engine(url, connect_args={"connect_timeout": 5})
    logger.info(f"Sqlalchemy connection: Engine: {engine}")
    return engine


def check_connection(
    *,
    sqlalchemy_driver,
    hostname,
    port=None,
    username=None,
    password=None,
    database=None,
    backend_driver=None,
    dsn=None,
    service_name=None,
):
    """
    Make a connection to a database using sqlalchemy
    """
    engine = create_engine(
        sqlalchemy_driver=sqlalchemy_driver,
        hostname=hostname,
        port=port,
        username=username,
        password=password,
        database=database,
        backend_driver=backend_driver,
        dsn=dsn,
        service_name=service_name,
    )
    try:
        connection = engine.connect()  # NOQA
        return {
            "status": 1,
            "message": "connection success",
            "timestamp": timezone.now().isoformat(),
        }
    except Exception as ex:
        return {
            "status": 0,
            "message": str(ex),
            "timestamp": timezone.now().isoformat(),
        }


def create_engine_for_microsoft_dynamics(*, sqlalchemy_driver, hostname, database, backend_driver=None):
    query = {}
    if backend_driver:
        query.update(
            {
                "driver": backend_driver,
            }
        )
    url = sqlalchemy.engine.url.URL(
        drivername=sqlalchemy_driver,
        host=hostname,
        database=database,
        query=query,
    )
    engine = sqlalchemy.create_engine(url, connect_args={"connect_timeout": 5})
    return engine


def check_microsoft_dynamics_connection(*, sqlalchemy_driver, hostname, database, backend_driver=None):
    """
    This function is used to check the connection to SQLServer using windows authentication
    for Microsoft Dynamics Navision 2016
    """
    engine = create_engine_for_microsoft_dynamics(
        sqlalchemy_driver=sqlalchemy_driver,
        hostname=hostname,
        database=database,
        backend_driver=backend_driver,
    )
    try:
        connection = engine.connect()
        del connection
        return {
            "status": 1,
            "message": "connection success",
            "timestamp": timezone.now().isoformat(),
        }
    except Exception as ex:
        return {
            "status": 0,
            "message": str(ex),
            "timestamp": timezone.now().isoformat(),
        }


def get_excel_filepath_for_glob(pattern):
    """
    Return a single excel file path matching `pattern`
    """
    matching_paths = sorted(glob.glob(pattern))
    if not matching_paths:
        raise ValueError(f"Found no file for: {pattern}")
    return matching_paths[0]


def checkExcelFile(path):
    try:
        filename = get_excel_filepath_for_glob(path)
        content = open(filename, "rb").read()
        xls_stream = BytesIO(content)
        worksheets = CustomXls.get_worksheets_wrapper(xls_stream)
        del worksheets
        return {
            "status": 1,
            "message": "connected to excel file",
            "timestamp": timezone.now().isoformat(),
        }
    except Exception as ex:
        return {
            "status": 0,
            "message": str(ex),
            "timestamp": timezone.now().isoformat(),
        }


def checkCsvFile(path):
    try:
        filename = get_excel_filepath_for_glob(path)
        in_stream = open(filename)
        rows = csv.reader(in_stream)
        del rows
        return {
            "status": 1,
            "message": "connected to csv file",
            "timestamp": timezone.now().isoformat(),
        }
    except Exception as ex:
        return {
            "status": 0,
            "message": str(ex),
            "timestamp": timezone.now().isoformat(),
        }


def check_oracle_ebs_paths(output_directory, input_directory):
    output_exists = os.path.exists(output_directory) and os.path.isdir(output_directory)
    input_exists = os.path.exists(input_directory) and os.path.isdir(input_directory)
    if input_exists and output_exists:
        return {
            "status": 1,
            "message": "Directories are accessible",
            "timestamp": timezone.now().isoformat(),
        }
    else:
        return {
            "status": 0,
            "message": "Directories are not accessible",
            "timestamp": timezone.now().isoformat(),
        }


def database_connection_kwargs(datasource):
    """
    Return kwargs that we can use for create_engine or check_connection
    function.

    :param: datasource - details of the datasource
    """
    ds = datasource
    config = (ds and ds.get("config")) or {}
    if not config:
        raise ValueError("Unable to find datasource config")
    if ds.get("type") == "db:mssql":
        hostname = config.get("hostname", "")
        port = config.get("port", None)
        username = config.get("username", "")
        password = config.get("password", "")
        database = config.get("database", "")
        backend_driver = config.get("backend_driver", "")
        return dict(
            sqlalchemy_driver="mssql+pyodbc",
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            database=database,
            backend_driver=backend_driver,
        )
    elif ds.get("type") == "db:postgresql":
        return dict(
            sqlalchemy_driver="postgresql",
            hostname=config.get("hostname", ""),
            port=config.get("port", None),
            username=config.get("username", ""),
            password=config.get("password", ""),
            database=config.get("database", ""),
        )
    elif ds.get("type") == "db:oracle":
        return dict(
            sqlalchemy_driver="oracle+cx_oracle",
            hostname=config.get("hostname", ""),
            port=config.get("port", None),
            username=config.get("username", ""),
            password=config.get("password", ""),
            database=config.get("database", ""),
            service_name=config.get("service_name", None),
        )
    elif ds.get("type") == "db:mysql":
        return dict(
            sqlalchemy_driver="mysql",
            hostname=config.get("hostname", ""),
            port=config.get("port", None),
            username=config.get("username", ""),
            password=config.get("password", ""),
            database=config.get("database", ""),
        )
    elif ds.get("type") == "file:excel":
        return dict(
            path=config.get("path", ""),
        )
    elif ds.get("type") == "file:csv":
        return dict(
            path=config.get("path", ""),
        )
    elif ds.get("type") == "odbc":
        return dict(
            sqlalchemy_driver="mssql+pyodbc",
            hostname=config.get("hostname", ""),
            dsn=config.get("dsn", ""),
        )
    elif ds.get("type") == "erp:oracleebs":
        return dict(
            input_directory=config.get("input_directory", ""),
            output_directory=config.get("output_directory", ""),
        )
    else:
        raise NotImplementedError("Unsupported database type")


def microsoft_dynamics_connection_kwargs(datasource):
    ds = datasource
    config = (ds and ds.get("config")) or {}
    if not config:
        raise ValueError("Unable to find datasource config")
    if ds.get("type") == "erp:microsoft":
        return dict(
            sqlalchemy_driver="mssql+pyodbc",
            hostname=config.get("hostname", ""),
            database=config.get("database", ""),
            backend_driver=config.get("backend_driver", ""),
        )


def get_table_names(engine):
    inspector = inspect(engine)
    return [{"type": "table", "name": t} for t in inspector.get_table_names()] + [
        {"type": "view", "name": v} for v in inspector.get_view_names()
    ]


def get_column_names(engine, table_name):
    metadata = sqlalchemy.MetaData(bind=engine)
    chosen_table = sqlalchemy.Table(table_name, metadata, autoload=True, autoload_with=engine)
    columns = chosen_table.c
    col = []
    for c in columns:
        col.append(c.name)
    return col


def get_example_row(engine, table_name):
    metadata = sqlalchemy.MetaData(bind=engine)
    table = sqlalchemy.Table(table_name, metadata, autoload=True, autoload_with=engine)
    query = sqlalchemy.select([table]).limit(1)
    return [dict(r) for r in engine.execute(query)]


