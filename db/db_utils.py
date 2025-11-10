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

def update_table_cell(connection, table, column, pk_value, new_value, row_values=None, headers=None):
    """
    Update a cell in a table.
    1. If a PK exists, update using it.
    2. If no PK, find a single exact matching row based on all column values.
       - If multiple matches, deny update.
       - If exactly one match, update that row.
    """
    cursor = connection.cursor()

    # Handle empty string as NULL for numeric/date columns
    if new_value == "":
        new_value = None

    # Step 1: Try primary key update
    cursor.execute("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_NAME), 'IsPrimaryKey') = 1
          AND LOWER(TABLE_NAME) = LOWER(?)
    """, (table,))
    pk_row = cursor.fetchone()

    if pk_row:
        pk_col = pk_row[0]  # tuple-safe
        sql = f"UPDATE [{table}] SET [{column}] = ? WHERE [{pk_col}] = ?"
        cursor.execute(sql, (new_value, pk_value))
        connection.commit()
        return cursor.rowcount

    # Step 2: No PK — match row by full content
    if not row_values or not headers:
        raise ValueError("Full row data (row_values, headers) required for non-PK updates")

    # Build WHERE clause from all columns except the one being updated
    where_clauses = []
    params = []
    for col_name, val in zip(headers, row_values):
        if col_name == column:
            continue
        if val is None or val == "":
            where_clauses.append(f"[{col_name}] IS NULL")
        else:
            where_clauses.append(f"[{col_name}] = ?")
            params.append(val)

    where_sql = " AND ".join(where_clauses)
    if not where_sql:
        raise ValueError("Cannot construct WHERE clause for row identification")

    # Ensure only one row matches
    check_sql = f"SELECT COUNT(*) FROM [{table}] WHERE {where_sql}"
    cursor.execute(check_sql, params)
    match_count = cursor.fetchone()[0]

    if match_count == 0:
        raise ValueError("No matching row found — update canceled.")
    elif match_count > 1:
        raise ValueError("Multiple matching rows found — update canceled to avoid ambiguity.")

    # Perform update on that exact row
    update_sql = f"UPDATE [{table}] SET [{column}] = ? WHERE {where_sql}"
    cursor.execute(update_sql, [new_value] + params)
    connection.commit()
    return cursor.rowcount

def bulk_insert(connection, table_name, df, chunk_size=1000, parent=None):
    """
    Insert many rows into a table efficiently using pyodbc.
    Detects invalid type conversions (e.g., string in numeric column) and reports clearly.
    """
    import math
    import pandas as pd
    import numpy as np
    from PyQt5.QtWidgets import QMessageBox

    if df is None or df.empty:
        return 0

    cursor = connection.cursor()
    try:
        # 1️⃣ Get metadata (column names and SQL types)
        cursor.execute(f"SELECT TOP 0 * FROM [{table_name}]")
        desc = cursor.description
        col_meta = {
            d[0]: {
                "type_code": d[1],
                "maxlen": d[3] or d[4] or None,
            }
            for d in desc
        }

        # 2️⃣ Validate and sanitize values
        for col in df.columns:
            meta = col_meta.get(col, {})
            sql_type = meta.get("type_code")
            maxlen = meta.get("maxlen")

            # --- Trim long strings for varchar/nvarchar ---
            if maxlen and maxlen > 0 and df[col].dtype == object:
                df[col] = df[col].astype(str).apply(
                    lambda v: v[:maxlen] if isinstance(v, str) and len(v) > maxlen else v
                )

            # --- Detect numeric columns ---
            # SQL numeric type_codes vary by driver: 4=INT, 3=DECIMAL, 5=FLOAT, -5=BIGINT, etc.
            numeric_codes = {2, 3, 4, 5, 6, 7, -5, -6}
            if sql_type in numeric_codes:
                bad_rows = []
                for idx, v in enumerate(df[col]):
                    if v in (None, "", np.nan):
                        continue
                    try:
                        float(v)
                    except Exception:
                        bad_rows.append((idx + 1, v))

                if bad_rows:
                    examples = ", ".join(f"'{val}' (row {i})" for i, val in bad_rows[:3])
                    msg = (
                        f"❌ Column '{col}' expects numeric data.\n\n"
                        f"Found invalid values: {examples}"
                        + (f"\n… and {len(bad_rows) - 3} more." if len(bad_rows) > 3 else "")
                    )
                    if parent:
                        QMessageBox.critical(parent, "Invalid Data Type", msg)
                    raise ValueError(msg)

        # 3️⃣ Prepare insert query
        columns = ", ".join(f"[{col}]" for col in df.columns)
        placeholders = ", ".join(["?"] * len(df.columns))
        query = f"INSERT INTO [{table_name}] ({columns}) VALUES ({placeholders})"

        values = [
            tuple(None if pd.isna(v) else v for v in row)
            for row in df.to_numpy()
        ]
        total = len(values)
        num_chunks = math.ceil(total / chunk_size)

        # 4️⃣ Execute in chunks
        for i in range(num_chunks):
            chunk = values[i * chunk_size:(i + 1) * chunk_size]
            cursor.fast_executemany = True
            cursor.executemany(query, chunk)

        connection.commit()
        return total

    except Exception as e:
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        # If we already raised a clear message earlier, keep it as-is
        raise

    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass




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

import pandas as pd
import re

def fetch_query_with_pagination(connection, query, page=0, page_size=500):
    """
    Execute any SQL query (including multi-statement batches).
    SELECT queries are paginated; non-SELECT queries execute directly.
    Returns (columns, rows, stats) where stats is a dict with counts.
    """
    import re
    import pandas as pd

    if not query or not query.strip():
        return [], [], {"success": 0, "failed": 0, "total": 0}

    query = query.strip().strip(';').strip('"').strip("'")

    # Split into SQL statements
    statements = [s.strip() for s in re.split(r';\s*(?:\r?\n)+', query) if s.strip()]

    all_columns, all_rows = [], []
    success_count, fail_count = 0, 0

    for stmt in statements:
        # Skip empty/comment-only statements
        if not re.search(r'\w', stmt):
            continue

        # Detect SELECT (ignoring comments)
        is_select = bool(re.match(r'^\s*(?:--[^\n]*\n\s*)*select\b', stmt, flags=re.IGNORECASE))

        if is_select:
            if not re.search(r'\border\s+by\b', stmt, flags=re.IGNORECASE):
                stmt += " ORDER BY (SELECT NULL)"
            paginated = f"{stmt} OFFSET {page * page_size} ROWS FETCH NEXT {page_size} ROWS ONLY"
            print(f"[DEBUG] Running SELECT via pandas:\n{paginated}\n")

            try:
                df = pd.read_sql_query(paginated, connection)
                all_columns = list(df.columns)
                all_rows = df.values.tolist()
                success_count += 1
            except Exception as e:
                print(f"[ERROR] Failed SELECT: {e}")
                fail_count += 1
        else:
            print(f"[DEBUG] Executing non-SELECT SQL directly:\n{stmt}\n")
            cursor = connection.cursor()
            try:
                cursor.execute(stmt)
                connection.commit()
                print(f"[DEBUG] Executed successfully ({cursor.rowcount} rows affected).")
                success_count += 1
            except Exception as e:
                connection.rollback()
                print(f"[ERROR] Failed to execute statement: {e}")
                fail_count += 1
            finally:
                cursor.close()

    stats = {
        "success": success_count,
        "failed": fail_count,
        "total": success_count + fail_count,
    }

    print(f"[INFO] Query batch complete: {stats['success']} succeeded, {stats['failed']} failed.")
    return all_columns, all_rows, stats



def get_table_row_count(connection, table_name):
    """Return total number of rows in a table."""
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    return cursor.fetchone()[0]