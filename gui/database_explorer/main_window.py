from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QMessageBox, 
    QPushButton, QHBoxLayout, QDesktopWidget, QSizePolicy
)
from PyQt5.QtCore import Qt

from gui.integrated_console import IntegratedConsole, redirect_std
from gui.window_utils import setup_app_settings, restore_window_settings, save_window_settings

from .tree_panel import DatabaseTreePanel
from .table_designer import TableDesignerPanel
from .query_editor import QueryEditorPanel
from .data_preview import DataPreviewPanel
from .controller import DBController


class DatabaseExplorerWindow(QWidget):
    """High-level orchestration; delegates to panels and DB controller."""

    def __init__(self, connection=None, database=None, connection_window=None):
        super().__init__()
        self.controller = DBController(connection)
        self.connection_window = connection_window
        self.gui_settings, self.app_settings = setup_app_settings()

        self.selected_database = database
        self.current_table = None
        self.last_table_preview = None
        self.last_query_results = None
        self.last_executed_query = None
        self.current_mode = "table"   # <--- new mode tracker

        self.setWindowTitle(
            f"Database Explorer - {database}" if database else "Database Explorer"
        )

        self._build_ui()
        self._connect_signals()

        redirect_std(self.console)
        restore_window_settings(self)

        if self.controller.conn and not self.selected_database:
            self._show_database_list()
        elif self.controller.conn and self.selected_database:
            self._enter_database(self.selected_database)

    # ---------------- UI ----------------
    def _build_ui(self):
        self.setWindowTitle(f"Database Explorer - {self.selected_database or ''}".strip() or "Database Explorer")
        self.resize(1200, 700)
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # --- Main vertical splitter (top + bottom) ---
        self.main_splitter = QSplitter(Qt.Vertical)

        # ---------------- TOP SPLIT ----------------
        self.top_splitter = QSplitter(Qt.Horizontal)

        # ---- Left: Tree + Disconnect ----
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 5)
        left_layout.setSpacing(4)

        self.back_btn = QPushButton("⛓️‍💥 Disconnect from Server")
        left_layout.addWidget(self.back_btn)

        self.tree_panel = DatabaseTreePanel()
        left_layout.addWidget(self.tree_panel, 1)

        self.top_splitter.addWidget(self.left_panel)

        # ---- Right: Table/Query area ----
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 5) 
        right_layout.setSpacing(4)

        # Mode buttons (Table / Query)
        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(5, 0, 0, 0) 
        self.table_mode_btn = QPushButton("Table")
        self.query_mode_btn = QPushButton("Query")
        self.table_mode_btn.setCheckable(True)
        self.query_mode_btn.setCheckable(True)
        self.table_mode_btn.setChecked(True)
        mode_layout.addWidget(self.table_mode_btn)
        mode_layout.addWidget(self.query_mode_btn)
        mode_layout.addStretch()
        right_layout.addLayout(mode_layout)

        # Button styles
        for btn in (self.back_btn, self.table_mode_btn, self.query_mode_btn):
            btn.setMinimumHeight(18)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 4px 10px;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    background: #f5f5f5;
                }
                QPushButton:checked {
                    background: #d0e1ff;
                    border: 1px solid #5a8dee;
                }
                QPushButton:hover {
                    background: #e8e8e8;
                }
            """)
        # Panels (stacked)
        self.table_panel = TableDesignerPanel()
        self.query_panel = QueryEditorPanel()
        self.query_panel.hide()
        right_layout.addWidget(self.table_panel)
        right_layout.addWidget(self.query_panel)

        self.top_splitter.addWidget(self.right_panel)
        self.top_splitter.setStretchFactor(0, 1)
        self.top_splitter.setStretchFactor(1, 3)

        # ---------------- BOTTOM SPLIT ----------------
        self.bottom_splitter = QSplitter(Qt.Vertical)
        self.data_panel = DataPreviewPanel()
        self.console = IntegratedConsole()

        self.bottom_splitter.addWidget(self.data_panel)
        self.bottom_splitter.addWidget(self.console)
        self.bottom_splitter.setStretchFactor(0, 4)
        self.bottom_splitter.setStretchFactor(1, 1)
        self.bottom_splitter.setSizes([400, 200])

        # ---- Combine splits ----
        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.bottom_splitter)
        self.main_splitter.setStretchFactor(0, 3)
        self.main_splitter.setStretchFactor(1, 2)

        # ---- Style the main splitter handle ----
        self.main_splitter.setObjectName("mainSplitter")
        self.main_splitter.setStyleSheet("""
            QSplitter#mainSplitter::handle {
                background-color: #bbb;
                height: 1px;
            }
        """)

        root.addWidget(self.main_splitter)


    def _connect_signals(self):
        # --- existing signals ---
        self.tree_panel.databaseSelected.connect(self._enter_database)
        self.tree_panel.tableSelected.connect(self._open_table)
        self.tree_panel.requestAddDatabase.connect(self._add_database)
        self.tree_panel.requestAddTable.connect(self._add_table)

        self.table_panel.addColumnRequested.connect(self._add_column)
        self.table_panel.renameColumnRequested.connect(self._rename_column)
        self.table_panel.changeTypeRequested.connect(self._alter_column_type)

        self.query_panel.runQueryRequested.connect(self._run_query)
        self.query_panel.openCommonQueriesRequested.connect(self._open_common_queries)

        self.data_panel.exportCurrentRequested.connect(self._export_current)
        self.data_panel.exportFullTableRequested.connect(self._export_full_table)
        self.data_panel.exportFullQueryRequested.connect(self._export_full_query)
        self.data_panel.pageChangeRequested.connect(self._change_query_page)

        self.back_btn.clicked.connect(self._handle_back_button)

        # --- NEW: mode toggle buttons ---
        self.table_mode_btn.clicked.connect(lambda: self._switch_mode("table"))
        self.query_mode_btn.clicked.connect(lambda: self._switch_mode("query"))

    # ---------------- Mode switching ----------------
    def _switch_mode(self, mode: str):
        if mode == self.current_mode:
            return

        self.current_mode = mode
        self.table_mode_btn.setChecked(mode == "table")
        self.query_mode_btn.setChecked(mode == "query")

        if mode == "table":
            self.query_panel.hide()
            self.table_panel.show()
            if self.last_table_preview:
                cols, rows, label = self.last_table_preview
                self.data_panel.show_table_data(columns=cols, rows=rows, label=label)
        else:
            self.table_panel.hide()
            self.query_panel.show()
            if self.last_query_results:
                cols, rows, query, page, size = self.last_query_results
                self.data_panel.show_query_results(cols, rows, page, size)
            if self.selected_database:
                tables = self.controller.fetch_tables()
                self.query_panel.set_context(
                    db_name=self.selected_database,
                    table_name=self.current_table,
                    tables=tables,
                )

        (self.query_panel if mode == "query" else self.table_panel).setFocus()

    # ---------------- Tree / Navigation ----------------
    def _show_database_list(self):
        try:
            dbs = self.controller.fetch_databases()
            self.tree_panel.show_databases(dbs)
            self.back_btn.setVisible(True)
            self.back_btn.setText("⛓️‍💥 Disconnect from Server")
            self.selected_database = None
            self.current_table = None
            self.setWindowTitle("Database Explorer")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load databases:\n{e}")

    def _enter_database(self, db_name: str):
        try:
            self.controller.use_database(db_name)
            self.selected_database = db_name
            self.setWindowTitle(f"Database Explorer - {db_name}")

            tables = self.controller.fetch_tables()
            self.tree_panel.show_database_objects(tables)

            # Update query context
            self.query_panel.set_context(db_name=db_name, table_name=None, tables=tables)

            self.back_btn.setVisible(True)
            self.back_btn.setText("⬅️ Return to Databases")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load database '{db_name}':\n{e}")

    def _open_table(self, table_name: str):
        if self.current_mode != "table":
            self._switch_mode("table")
        self.current_table = table_name
        try:
            # Preview
            cols, rows = self.controller.fetch_table_preview(table_name)
            self.last_table_preview = (cols, rows, table_name)
            self.data_panel.show_table_data(columns=cols, rows=rows, label=table_name)

            # Schema into designer
            schema = self.controller.fetch_table_schema(table_name)  # list[(name, type)]
            self.table_panel.load_schema(schema)

            # Update query context
            tables = self.controller.fetch_tables()
            self.query_panel.set_context(
                db_name=self.selected_database, table_name=table_name, tables=tables
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load table:\n{e}")

    # ---------------- Table Designer actions ----------------
    def _add_column(self, name: str, col_type: str):
        if not self.current_table:
            QMessageBox.warning(self, "No Table", "Open a table first.")
            return
        try:
            self.controller.add_column(self.current_table, name, col_type)
            QMessageBox.information(self, "Success", f"Column '{name}' added.")
            self._open_table(self.current_table)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add column:\n{e}")

    def _rename_column(self, old: str, new: str):
        if not self.current_table or not new or new == old:
            return
        confirm = QMessageBox.question(
            self, "Rename Column",
            f"Rename column '{old}' to '{new}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.No:
            return
        try:
            self.controller.rename_column(self.current_table, old, new)
            QMessageBox.information(self, "Success", f"Column renamed to '{new}'.")
            self._open_table(self.current_table)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename column:\n{e}")

    def _alter_column_type(self, column: str, new_type: str):
        if not self.current_table:
            return
        confirm = QMessageBox.question(
            self, "Change Column Type",
            f"Change column '{column}' to type {new_type}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.No:
            return
        try:
            self.controller.alter_column_type(self.current_table, column, new_type)
            QMessageBox.information(self, "Success", f"Column '{column}' type changed to {new_type}.")
            self._open_table(self.current_table)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to alter column:\n{e}")

    def _add_table(self):
        from gui.dialog import AddNewDialog
        dialog = AddNewDialog(self, mode="table")
        if dialog.exec_() == dialog.Accepted:
            name, columns = dialog.get_table_definition()
            if not name or not columns:
                QMessageBox.warning(self, "Invalid input", "Specify name and at least one column.")
                return
            try:
                self.controller.create_table(name, columns)
                QMessageBox.information(self, "Success", f"Table '{name}' created.")
                self._enter_database(self.selected_database)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create table:\n{e}")

    def _add_database(self):
        from gui.dialog import AddNewDialog
        dialog = AddNewDialog(self, mode="database")
        if dialog.exec_() == dialog.Accepted:
            db_name = dialog.get_database_name()
            if not db_name:
                QMessageBox.warning(self, "Invalid input", "Please specify a database name.")
                return
            try:
                self.controller.create_database(db_name)
                QMessageBox.information(self, "Success", f"Database '{db_name}' created.")
                self._show_database_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create database:\n{e}")

    # ---------------- Query actions ----------------
    def _run_query(self, query: str, page: int, page_size: int):
        if not query.strip():
            self.query_panel.show_message("⚠️ Please enter a SQL query to run.", kind="warn")
            return
        try:
            columns, rows = self.controller.fetch_query_with_pagination(query, page, page_size)
            self.last_executed_query = query
            self.last_query_results = (columns, rows, query, page, page_size)

            if columns:
                self.data_panel.show_query_results(columns, rows, page, page_size, query)
                self.query_panel.show_message(
                    f"✅ Showing rows {page*page_size+1}–{page*page_size+len(rows)} (page {page+1})",
                    kind="ok",
                )
            else:
                self.data_panel.clear()
                self.query_panel.show_message("✅ Query executed successfully (no result to show).", kind="ok")
        except Exception as e:
            self.query_panel.show_message(f"❌ Failed to execute query: {e}", kind="err")

    def _change_query_page(self, new_page: int, page_size: int):
        if not self.last_query_results:
            return
        _, _, query, _, _ = self.last_query_results
        self._run_query(query, new_page, page_size)

    # ---------------- Export actions ----------------
    def _export_current(self, headers, rows, label):
        from core.export_utils import export_data_to_file
        # Convert rows + headers into list of dicts
        data = [dict(zip(headers, r)) for r in rows]
        export_data_to_file(self, data, headers, label)

    def _export_full_table(self, table_name):
        from core.export_utils import export_paginated_data
        from db.db_utils import fetch_full_table_paginated
        export_paginated_data(self, fetch_full_table_paginated, table_name)

    def _export_full_query(self, _ignored_query):
        """Export using the last executed query, not the current editor contents."""
        from core.export_utils import export_paginated_data
        from db.db_utils import fetch_query_with_pagination
        query = self.last_executed_query
        if not query or not query.strip():
            QMessageBox.warning(self, "No Query", "Run a query before exporting.")
            return

        export_paginated_data(self, fetch_query_with_pagination, "query_results", fetch_args=query, is_query=True)
    # ---------------- Common queries ----------------
    def _open_common_queries(self):
        from gui.common_queries_window import CommonQueriesDialog
        dialog = CommonQueriesDialog(parent=self)
        dialog.show()

    # ---------------- Back / Disconnect ----------------
    def _handle_back_button(self):
        if self.selected_database:
            # return to list view
            self._show_database_list()
            return

        confirm = QMessageBox.question(
            self,
            "Disconnect",
            "Are you sure you want to disconnect from the server?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.No:
            return

        try:
            if self.controller.conn:
                try:
                    self.controller.conn.close()
                except Exception:
                    pass
            self.controller.conn = None
            self.selected_database = None
            self.current_table = None

            self.tree_panel.clear()
            self.back_btn.setVisible(True)
            self.back_btn.setText("⛓️‍💥 Disconnect from Server")

            if getattr(self, "connection_window", None):
                try:
                    self.connection_window.db_connection = None
                    self.connection_window.show()
                    self.connection_window.raise_()
                    self.connection_window.activateWindow()
                except Exception:
                    pass
            else:
                try:
                    from gui.connection_window import ConnectionWindow
                    self.connection_window = ConnectionWindow()
                    self.connection_window.show()
                except Exception:
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to disconnect:\n{e}")

    def refresh_databases(self):
        self._show_database_list()

    # ---------------- Qt events ----------------
    def closeEvent(self, event):
        save_window_settings(self)
        super().closeEvent(event)

