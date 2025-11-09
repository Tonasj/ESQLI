class DBController:
    """Thin wrapper around db.db_utils with a bit of state."""

    def __init__(self, conn):
        self.conn = conn
        self.current_db = None
        
        # --- Enable autocommit for DDL operations ---
        try:
            if hasattr(self.conn, "autocommit"):
                self.conn.autocommit = True
            else:
                raw = getattr(self.conn, "connection", None)
                if raw is not None and hasattr(raw, "autocommit"):
                    raw.autocommit = True
        except Exception as e:
            print(f"[WARN] Could not enable autocommit: {e}")

    # -------- DB listing / selection --------
    def fetch_databases(self):
        from db.db_utils import fetch_databases
        return fetch_databases(self.conn)

    def use_database(self, db_name):
        from db.db_utils import use_database
        use_database(self.conn, db_name)
        self.current_db = db_name

    def fetch_tables(self):
        from db.db_utils import fetch_tables
        return fetch_tables(self.conn)

    # -------- Table preview & schema --------
    def fetch_table_preview(self, table_name):
        from db.db_utils import fetch_table_preview
        return fetch_table_preview(self.conn, table_name)

    def fetch_table_schema(self, table_name):
        from db.db_utils import fetch_table_schema
        return fetch_table_schema(self.conn, table_name)

    def add_column(self, table, name, typ):
        from db.db_utils import add_column
        return add_column(self.conn, table, name, typ)

    def rename_column(self, table, old, new):
        from db.db_utils import rename_column
        return rename_column(self.conn, table, old, new)

    def alter_column_type(self, table, column, new_type):
        from db.db_utils import alter_column_type
        return alter_column_type(self.conn, table, column, new_type)
    
    def set_primary_key(self, table, column, enabled):
        from db.db_utils import set_primary_key
        return set_primary_key(self.conn, table, column, enabled)

    def set_auto_increment(self, table, column, enabled):
        from db.db_utils import set_auto_increment
        return set_auto_increment(self.conn, table, column, enabled)
    
    def set_nullable(self, table, column, enabled):
        from db.db_utils import set_nullable
        return set_nullable(self.conn, table, column, enabled)
    
    def fetch_column_info(self, table_name, column_name):
        from db.db_utils import fetch_column_info
        return fetch_column_info(self.conn, table_name, column_name)

    def update_table_cell(self, table, column, pk_value, new_value, row_values=None, headers=None):
        from db.db_utils import update_table_cell
        return update_table_cell(self.conn, table, column, pk_value, new_value, row_values, headers)

    # -------- DDL --------
    def create_table(self, name, columns):
        from db.db_utils import create_table
        return create_table(self.conn, name, columns)

    def create_database(self, name):
        from db.db_utils import create_database
        return create_database(self.conn, name)
    
    def add_table_item(self, table, values):
        from db.db_utils import insert_row
        return insert_row(self.conn, table, values)

    # -------- Query --------
    def fetch_query_with_pagination(self, query, page, page_size):
        from db.db_utils import fetch_query_with_pagination
        return fetch_query_with_pagination(self.conn, query, page, page_size)