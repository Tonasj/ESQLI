import os
import sys
import traceback
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QTableWidget, QTableWidgetItem, QDialog, QLineEdit, 
    QComboBox, QPushButton, QHBoxLayout, QLabel, QHeaderView, QTextEdit
)
from PyQt5.QtCore import QSettings, Qt, QByteArray
from gui.integrated_console import IntegratedConsole, redirect_std
from gui.dialog import AddNewDialog
from gui.syntax_highlighter import SQLHighlighter
from gui.common_queries_window import CommonQueriesDialog
from db.db_utils import (
    fetch_databases, fetch_tables, use_database,
    fetch_table_schema, fetch_table_preview,
    create_table, create_database, add_column,
    rename_column, alter_column_type, execute_custom_query
)


class DatabaseExplorerWindow(QWidget):
    def __init__(self, connection=None, database=None, connection_window=None):
        super().__init__()
        self.conn = connection
        self.selected_database = database
        self.current_table = None
        self.connection_window = connection_window

        # --- Configuration paths ---
        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_folder = os.path.join(base_folder, "config")
        os.makedirs(config_folder, exist_ok=True)
        gui_settings_path = os.path.join(config_folder, "gui_settings.ini")
        app_settings_path = os.path.join(config_folder, "app_settings.ini")

        self.gui_settings = QSettings(gui_settings_path, QSettings.IniFormat)
        self.app_settings = QSettings(app_settings_path, QSettings.IniFormat)

        # --- Window setup ---
        self.setWindowTitle(f"Database Explorer - {database}" if database else "Database Explorer")
        self.setGeometry(100, 100, 1200, 700)

        main_layout = QVBoxLayout(self)
        self.main_splitter = QSplitter(Qt.Vertical)

        # --- Top split: Tree + Table designer ---
        self.top_splitter = QSplitter(Qt.Horizontal)

        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
 
        self.back_btn = QPushButton("⛓️‍💥 Disconnect from Server")
        self.back_btn.setVisible(True)
        self.back_btn.clicked.connect(self.handle_back_button)
        left_layout.addWidget(self.back_btn)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Database Objects"])
        left_layout.addWidget(self.tree, 1)
        self.top_splitter.addWidget(self.left_panel)

        self.table_designer = self.create_table_designer_panel()
        self.top_splitter.addWidget(self.table_designer)

        # --- Bottom split: Table content + console ---
        self.bottom_splitter = QSplitter(Qt.Vertical)
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_container.hide()
        self.bottom_splitter.addWidget(self.content_container)

        self.console = IntegratedConsole()
        self.bottom_splitter.addWidget(self.console)
        self.bottom_splitter.setStretchFactor(0, 4)
        self.bottom_splitter.setStretchFactor(1, 1)
        self.bottom_splitter.setSizes([0, 200])

        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.bottom_splitter)
        main_layout.addWidget(self.main_splitter)

        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        redirect_std(self.console)

        # --- Initial load ---
        if self.conn and not self.selected_database:
            self.populate_databases_tree()
        elif self.conn and self.selected_database:
            self.populate_tree_structure()
            self.load_database_data(self.conn, self.selected_database)

        if self.gui_settings:
            self.restore_window_settings()

    # --- Table designer panel ---
    def create_table_designer_panel(self):
        panel = QWidget()
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # --- Mode buttons ---
        mode_layout = QHBoxLayout()
        self.table_mode_btn = QPushButton("Table")
        self.query_mode_btn = QPushButton("Query")
        self.table_mode_btn.setCheckable(True)
        self.query_mode_btn.setCheckable(True)
        self.table_mode_btn.setChecked(True)

        mode_layout.addWidget(self.table_mode_btn)
        mode_layout.addWidget(self.query_mode_btn)
        main_layout.addLayout(mode_layout)

        # --- Table view (default) ---
        self.table_mode_widget = QWidget()
        table_layout = QVBoxLayout(self.table_mode_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.column_table = QTableWidget()
        self.column_table.setColumnCount(2)
        self.column_table.setHorizontalHeaderLabels(["Column Name", "Data Type"])
        self.column_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.column_table, 9)

        # Default "Add column" row
        self.column_table.setRowCount(1)
        add_item = QTableWidgetItem("Add column")
        add_item.setFlags(Qt.ItemIsEnabled)
        font = add_item.font()
        font.setItalic(True)
        add_item.setFont(font)
        add_item.setForeground(Qt.gray)
        self.column_table.setItem(0, 0, add_item)
        self.column_table.setItem(0, 1, QTableWidgetItem(""))
        self.column_table.cellDoubleClicked.connect(self.handle_table_double_click)

        self.form_widget = QWidget()
        self.form_widget.hide()
        form_layout = QVBoxLayout(self.form_widget)
        form_layout.addWidget(QLabel("<b>Add Column</b>"))

        self.new_col_name = QLineEdit()
        self.new_col_type = QComboBox()
        self.new_col_type.addItems(["INT", "VARCHAR(255)", "FLOAT", "DATE", "BIT"])
        add_col_btn = QPushButton("Add Column")
        cancel_btn = QPushButton("Cancel")

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Name:"))
        input_layout.addWidget(self.new_col_name)
        input_layout.addWidget(QLabel("Type:"))
        input_layout.addWidget(self.new_col_type)
        form_layout.addLayout(input_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_col_btn)
        btn_layout.addWidget(cancel_btn)
        form_layout.addLayout(btn_layout)

        add_col_btn.clicked.connect(self.add_column_to_table)
        cancel_btn.clicked.connect(self.form_widget.hide)

        table_layout.addWidget(self.form_widget, 1)

        # --- Query view ---
        self.query_mode_widget = QWidget()
        query_layout = QVBoxLayout(self.query_mode_widget)
        query_layout.setContentsMargins(0, 0, 0, 0)

        query_layout.addWidget(QLabel("<b>Run Custom SQL Query</b>"))

        # Buttons
        run_query_btn = QPushButton("▶️ Run Query")
        common_queries_btn = QPushButton("❔ Common SQL Queries")

        # --- Put both buttons in the same horizontal row ---
        btn_row = QHBoxLayout()
        btn_row.addWidget(run_query_btn)
        btn_row.addStretch()
        btn_row.addWidget(common_queries_btn)

        query_layout.addLayout(btn_row)

        # Query input field
        self.query_input = QTextEdit()
        self.highlighter = SQLHighlighter(self.query_input.document(), self.query_input)
        self.query_input.textChanged.connect(self.highlighter.apply_uppercase_keywords)

        common_queries_btn.clicked.connect(self.open_common_queries)
        run_query_btn.clicked.connect(self.run_custom_query)

        query_layout.addWidget(self.query_input)

        
        self.query_mode_widget.hide()  # hidden by default

        # Add both modes to main layout
        main_layout.addWidget(self.table_mode_widget)
        main_layout.addWidget(self.query_mode_widget)

        # --- Connect mode switching ---
        self.table_mode_btn.clicked.connect(lambda: self.switch_mode("table"))
        self.query_mode_btn.clicked.connect(lambda: self.switch_mode("query"))

        return panel

    def handle_table_double_click(self, row, column):
        if row == self.column_table.rowCount() - 1:
            self.form_widget.show()
            self.new_col_name.setFocus()

    # --- Database + Tree management ---
    def populate_tree_structure(self):
        self.tree.setHeaderHidden(True)
        self.tables_item = QTreeWidgetItem(["Tables"])
        self.views_item = QTreeWidgetItem(["Views"])
        self.procedures_item = QTreeWidgetItem(["Stored Procedures"])
        self.tree.addTopLevelItem(self.tables_item)
        self.tree.addTopLevelItem(self.views_item)
        self.tree.addTopLevelItem(self.procedures_item)
        self.tree.expandAll()

    def load_database_data(self, connection, database):
        self.conn = connection
        self.selected_database = database
        self.setWindowTitle(f"Database Explorer - {database}")
        use_database(connection, database)

        self.tables_item.takeChildren()
        add_item = QTreeWidgetItem(self.tables_item, ["➕ Add new table..."])
        add_item.setData(0, Qt.UserRole, "add_new_table")
        font = add_item.font(0)
        font.setItalic(True)
        add_item.setFont(0, font)

        for table_name in fetch_tables(connection):
            t_item = QTreeWidgetItem(self.tables_item, [table_name])
            t_item.setData(0, Qt.UserRole, "table")

        self.tree.expandAll()

    # --- Table viewing ---
    def open_table_in_designer(self, table_name):
        """Show table data and editable schema designer."""
        try:
            self.current_table = table_name

            # --- Load preview data ---
            columns, rows = fetch_table_preview(self.conn, table_name)
            content_table = QTableWidget()
            content_table.setColumnCount(len(columns))
            content_table.setHorizontalHeaderLabels(columns)
            content_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    content_table.setItem(i, j, QTableWidgetItem(str(val)))

            # Replace existing content
            for i in reversed(range(self.content_layout.count())):
                w = self.content_layout.itemAt(i).widget()
                if w:
                    w.setParent(None)
            self.content_layout.addWidget(content_table)
            self.content_table = content_table
            self.content_container.show()

            # --- Load schema into designer ---
            cols = fetch_table_schema(self.conn, table_name)
            self.column_table.blockSignals(True)  # avoid triggering during setup
            self.column_table.setRowCount(0)

            valid_types = ["INT", "VARCHAR(255)", "FLOAT", "DATE", "BIT"]

            for col_name, col_type in cols:
                row_pos = self.column_table.rowCount()
                self.column_table.insertRow(row_pos)

                # Editable name item
                name_item = QTableWidgetItem(col_name)
                name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
                self.column_table.setItem(row_pos, 0, name_item)

                # Type combo box
                type_combo = QComboBox()
                type_combo.addItems(valid_types)
                # Try to match current type
                idx = type_combo.findText(col_type.upper())
                if idx != -1:
                    type_combo.setCurrentIndex(idx)
                else:
                    type_combo.setCurrentIndex(0)
                type_combo.currentTextChanged.connect(
                    lambda new_type, col=col_name: self.change_column_type(col, new_type)
                )
                self.column_table.setCellWidget(row_pos, 1, type_combo)

            self.column_table.blockSignals(False)

            # --- Add "Add column" row ---
            row_pos = self.column_table.rowCount()
            self.column_table.insertRow(row_pos)
            add_item = QTableWidgetItem("Add column")
            add_item.setFlags(Qt.ItemIsEnabled)
            font = add_item.font()
            font.setItalic(True)
            add_item.setFont(font)
            add_item.setForeground(Qt.gray)
            self.column_table.setItem(row_pos, 0, add_item)
            self.column_table.setItem(row_pos, 1, QTableWidgetItem(""))

            # --- Connect cell change for renaming ---
            try:
                self.column_table.itemChanged.disconnect()
            except Exception:
                pass
            self.column_table.itemChanged.connect(self.on_schema_item_changed)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load table:\n{e}")
            print(f"⚠️Error: Failed to load table: {e}")


    # --- Column addition ---
    def add_column_to_table(self):
        if not self.current_table:
            QMessageBox.warning(self, "No Table", "Open a table first.")
            return

        new_name = self.new_col_name.text().strip()
        new_type = self.new_col_type.currentText()
        if not new_name:
            QMessageBox.warning(self, "Invalid", "Column name required.")
            return
        try:
            add_column(self.conn, self.current_table, new_name, new_type)
            self.new_col_name.clear()
            self.form_widget.hide()
            QMessageBox.information(self, "Success", f"Column '{new_name}' added.")
            self.open_table_in_designer(self.current_table)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add column:\n{e}")
            print(f"⚠️Error: Failed to add column: {e}")

    # --- New DB/Table dialogs ---
    def add_new_table_dialog(self):
        dialog = AddNewDialog(self, mode="table")
        if dialog.exec_() == QDialog.Accepted:
            table_name, columns = dialog.get_table_definition()
            if not table_name or not columns:
                QMessageBox.warning(self, "Invalid input", "Please specify table name and at least one column.")
                return
            try:
                create_table(self.conn, table_name, columns)
                new_item = QTreeWidgetItem(self.tables_item, [table_name])
                new_item.setData(0, Qt.UserRole, "table")
                QMessageBox.information(self, "Success", f"Table '{table_name}' created successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create table:\n{e}")
                print(f"⚠️Error: Failed to create table: {e}")

    def add_new_database_dialog(self):
        dialog = AddNewDialog(self, mode="database")
        if dialog.exec_() == QDialog.Accepted:
            db_name = dialog.get_database_name()
            if not db_name:
                QMessageBox.warning(self, "Invalid input", "Please specify a database name.")
                return
            try:
                create_database(self.conn, db_name)
                QMessageBox.information(self, "Success", f"Database '{db_name}' created successfully.")
                self.populate_databases_tree()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create database:\n{e}")
                print(f"⚠️Error: Failed to create database: {e}")

    def populate_databases_tree(self):
        self.tree.clear()
        self.tree.setHeaderLabels(["Databases", "Action"])
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 40)
        try:
            databases = fetch_databases(self.conn)
            add_db_item = QTreeWidgetItem(["➕ Add new database..."])
            add_db_item.setData(0, Qt.UserRole, "add_new_database")
            font = add_db_item.font(0)
            font.setItalic(True)
            add_db_item.setFont(0, font)
            self.tree.addTopLevelItem(add_db_item)

            for db_name in databases:
                db_item = QTreeWidgetItem([db_name])
                db_item.setData(0, Qt.UserRole, "database")
                self.tree.addTopLevelItem(db_item)

                btn = QPushButton("🔗")
                btn.setMaximumWidth(30)
                btn.setToolTip(f"Connect to {db_name}")
                btn.clicked.connect(lambda _, db=db_name: self.select_database(db))
                self.tree.setItemWidget(db_item, 1, btn)
            self.tree.expandAll()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load databases:\n{e}")
            print(f"⚠️Error: Failed to load databases: {e}")
        
    # --- Navigation ---
    def select_database(self, db_name):
        try:
            self.selected_database = db_name
            self.tree.clear()
            self.populate_tree_structure()
            self.load_database_data(self.conn, db_name)
            self.back_btn.setVisible(True)
            self.back_btn.setText("⬅️ Return to Databases")  # reset label
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load database '{db_name}':\n{e}")
            print(f"⚠️Error: Failed to load database '{db_name}': {e}")
    
    def return_to_database_list(self):
        try:
            self.selected_database = None
            self.current_table = None
            self.setWindowTitle("Database Explorer")
            self.tree.clear()
            self.populate_databases_tree()
            self.back_btn.setText("⛓️‍💥 Disconnect from Server")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to return to database list:\n{e}")
            print(f"⚠️Error: Failed to return to database list: {e}")
    
    def on_schema_item_changed(self, item):
        """Handle column renaming when name is edited."""
        if not hasattr(self, "current_table") or not self.current_table:
            return

        row = item.row()
        col = item.column()
        if col != 0:
            return

        try:
            old_name = fetch_table_schema(self.conn, self.current_table)[row][0]
        except Exception:
            return

        new_name = item.text().strip()
        if not new_name or new_name == old_name:
            return

        reply = QMessageBox.question(
            self,
            "Rename Column",
            f"Rename column '{old_name}' to '{new_name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.No:
            item.setText(old_name)
            return

        try:
            rename_column(self.conn, self.current_table, old_name, new_name)
            QMessageBox.information(self, "Success", f"Column renamed to '{new_name}'.")
            self.open_table_in_designer(self.current_table)  # refresh schema
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename column:\n{e}")
            print(f"⚠️Error: Failed to rename column: {e}")
            item.setText(old_name)


    def change_column_type(self, column_name, new_type):
        """Change a column's data type via ALTER TABLE."""
        if not hasattr(self, "current_table") or not self.current_table:
            return

        reply = QMessageBox.question(
            self,
            "Change Column Type",
            f"Change column '{column_name}' to type {new_type}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.No:
            return

        try:
            alter_column_type(self.conn, self.current_table, column_name, new_type)
            QMessageBox.information(
                self, "Success", f"Column '{column_name}' type changed to {new_type}."
            )
            self.open_table_in_designer(self.current_table)  # refresh schema
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to alter column:\n{e}")
            print(f"⚠️Error: Failed to alter column: {e}")
    
    def switch_mode(self, mode):
        """Switch between Table and Query modes."""
        if mode == "table":
            self.query_mode_btn.setChecked(False)
            self.table_mode_btn.setChecked(True)
            self.query_mode_widget.hide()
            self.table_mode_widget.show()
        else:
            self.table_mode_btn.setChecked(False)
            self.query_mode_btn.setChecked(True)
            self.table_mode_widget.hide()
            self.query_mode_widget.show()

            if not self.query_input.toPlainText().strip():
                contextual_query = ""
                if self.selected_database:
                    contextual_query += f"USE `{self.selected_database}`;\n"
                    if self.current_table:
                        contextual_query += f"-- Current table: `{self.current_table}`\n"
                self.query_input.setPlainText(contextual_query)


    def run_custom_query(self):
        """Execute user-provided SQL query and display results."""
        query = self.query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "No Query", "Please enter a SQL query to run.")
            return

        try:
            columns, rows = execute_custom_query(self.conn, query)
            # Clear previous content
            for i in reversed(range(self.content_layout.count())):
                w = self.content_layout.itemAt(i).widget()
                if w:
                    w.setParent(None)

            if not columns:
                QMessageBox.information(self, "Success", "Query executed successfully (no result set).")
                return

            result_table = QTableWidget()
            result_table.setColumnCount(len(columns))
            result_table.setHorizontalHeaderLabels(columns)
            result_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    result_table.setItem(i, j, QTableWidgetItem(str(val)))

            self.content_layout.addWidget(result_table)
            self.content_container.show()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to execute query:\n{e}")
            print(f"⚠️Error: Failed to execute query: {e}")
        
    def on_item_double_clicked(self, item, column):
        item_type = item.data(0, Qt.UserRole)

        if item_type == "add_new_database":
            self.add_new_database_dialog()
            return

        if item_type == "add_new_table":
            self.add_new_table_dialog()
            return

        if item_type != "table":
            if hasattr(self, "content_table"):
                self.content_table.hide()
            self.content_container.hide()
            return

        table_name = item.text(0)
        self.open_table_in_designer(table_name)       

    def handle_back_button(self):
        """
        - If viewing a specific database -> return to DB list.
        - If already at DB list -> disconnect (close conn), clear UI, and show the existing ConnectionWindow.
        """
        if self.selected_database:
            # currently inside a database: go back to database list
            self.return_to_database_list()
            self.back_btn.setText("⛓️‍💥 Disconnect from Server")
            return

        # Already at database list -> disconnect from server
        confirm = QMessageBox.question(
            self,
            "Disconnect",
            "Are you sure you want to disconnect from the server?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.No:
            return

        try:
            # close underlying DB connection if present
            if self.conn:
                try:
                    self.conn.close()
                except Exception as e:
                    print(f"⚠️Warning: error closing connection: {e}")
            self.conn = None
            self.selected_database = None
            self.current_table = None

            # clear UI (but keep window open)
            self.tree.clear()
            # hide any content panel
            try:
                self.content_container.hide()
            except Exception:
                pass

            # reset back button state/visibility as you desire
            # keep it visible (you said you want it always visible); update label
            self.back_btn.setVisible(True)
            self.back_btn.setText("⛓️‍💥 Disconnect from Server")

            # If this explorer was opened by a ConnectionWindow, show it (reuse)
            if getattr(self, "connection_window", None):
                try:
                    # ensure the connection window is aware there's no active connection
                    self.connection_window.db_connection = None
                    self.connection_window.show()
                    self.connection_window.raise_()
                    self.connection_window.activateWindow()
                except Exception as e:
                    print(f"⚠️Error showing ConnectionWindow: {e}")
            else:
                # fallback: if no reference available, create a new ConnectionWindow
                try:
                    from gui.connection_window import ConnectionWindow
                    self.connection_window = ConnectionWindow()
                    self.connection_window.show()
                except Exception as e:
                    print(f"⚠️Error creating fallback ConnectionWindow: {e}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to disconnect:\n{e}")
            print(f"⚠️Error: Failed to disconnect: {e}")

    def open_common_queries(self):
        dialog = CommonQueriesDialog()
        dialog.show()

    # --- Window persistence ---
    def closeEvent(self, event):
        self.save_window_settings()
        super().closeEvent(event)

    def save_window_settings(self):
        if not self.gui_settings:
            return
        self.gui_settings.setValue("explorer_geometry", self.saveGeometry())
        self.gui_settings.setValue("main_splitter", self.main_splitter.saveState())
        self.gui_settings.setValue("top_splitter", self.top_splitter.saveState())
        self.gui_settings.setValue("bottom_splitter", self.bottom_splitter.saveState())

    def restore_window_settings(self):
        if not self.gui_settings:
            return
        geometry = self.gui_settings.value("explorer_geometry")
        if geometry:
            self.restoreGeometry(QByteArray(geometry))
        for key, splitter in [
            ("main_splitter", getattr(self, "main_splitter", None)),
            ("top_splitter", getattr(self, "top_splitter", None)),
            ("bottom_splitter", getattr(self, "bottom_splitter", None)),
        ]:
            state = self.gui_settings.value(key)
            if splitter and state:
                splitter.restoreState(QByteArray(state))
