import cx_Oracle
from django.conf import settings

cx_Oracle.init_oracle_client(lib_dir=r"C:\oracle\instantclient_21\instantclient_23_0")

def get_oracle_connection():
    conf = settings.ORACLE_DB

    dsn = cx_Oracle.makedsn(
        conf["HOST"],
        conf["PORT"],
        service_name=conf["SERVICE_NAME"]
    )

    conn = cx_Oracle.connect(
        conf["USER"],
        conf["PASSWORD"],
        dsn
    )

    return conn