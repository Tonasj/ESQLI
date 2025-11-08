import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QMessageBox, 
    QPushButton, QHBoxLayout, QDesktopWidget, QSizePolicy,
    QCheckBox
)
from PyQt5.QtCore import Qt

from gui.gui_helpers.integrated_console import IntegratedConsole, redirect_std
from gui.gui_helpers.window_utils import setup_app_settings, restore_window_settings, save_window_settings

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
        debug_enabled = self.app_settings.value("debug_enabled", False, type=bool)

        self.setWindowTitle(
            f"Database Explorer - {database}" if database else "Database Explorer"
        )

        self._build_ui()
        self._connect_signals()

        self.stdout_stream, self.stderr_stream = redirect_std(self.console, debug_enabled)
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
        root.setContentsMargins(5, 5, 5, 5)

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
            btn.setMinimumHeight(24)
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

        console_container = QWidget()
        console_layout = QVBoxLayout(console_container)
        console_layout.setContentsMargins(0, 0, 0, 0)
        console_layout.setSpacing(2)

        self.console = IntegratedConsole()
        self.debug_checkbox = QCheckBox("Enable debug messages")
        debug_enabled = self.app_settings.value("debug_enabled", False, type=bool)
        self.debug_checkbox.setChecked(debug_enabled)

        console_layout.addWidget(self.console, 1)
        console_layout.addWidget(self.debug_checkbox, 0, Qt.AlignLeft)
        self.left_panel.setMinimumWidth(200)
        self.right_panel.setMinimumWidth(400)
        self.data_panel.setMinimumHeight(100)
        self.console.setMinimumHeight(100)

        self.bottom_splitter.addWidget(self.data_panel)
        self.bottom_splitter.addWidget(console_container)
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
        self.top_splitter.setCollapsible(0, False)
        self.top_splitter.setCollapsible(1, False)

        self.bottom_splitter.setCollapsible(0, False)
        self.bottom_splitter.setCollapsible(1, False)

        self.main_splitter.setCollapsible(0, False)
        self.main_splitter.setCollapsible(1, False)

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
        self.table_panel.primaryKeyToggled.connect(self._set_primary_key)
        self.table_panel.autoIncrementToggled.connect(self._set_auto_increment)
        self.table_panel.nullableToggled.connect(self._set_nullable)

        self.query_panel.runQueryRequested.connect(self._run_query)
        self.query_panel.openCommonQueriesRequested.connect(self._open_common_queries)

        self.data_panel.exportCurrentRequested.connect(self._export_current)
        self.data_panel.exportFullTableRequested.connect(self._export_full_table)
        self.data_panel.exportFullQueryRequested.connect(self._export_full_query)
        self.data_panel.addTableItemRequested.connect(self._add_table_item)
        self.data_panel.pageChangeRequested.connect(self._change_query_page)
        self.data_panel.cellUpdateRequested.connect(self._update_cell_value)

        self.back_btn.clicked.connect(self._handle_back_button)

        # --- NEW: mode toggle buttons ---
        self.table_mode_btn.clicked.connect(lambda: self._switch_mode("table"))
        self.query_mode_btn.clicked.connect(lambda: self._switch_mode("query"))

        self.debug_checkbox.toggled.connect(self._on_toggle_debug)
    
    # ---------------- Debug messages ----------------
    def _on_toggle_debug(self, enabled: bool):
        self.app_settings.setValue("debug_enabled", enabled)
        if hasattr(self.console, "stdout_stream"):
            self.console.stdout_stream.debug_enabled = enabled
        if hasattr(self.console, "stderr_stream"):
            self.console.stderr_stream.debug_enabled = enabled
        print(f"[INFO] Debug messages {'enabled' if enabled else 'disabled'}")

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

            has_pk = any(col[2] for col in schema)  # col[2] is is_primary
            self.data_panel.set_primary_key_info(has_pk, pk_index=0)

            # Update query context
            tables = self.controller.fetch_tables()
            self.query_panel.set_context(
                db_name=self.selected_database, table_name=table_name, tables=tables
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load table:\n{e}")

    # ---------------- Table Designer actions ----------------
    def _add_table_item(self, table_name):
        """Open a dialog to add a new row to the current table."""
        if not self.current_table:
            QMessageBox.warning(self, "No Table", "Open a table first.")
            return

        try:
            # Fetch current table schema
            schema = self.controller.fetch_table_schema(self.current_table)

            from gui.other_windows.dialog import AddRowDialog
            dialog = AddRowDialog(self, self.current_table, schema)

            if dialog.exec_() == dialog.Accepted:
                values = dialog.get_values()
                self.controller.add_table_item(self.current_table, values)
                QMessageBox.information(
                    self,
                    "Row added",
                    f"A new row has been added to '{self.current_table}'."
                )
                # Refresh the table preview
                self._open_table(self.current_table)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add row:\n{e}")

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

    def _set_primary_key(self, column, enabled):
        """Enable or disable primary key with validation against nullable columns."""
        if enabled:
            try:
                # Check if the column is nullable before applying PK
                col_info = self.controller.fetch_column_info(self.current_table, column)
                if col_info and col_info.get("is_nullable", "").upper() == "YES":
                    QMessageBox.warning(
                        self,
                        "Invalid Primary Key Operation",
                        (
                            f"The column '{column}' allows NULL values.\n\n"
                            "⚠️ A PRIMARY KEY column must be defined as NOT NULL.\n"
                            "Please alter the column to disallow NULLs before setting it as a primary key."
                        ),
                    )
                    self.table_panel._revert_checkbox(column, 2, False)
                    return
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Warning",
                    f"Could not verify nullability for column '{column}':\n{e}\nProceeding anyway."
                )

        try:
            self.controller.set_primary_key(self.current_table, column, enabled)
            QMessageBox.information(
                self,
                "Success",
                f"Primary key {'set' if enabled else 'removed'} on '{column}'."
            )
            self._open_table(self.current_table)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update primary key:\n{e}"
            )
            self.table_panel._revert_checkbox(column, 2, not enabled)

    def _set_auto_increment(self, column, enabled):
        """Enable or disable auto-increment (IDENTITY) on a column, with validation and confirmation."""
        if enabled:
            try:
                # Check if column allows NULLs
                col_info = self.controller.fetch_column_info(self.current_table, column)
                if col_info and col_info.get("is_nullable", "").upper() == "YES":
                    QMessageBox.warning(
                        self,
                        "Invalid Auto Increment Operation",
                        (
                            f"The column '{column}' allows NULL values.\n\n"
                            "⚠️ Auto-increment (IDENTITY) columns must be defined as NOT NULL.\n"
                            "Please alter the column to disallow NULLs before enabling auto increment."
                        ),
                    )
                    self.table_panel._revert_checkbox(column, 3, False)
                    return
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Warning",
                    f"Could not verify nullability for column '{column}':\n{e}\nProceeding anyway."
                )

            # Standard warning about data loss
            confirm = QMessageBox.warning(
                self,
                "⚠️ Data Loss Warning",
                (
                    "Enabling auto-increment on an existing column may require recreating it.\n\n"
                    "⚠️ This process can potentially cause data loss or reset existing values.\n\n"
                    "Do you want to continue?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm == QMessageBox.No:
                self.table_panel._revert_checkbox(column, 3, False)
                return

        try:
            self.controller.set_auto_increment(self.current_table, column, enabled)
            QMessageBox.information(
                self,
                "Success",
                f"Auto increment {'enabled' if enabled else 'disabled'} on '{column}'."
            )
            self._open_table(self.current_table)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update auto increment:\n{e}"
            )
            self.table_panel._revert_checkbox(column, 3, not enabled)

    def _set_nullable(self, column: str, is_nullable: bool):
        """Enable/disable NULLs on a column with basic validation."""
        if not self.current_table:
            return

        # If trying to make a column NULL-able, block if it is PK or IDENTITY
        try:
            col_info = self.controller.fetch_column_info(self.current_table, column) or {}
        except Exception as e:
            col_info = {}
            # Non-fatal; continue with best-effort but warn.
            QMessageBox.warning(
                self,
                "Warning",
                f"Could not verify current attributes for '{column}':\n{e}\nProceeding anyway."
            )

        def _truthy(v):
            s = str(v).strip().upper()
            return s in ("1", "TRUE", "YES", "Y")

        is_pk = _truthy(col_info.get("is_primary", col_info.get("primary_key", False)))
        is_identity = _truthy(col_info.get("is_identity", col_info.get("auto_increment", False)))

        # PK/IDENTITY columns must be NOT NULL
        if is_nullable and (is_pk or is_identity):
            QMessageBox.warning(
                self,
                "Invalid Operation",
                (
                    f"Column '{column}' is {'PRIMARY KEY' if is_pk else 'IDENTITY'}.\n\n"
                    "Such columns must be defined as NOT NULL."
                ),
            )
            # Revert the checkbox in the UI (nullable is column index 4)
            self.table_panel._revert_checkbox(column, 4, False)
            return

        # Making a column NOT NULL can fail if existing rows contain NULLs
        if not is_nullable:
            confirm = QMessageBox.warning(
                self,
                "Set NOT NULL?",
                (
                    "Setting this column to NOT NULL will fail if any existing rows contain NULL values.\n\n"
                    "Do you want to continue?"
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if confirm == QMessageBox.No:
                # Revert back to nullable=True in UI
                self.table_panel._revert_checkbox(column, 4, True)
                return

        try:
            # Your controller should implement this; typical signature below:
            # set_nullable(table_name, column_name, is_nullable: bool)
            self.controller.set_nullable(self.current_table, column, is_nullable)
            QMessageBox.information(
                self,
                "Success",
                f"Column '{column}' is now {'NULL' if is_nullable else 'NOT NULL'}."
            )
            # Reload to refresh flags and constraints in the designer
            self._open_table(self.current_table)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update nullability:\n{e}"
            )
            # Revert UI state back
            self.table_panel._revert_checkbox(column, 4, not is_nullable)

    def _update_cell_value(self, table, column, pk_value, new_value):
        """Commit an edited cell back to the database."""
        if not self.current_table or self.current_table != table:
            return
        try:
            self.controller.update_table_cell(table, column, pk_value, new_value)
            QMessageBox.information(self, "Success", f"Value updated in '{column}'.")
            self._open_table(table)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update value:\n{e}")

    def _add_table(self):
        from gui.other_windows.dialog import AddNewDialog
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
        from gui.other_windows.dialog import AddNewDialog
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
        from gui.other_windows.common_queries_window import CommonQueriesDialog
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
                    from gui.connection_window.connection_window import ConnectionWindow
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

