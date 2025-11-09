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
    """
    Return a list of (column_name, data_type, is_primary_key, is_identity, is_nullable)
    for the given table (SQL Server compatible).
    """
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT 
            c.COLUMN_NAME,
            c.DATA_TYPE,
            CASE WHEN kcu.COLUMN_NAME IS NOT NULL THEN 1 ELSE 0 END AS is_primary,
            COLUMNPROPERTY(OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME), c.COLUMN_NAME, 'IsIdentity') AS is_identity,
            c.IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
            ON c.TABLE_NAME = kcu.TABLE_NAME
            AND c.COLUMN_NAME = kcu.COLUMN_NAME
            AND kcu.CONSTRAINT_NAME IN (
                SELECT CONSTRAINT_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                WHERE CONSTRAINT_TYPE = 'PRIMARY KEY'
            )
        WHERE c.TABLE_NAME = ?
        ORDER BY c.ORDINAL_POSITION
    """, (table_name,))

    # Normalize and return as tuple list
    result = []
    for row in cursor.fetchall():
        col_name = row.COLUMN_NAME
        data_type = row.DATA_TYPE
        is_primary = bool(row.is_primary)
        is_identity = bool(row.is_identity)
        is_nullable = (str(row.IS_NULLABLE).upper() == "YES")
        result.append((col_name, data_type, is_primary, is_identity, is_nullable))
    return result

def fetch_table_preview(connection, table_name, limit=50):
    """Return up to `limit` rows and column names from a table."""
    cursor = connection.cursor()
    cursor.execute(f"SELECT TOP {limit} * FROM [{table_name}]")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return columns, rows

def create_table(connection, table_name, columns):
    """
    Create a table with columns defined as:
    [(name, type, is_primary, is_identity, is_nullable)]
    """
    col_defs = []
    pk_col = None

    for name, col_type, is_primary, is_identity, is_nullable in columns:
        parts = [f"[{name}] {col_type}"]

        if is_identity:
            parts.append("IDENTITY(1,1)")
        if not is_nullable or is_primary:
            parts.append("NOT NULL")
        if is_primary:
            pk_col = name

        col_defs.append(" ".join(parts))

    if pk_col:
        col_defs.append(f"PRIMARY KEY ([{pk_col}])")

    query = f"CREATE TABLE [{table_name}] ({', '.join(col_defs)})"
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

def fetch_column_info(connection, table_name, column_name):
    """Return column metadata: name, type, nullability, etc."""
    cursor = connection.cursor()
    cursor.execute(f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
    """, (table_name, column_name))
    row = cursor.fetchone()
    if row:
        return {"name": row[0], "data_type": row[1], "is_nullable": row[2]}
    return None

def add_column(connection, table_name, column_name, column_type):
    """ALTER TABLE to add a new column."""
    cursor = connection.cursor()
    cursor.execute(f"ALTER TABLE [{table_name}] ADD [{column_name}] {column_type}")
    connection.commit()

def insert_row(connection, table_name, values):
    """Insert a new row into the given table."""
    escaped_cols = ", ".join(f"[{c}]" for c in values.keys())
    placeholders = ", ".join(["?" for _ in values])
    cursor = connection.cursor()
    query = f"INSERT INTO [{table_name}] ({escaped_cols}) VALUES ({placeholders})"
    cursor.execute(query, list(values.values()))
    connection.commit()

def update_table_cell(connection, table, column, pk_value, new_value):
    """
    Update a single cell identified by the table's primary key if present.
    If no PK exists, fall back to updating by row number order.
    """
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_NAME), 'IsPrimaryKey') = 1
          AND TABLE_NAME = ?
    """, (table,))
    pk_row = cursor.fetchone()

    if pk_row:
        pk_col = pk_row.COLUMN_NAME
        sql = f"UPDATE [{table}] SET [{column}] = ? WHERE [{pk_col}] = ?"
        cursor.execute(sql, (new_value, pk_value))
    else:
        # No PK: fall back to ROW_NUMBER()-based subquery update
        sql = f"""
            WITH Ordered AS (
                SELECT *, ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS rn
                FROM [{table}]
            )
            UPDATE Ordered
            SET [{column}] = ?
            WHERE rn = ?
        """
        # pk_value here is actually our row index (0-based in UI)
        cursor.execute(sql, (new_value, int(pk_value) + 1))

    connection.commit()



def rename_column(connection, table_name, old_name, new_name):
    """Rename a column in a table using sp_rename."""
    cursor = connection.cursor()
    cursor.execute(
        f"EXEC sp_rename '[{table_name}].[{old_name}]', '{new_name}', 'COLUMN'"
    )
    connection.commit()

def alter_column_type(connection, table_name, column_name, new_type):
    """Change a column's data type using ALTER TABLE."""
    cursor = connection.cursor()
    cursor.execute(
        f"ALTER TABLE [{table_name}] ALTER COLUMN [{column_name}] {new_type}"
    )
    connection.commit()

def set_primary_key(connection, table, column, enabled):
    cursor = connection.cursor()
    if enabled:
        # Ensure column is NOT NULL
        cursor.execute(f"ALTER TABLE [{table}] ALTER COLUMN [{column}] INT NOT NULL;")
        # Then add primary key constraint
        cursor.execute(f"ALTER TABLE [{table}] ADD CONSTRAINT [PK_{table}_{column}] PRIMARY KEY ([{column}])")
    else:
        cursor.execute(f"ALTER TABLE [{table}] DROP CONSTRAINT [PK_{table}_{column}]")
    connection.commit()

def set_auto_increment(connection, table, column, enabled):
    """
    Enable or disable IDENTITY (auto-increment) for a column in SQL Server.

    Because SQL Server doesn't support direct toggling of IDENTITY,
    this recreates the column safely.
    """
    cursor = connection.cursor()
    try: 
        cursor.execute("BEGIN TRAN")
        # Step 1: Get current column definition
        cursor.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, COLUMN_DEFAULT, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
        """, (table, column))
        col_info = cursor.fetchone()
        if not col_info:
            raise ValueError(f"Column '{column}' not found in table '{table}'")

        col_name, data_type, char_len, default_val, is_nullable = col_info

        # Ensure only INT/BIGINT can be IDENTITY
        if "INT" not in data_type.upper():
            raise ValueError(f"Auto-increment is only valid for INT columns (got {data_type})")

        # Step 2: Check if column already is identity
        cursor.execute(f"""
            SELECT COLUMNPROPERTY(OBJECT_ID(?), ?, 'IsIdentity')
        """, (table, column))
        is_identity = cursor.fetchone()[0] == 1

        if enabled and is_identity:
            return  # nothing to do
        if not enabled and not is_identity:
            return  # nothing to do

        # Step 3: Build temporary column
        temp_col = f"{column}_temp"

        # Step 4: Create a temporary column with or without IDENTITY
        length_clause = f"({char_len})" if char_len and data_type.upper() in ("VARCHAR", "CHAR", "NVARCHAR") else ""
        identity_clause = "IDENTITY(1,1)" if enabled else ""
        null_clause = "NOT NULL"

        cursor.execute(f"""
            ALTER TABLE [{table}] ADD [{temp_col}] {data_type}{length_clause} {identity_clause} {null_clause}
        """)

        # Step 5: Copy existing data
        # (We can't insert explicit identity values unless IDENTITY_INSERT is ON)
        if not enabled:
            # Copy values from the old identity column to the new plain one
            cursor.execute(f"UPDATE [{table}] SET [{temp_col}] = [{column}]")
        else:
            # Recreating as identity: values will auto-generate
            pass

        # Step 6: Drop constraints and old column, then rename
        cursor.execute(f"ALTER TABLE [{table}] DROP COLUMN [{column}]")
        cursor.execute(f"EXEC sp_rename '[{table}].[{temp_col}]', '{column}', 'COLUMN'")

        connection.commit()
    except Exception as e:
        cursor.execute("ROLLBACK TRAN")
        connection.rollback()
        raise

def set_nullable(connection, table, column, enabled):
    """
    Toggle a column's NULL / NOT NULL constraint for SQL Server safely.
    Drops default constraints if necessary and reuses correct type metadata.
    """
    cursor = connection.cursor()
    try:
        # 1. Drop any default constraint bound to the column
        cursor.execute(f"""
            DECLARE @sql NVARCHAR(4000);
            SELECT @sql = N'ALTER TABLE [' + OBJECT_NAME(parent_object_id) +
                          '] DROP CONSTRAINT [' + name + ']'
            FROM sys.default_constraints
            WHERE parent_object_id = OBJECT_ID('[{table}]')
              AND COL_NAME(parent_object_id, parent_column_id) = '{column}';
            IF @sql IS NOT NULL EXEC sp_executesql @sql;
        """)

        # 2. Lookup full data type info
        cursor.execute(f"""
            SELECT DATA_TYPE,
                   CHARACTER_MAXIMUM_LENGTH,
                   NUMERIC_PRECISION,
                   NUMERIC_SCALE,
                   COLLATION_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table}' AND COLUMN_NAME = '{column}';
        """)
        row = cursor.fetchone()
        if not row:
            raise Exception(f"Column {column} not found in table {table}.")

        data_type, char_len, precision, scale, collation = row

        if data_type.upper() in ("CHAR", "NCHAR", "VARCHAR", "NVARCHAR"):
            type_decl = f"{data_type}({char_len if char_len != -1 else 'MAX'})"
        elif data_type.upper() in ("DECIMAL", "NUMERIC"):
            type_decl = f"{data_type}({precision},{scale})"
        else:
            type_decl = data_type

        if collation and data_type.upper() in ("CHAR", "NCHAR", "VARCHAR", "NVARCHAR"):
            type_decl += f" COLLATE {collation}"

        null_clause = "NULL" if enabled else "NOT NULL"

        # 3. Execute the ALTER with proper type definition
        sql = f"ALTER TABLE [{table}] ALTER COLUMN [{column}] {type_decl} {null_clause};"
        cursor.execute(sql)

        # 4. Commit safely (force autocommit if needed)
        try:
            connection.commit()
        except Exception:
            if hasattr(connection, "autocommit"):
                connection.autocommit = True
                cursor.execute(sql)
    except Exception as e:
        connection.rollback()
        raise
    finally:
        cursor.close()



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