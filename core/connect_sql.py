import pyodbc

def connect_to_sql(host, database="master", username=None, password=None,
                   driver="{ODBC Driver 17 for SQL Server}", use_windows_auth=False):
    """
    Connect to a SQL Server instance using either SQL or Windows Authentication.

    :param host: Server address (e.g. localhost\\SQLEXPRESS)
    :param database: Database name (default is master)
    :param username: SQL login username (ignored if using Windows Auth)
    :param password: SQL login password (ignored if using Windows Auth)
    :param driver: ODBC driver name
    :param use_windows_auth: Boolean indicating whether to use Windows Authentication
    :return: pyodbc.Connection object
    :raises: pyodbc.Error on failure
    """
    if not host:
        raise ValueError("Empty host address")

    if host == "localhost":
        host = "localhost\\SQLEXPRESS"

    if use_windows_auth:
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={host};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
    else:
        if not username or not password:
            raise ValueError("Username and password required for SQL Authentication")
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={host};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

    try:
        print(f"Connecting to SQL Server at {host}, DB: {database}")
        conn = pyodbc.connect(conn_str)
        print("Connection successful.")
        return conn
    except pyodbc.Error as e:
        raise RuntimeError(f"Connection failed: {e}")
