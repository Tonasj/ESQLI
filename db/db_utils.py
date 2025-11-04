import sys

def fetch_databases(connection):
    """Return a list of database names."""
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sys.databases ORDER BY name")
    return [row[0] for row in cursor.fetchall()]

def fetch_tables(connection):
    """Return a list of table names in the current database."""
    cursor = connection.cursor()
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
    return [row[0] for row in cursor.fetchall()]

def use_database(connection, database_name):
    """Switch context to a specific database."""
    cursor = connection.cursor()
    cursor.execute(f"USE [{database_name}]")

def fetch_table_schema(connection, table_name):
    """Return (column_name, data_type) for a given table."""
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT COLUMN_NAME, DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}'
    """)
    return cursor.fetchall()

def fetch_table_preview(connection, table_name, limit=50):
    """Return up to `limit` rows and column names from a table."""
    cursor = connection.cursor()
    cursor.execute(f"SELECT TOP {limit} * FROM [{table_name}]")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return columns, rows

def create_table(connection, table_name, columns):
    """Create a table with the given name and [(col, type)] definition."""
    col_defs = ", ".join([f"[{n}] {t}" for n, t in columns])
    query = f"CREATE TABLE [{table_name}] ({col_defs})"
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()

def create_database(connection, db_name):
    """Create a new database and ensure autocommit where required."""
    cursor = connection.cursor()
    autocommit_attr = getattr(connection, "autocommit", None)
    previous_autocommit = None
    if autocommit_attr is not None:
        previous_autocommit = connection.autocommit
        if not previous_autocommit:
            connection.autocommit = True
    cursor.execute(f"CREATE DATABASE [{db_name}]")
    if autocommit_attr is None:
        try:
            connection.commit()
        except Exception:
            pass
    if previous_autocommit is not None:
        connection.autocommit = previous_autocommit

def add_column(connection, table_name, column_name, column_type):
    """ALTER TABLE to add a new column."""
    cursor = connection.cursor()
    cursor.execute(f"ALTER TABLE [{table_name}] ADD [{column_name}] {column_type}")
    connection.commit()

def rename_column(connection, table_name, old_name, new_name):
    """Rename a column in a table using sp_rename."""
    cursor = connection.cursor()
    cursor.execute(
        f"EXEC sp_rename '{table_name}.{old_name}', '{new_name}', 'COLUMN'"
    )
    connection.commit()

def alter_column_type(connection, table_name, column_name, new_type):
    """Change a column's data type using ALTER TABLE."""
    cursor = connection.cursor()
    cursor.execute(
        f"ALTER TABLE [{table_name}] ALTER COLUMN [{column_name}] {new_type}"
    )
    connection.commit()

def execute_custom_query(connection, query):
    """Execute a custom SQL query and return column names and rows if applicable."""
    cursor = connection.cursor()
    cursor.execute(query)

    try:
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall() if columns else []
    except Exception:
        columns, rows = [], []

    connection.commit()
    return columns, rows
