import cx_Oracle

# Replace these values
username = "system"
password = "system"
#dsn = cx_Oracle.makedsn("SERVER-CCVDY63", 1521, service_name="kopttestfin")
dsn = cx_Oracle.makedsn("192.168.4.62", 1521, service_name="kopttestfin")
cx_Oracle.init_oracle_client(lib_dir=r"C:\oracle\instantclient_21\instantclient_23_0")

try:
    # Connect
    conn = cx_Oracle.connect(username, password, dsn)
    print("✅ Connected to Oracle")

    cursor = conn.cursor()

    # IMPORTANT: Use SCHEMA.TABLE_NAME
    query = """
        SELECT *
        FROM FINANCE.FI_PN_MH_OLDBILL_PARAM
        WHERE EMP_CD='46000'
    """

    cursor.execute(query)

    for row in cursor:
        print(row)

    cursor.close()
    conn.close()

except Exception as e:
    print("❌ Error:", e)