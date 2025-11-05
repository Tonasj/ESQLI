class DBController:
    """Thin wrapper around db.db_utils with a bit of state."""

    def __init__(self, conn):
        self.conn = conn
        self.current_db = None

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

    # -------- DDL --------
    def create_table(self, name, columns):
        from db.db_utils import create_table
        return create_table(self.conn, name, columns)

    def create_database(self, name):
        from db.db_utils import create_database
        return create_database(self.conn, name)

    # -------- Query --------
    def fetch_query_with_pagination(self, query, page, page_size):
        from db.db_utils import fetch_query_with_pagination
        return fetch_query_with_pagination(self.conn, query, page, page_size)