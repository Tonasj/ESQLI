import sys
import re
import pandas as pd

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

def fetch_full_table_paginated(connection, table_name, chunk_size=10000):
    """Generator that yields rows from a table in chunks."""
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    total_rows = cursor.fetchone()[0]
    if total_rows == 0:
        return [], []

    cursor.execute(f"SELECT TOP 0 * FROM [{table_name}]")
    columns = [desc[0] for desc in cursor.description]

    offset = 0
    while offset < total_rows:
        query = f"""
            SELECT * FROM [{table_name}]
            ORDER BY (SELECT NULL)
            OFFSET {offset} ROWS FETCH NEXT {chunk_size} ROWS ONLY;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows:
            break
        yield columns, rows
        offset += len(rows)

def fetch_query_with_pagination(connection, query, page=0, page_size=500):
    """
    Execute a SQL query with proper pagination.
    Applies OFFSET/FETCH to the final SELECT statement only.
    Compatible with SQL Server, and ignores USE/COMMENT lines.
    """
    cursor = connection.cursor()
    query = query.strip()

    # Normalize spacing and strip trailing semicolons/newlines
    query = re.sub(r'\s+', ' ', query).strip().rstrip(';')

    # Find last SELECT statement (ignoring comments and USE)
    select_match = re.search(r'(select\b.*)$', query, flags=re.IGNORECASE)
    if not select_match:
        print("[DEBUG] No SELECT statement found; executing raw query.")
        cursor.execute(query)
        rows = cursor.fetchall() if cursor.description else []
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        connection.commit()
        return columns, rows

    # Split into "before SELECT" and "SELECT part"
    before_select = query[:select_match.start()].strip()
    select_stmt = select_match.group(1).strip()

    # Add ORDER BY if missing
    if re.search(r'\border\s+by\b', select_stmt, flags=re.IGNORECASE):
        paginated_select = (
            f"{select_stmt} OFFSET {page * page_size} ROWS FETCH NEXT {page_size} ROWS ONLY"
        )
    else:
        paginated_select = (
            f"{select_stmt} ORDER BY (SELECT NULL) OFFSET {page * page_size} ROWS FETCH NEXT {page_size} ROWS ONLY"
        )

    # Combine back into one runnable SQL batch
    final_query = before_select + "\n" + paginated_select if before_select else paginated_select

    print(f"[DEBUG] Running paginated SQL:\n{final_query}\n")

    cursor.execute(final_query)

    columns, rows = [], []
    # Handle multi-result sets
    while True:
        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            break
        if not cursor.nextset():
            break

    connection.commit()
    return columns, rows


def get_table_row_count(connection, table_name):
    """Return total number of rows in a table."""
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    return cursor.fetchone()[0]