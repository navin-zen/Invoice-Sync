import json
import logging

import sqlalchemy
from django.utils import timezone
from einvoicing.utils.datasource.databases import create_engine
from einvoicing.utils.settings import SettingsInfo
from sqlalchemy import *  # NOQA
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Some other example server values are
# server = 'localhost\sqlexpress' # for a named instance
# server = 'myserver,port' # to specify an alternate port
r"""server = "LAPTOP-JOQ41STM\GSTZENSQL"
database = "GSTZen"
username = "sa"
password = "gstzen123"
DRIVER = "ODBC Driver 17 for SQL Server"
DATABASE_CONNECTION = f"mssql://{username}:{password}@{server}/{database}?driver={DRIVER}"
"""
# this engine is for mssql server
# engine = create_engine(DATABASE_CONNECTION)

# this engine is for sqlite3
engine = create_engine(
    "sqlite:///C:\\Users\\Srivatsa B\\Downloads\\sqlite-tools-win32-x86-3310100\\sqlite-tools-win32-x86-3310100\\testdatabase.db"
)
metadata = MetaData(bind=engine)
Session = sessionmaker(bind=engine)
session = Session()

"""conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER="
    + server
    + ";DATABASE="
    + database
    + ";UID="
    + username
    + ";PWD="
    + password
)
"""

#  cursor = conn.cursor()


class CheckDBConnection:
    def check_datasource():
        """
        Check datasource and save connection status in DB
        """
        si = SettingsInfo()
        datasource = si.datasource_settings
        config = datasource.get("config", {})
        hostname = config.get("hostname", "")
        database = config.get("database", "")
        port = config.get("port", None)
        username = config.get("username", "")
        password = config.get("password", "")
        database_driver = config.get("database_driver", "")
        print("going inside the function")
        status = CustomDatabase.test_sqlalchemy_connection(
            hostname, database, port, username, password, database_driver
        )
        print(status)
        datasource["status"] = status
        # gc.metadata["datasource"] = datasource
        # gc.save()


class CustomDatabase:
    @classmethod
    def test_sqlalchemy_connection(cls, hostname, database, port, username, password, driver=None):
        query = {}
        if driver:
            query = {"driver": driver}
        url = sqlalchemy.engine.url.URL(
            drivername="mssql+pyodbc",
            username=username,
            password=password,
            host=hostname,
            database=database,
            query=query,
        )
        logger.info(f"Sqlalchemy connection: URL: {url}")
        engine = create_engine(url, connect_args={"connect_timeout": 5})
        logger.info(f"Sqlalchemy connection: Engine: {engine}")

        message = ""
        try:
            connection = engine.connect()  # NOQA
            return {
                "status": 1,
                "message": "connection success",
                "timestamp": timezone.now().isoformat(),
            }
        except Exception as ex:
            message = str(ex)
        return {
            "status": 0,
            "message": message,
            "timestamp": timezone.now().isoformat(),
        }

    @classmethod
    def get_sqlserver_table_data(cls):
        result = engine.execute("select * from Invoice_Table for json auto")
        print(result)
        for data in result:
            print("".join(data))

    # @classmethod
    # def insert_into_sqlserver_database(cls):
    #     cursor.execute("insert into Invoice_Table values('Srivatsa',11/12/1998)")
    #     conn.commit()

    @classmethod
    def update_sqlserver_database(cls):
        update_statement = "update Invoice_Table set Name='Srini' where Invoice_Type='Regular'"
        engine.execute(update_statement)
        cls.get_sqlserver_table_data()

    @classmethod
    def display_tables_in_database(cls):
        for table_name in engine.table_names():
            print(table_name)

    @classmethod
    def display_all_columns_in_table(cls, table_name):
        result = engine.execute("select * from Invoice_Table")
        for column_name in result.keys():
            print(column_name)

    @classmethod
    def test_sql_alchemy(cls):
        connection = engine.connect()
        print(engine.table_names())
        connection = engine.connect()
        result = connection.execute("select * from Invoice_Table for json auto")
        for row in result:
            print("".join(row))
        connection.close()

    @classmethod
    def get_sqlite_tables(cls):
        for table_name in engine.table_names():
            print(table_name)

    @classmethod
    def get_sqlite_columns_of_table(cls):
        result = engine.execute("select * from employee")
        for column_name in result.keys():
            print(column_name)
        employee = Table("employee", metadata, autoload=True)
        for col in employee.columns:
            print(col.name, col.type)

    # @classmethod
    # def get_sqlite_table_data(cls):
    #     employee = Table("employee", metadata, autoload=True)
    #     select_query = select([employee])
    #     data = engine.execute(select_query)
    #     for x in data:
    #         print(x)

    @classmethod
    def table_join(cls):
        employee = Table("employee", metadata, autoload=True)
        department = Table("department", metadata, autoload=True)
        print(session.query(employee).join(department))
        result = session.query(department).join(employee)
        for row in result:
            print(row)

    @classmethod
    def display_json_form_data(cls):
        with open("../config.json") as json_file:
            json.load(json_file)

    # commented code
    # engine = create_engine('mssql+pyodbc://scott:tiger@mydsn')
    # database_connection = f'mssql://sa:gstzen123@GSTZen?driver={DRIVER}'
    # db = create_engine("mssql+pyodbc://sa:gstzen123@172.28.128.1?driver=ODBC+Driver+17+for+SQL+Server")
    # print(metadata)
