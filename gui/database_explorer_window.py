import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QTextEdit, QInputDialog, QMessageBox, QTableWidget, QTableWidgetItem,
    QDialog, QFormLayout, QLineEdit, QComboBox, QPushButton, QHBoxLayout,
    QLabel, QHeaderView, QFrame
)
from PyQt5.QtCore import QSettings, Qt, QByteArray
from gui.integrated_console import IntegratedConsole, redirect_std


class AddTableDialog(QDialog):
    """Dialog that allows users to define a new table with columns."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Table")
        self.resize(200, 100)

        layout = QVBoxLayout(self)

        # Table name
        form_layout = QFormLayout()
        self.table_name_input = QLineEdit()
        form_layout.addRow("Table name:", self.table_name_input)

        # Columns
        self.columns = []
        self.column_layout = QVBoxLayout()
        self.add_column_row()
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Columns:"))
        layout.addLayout(self.column_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        add_col_btn = QPushButton("Add Column")
        create_btn = QPushButton("Create Table")
        cancel_btn = QPushButton("Cancel")

        btn_layout.addWidget(add_col_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        add_col_btn.clicked.connect(self.add_column_row)
        create_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def add_column_row(self):
        row_layout = QHBoxLayout()
        col_name = QLineEdit()
        col_type = QComboBox()
        col_type.addItems(["INT", "VARCHAR(255)", "FLOAT", "DATE", "BIT"])
        row_layout.addWidget(col_name)
        row_layout.addWidget(col_type)
        self.column_layout.addLayout(row_layout)
        self.columns.append((col_name, col_type))

    def get_table_definition(self):
        table_name = self.table_name_input.text().strip()
        cols = []
        for name_widget, type_widget in self.columns:
            name = name_widget.text().strip()
            ctype = type_widget.currentText()
            if name:
                cols.append((name, ctype))
        return table_name, cols


class DatabaseExplorerWindow(QWidget):
    def __init__(self, connection=None, database=None):
        super().__init__()
        self.conn = connection
        self.selected_database = database

        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_folder = os.path.join(base_folder, "config")
        os.makedirs(config_folder, exist_ok=True)

        gui_settings_path = os.path.join(config_folder, "gui_settings.ini")
        app_settings_path = os.path.join(config_folder, "app_settings.ini")

        self.gui_settings = QSettings(gui_settings_path, QSettings.IniFormat)
        self.app_settings = QSettings(app_settings_path, QSettings.IniFormat)

        self.setWindowTitle(f"Database Explorer - {database}" if database else "Database Explorer")
        self.setGeometry(100, 100, 1200, 700)

        # --- Layout setup ---
        main_layout = QVBoxLayout(self)
        self.main_splitter = QSplitter(Qt.Vertical)

        # --- Top: Tree + Table Designer ---
        self.top_splitter = QSplitter(Qt.Horizontal)

        # Left tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Database Objects"])
        self.top_splitter.addWidget(self.tree)
        self.top_splitter.setSizes([300, 700])

        # Right: Table Designer Panel
        self.table_designer = self.create_table_designer_panel()
        self.top_splitter.addWidget(self.table_designer)

        # --- Bottom: Table content + Console ---
        self.bottom_splitter = QSplitter(Qt.Vertical)

        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_splitter.addWidget(self.content_container)
        self.content_container.hide()

        # Console
        self.console = IntegratedConsole()
        self.bottom_splitter.addWidget(self.console)

        self.bottom_splitter.setStretchFactor(0, 4)
        self.bottom_splitter.setStretchFactor(1, 1)
        self.bottom_splitter.setSizes([0, 200])

        # Combine
        self.main_splitter.addWidget(self.top_splitter)
        self.main_splitter.addWidget(self.bottom_splitter)
        self.main_splitter.setSizes([350, 100])
        main_layout.addWidget(self.main_splitter)

        redirect_std(self.console)
        self.populate_tree_structure()

        if self.conn and self.selected_database:
            self.load_database_data(self.conn, self.selected_database)

        # Restore geometry/splitters last
        if self.gui_settings:
            self.restore_window_settings()

    # --- Table designer panel UI ---
    def create_table_designer_panel(self):
        panel = QWidget()
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # --- Left: Table ---
        self.column_table = QTableWidget()
        self.column_table.setColumnCount(2)
        self.column_table.setHorizontalHeaderLabels(["Column Name", "Data Type"])
        self.column_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.column_table, 9)

        # Initialize table with "Add column" row
        self.column_table.setRowCount(1)
        add_item = QTableWidgetItem("Add column")
        add_item.setFlags(Qt.ItemIsEnabled)
        font = add_item.font()
        font.setItalic(True)
        add_item.setFont(font)
        add_item.setForeground(Qt.gray)
        self.column_table.setItem(0, 0, add_item)
        self.column_table.setItem(0, 1, QTableWidgetItem(""))

        # Connect double-click signal
        self.column_table.cellDoubleClicked.connect(self.handle_table_double_click)

        # --- Right: Form ---
        self.form_widget = QWidget()
        self.form_widget.hide()  # hide by default
        form_layout = QVBoxLayout(self.form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)

        form_layout.addWidget(QLabel("<b>Add Column</b>"))

        self.new_col_name = QLineEdit()
        self.new_col_type = QComboBox()
        self.new_col_type.addItems(["INT", "VARCHAR(255)", "FLOAT", "DATE", "BIT"])
        add_col_btn = QPushButton("Add Column")
        cancel_btn = QPushButton("Cancel")

        # Keep form fields in a horizontal layout
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Name:"))
        input_layout.addWidget(self.new_col_name)
        input_layout.addWidget(QLabel("Type:"))
        input_layout.addWidget(self.new_col_type)
        form_layout.addLayout(input_layout)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_col_btn)
        btn_layout.addWidget(cancel_btn)
        form_layout.addLayout(btn_layout)

        form_layout.addStretch()
        main_layout.addWidget(self.form_widget, 1)

        # Connect buttons
        add_col_btn.clicked.connect(self.add_column_to_table)
        cancel_btn.clicked.connect(self.form_widget.hide)

        return panel

    def handle_table_double_click(self, row, column):
        last_row = self.column_table.rowCount() - 1
        if row == last_row:
            self.form_widget.show()
            self.new_col_name.setFocus()

    # --- Tree and DB loading ---
    def populate_tree_structure(self):
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
        cursor = self.conn.cursor()
        cursor.execute(f"USE [{self.selected_database}]")

        self.tables_item.takeChildren()
        add_item = QTreeWidgetItem(self.tables_item, ["➕ Add new table..."])
        add_item.setData(0, Qt.UserRole, "add_new_table")
        font = add_item.font(0)
        font.setItalic(True)
        add_item.setFont(0, font)

        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        for (table_name,) in cursor.fetchall():
            t_item = QTreeWidgetItem(self.tables_item, [table_name])
            t_item.setData(0, Qt.UserRole, "table")

        self.tree.expandAll()
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)

    # --- Window geometry ---
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
            if isinstance(geometry, QByteArray):
                self.restoreGeometry(geometry)
            else:
                self.restoreGeometry(QByteArray(geometry))

        for key, splitter in [
            ("main_splitter", getattr(self, "main_splitter", None)),
            ("top_splitter", getattr(self, "top_splitter", None)),
            ("bottom_splitter", getattr(self, "bottom_splitter", None)),
        ]:
            state = self.gui_settings.value(key)
            if splitter and state:
                splitter.restoreState(QByteArray(state))

    # --- Tree interactions ---
    def on_item_double_clicked(self, item, column):
        item_type = item.data(0, Qt.UserRole)

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

    def add_new_table_dialog(self):
        dialog = AddTableDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            table_name, columns = dialog.get_table_definition()
            if not table_name or not columns:
                QMessageBox.warning(self, "Invalid input", "Please specify table name and at least one column.")
                return
            try:
                col_defs = ", ".join([f"[{n}] {t}" for n, t in columns])
                query = f"CREATE TABLE [{table_name}] ({col_defs})"
                cursor = self.conn.cursor()
                cursor.execute(query)
                self.conn.commit()

                QTreeWidgetItem(self.tables_item, [table_name])
                QMessageBox.information(self, "Success", f"Table '{table_name}' created successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create table:\n{e}")

    # --- Table viewing and design ---
    def open_table_in_designer(self, table_name):
        """Show table data and structure."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"SELECT TOP 50 * FROM [{table_name}]")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            # Create a new QTableWidget for content
            content_table = QTableWidget()
            content_table.setColumnCount(len(columns))
            content_table.setHorizontalHeaderLabels(columns)
            content_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, val in enumerate(row):
                    content_table.setItem(i, j, QTableWidgetItem(str(val)))

            # Replace old content in persistent container
            for i in reversed(range(self.content_layout.count())):
                w = self.content_layout.itemAt(i).widget()
                if w:
                    w.setParent(None)
            self.content_layout.addWidget(content_table)
            self.content_table = content_table
            self.content_container.show()

            total_height = self.bottom_splitter.height() or 600
            table_height = int(total_height * 0.75)
            console_height = total_height - table_height
            self.bottom_splitter.setSizes([table_height, console_height])

            # Load schema into designer
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table_name}'
            """)
            cols = cursor.fetchall()

            self.column_table.setRowCount(0)
            for col_name, col_type in cols:
                row_pos = self.column_table.rowCount()
                self.column_table.insertRow(row_pos)
                self.column_table.setItem(row_pos, 0, QTableWidgetItem(col_name))
                self.column_table.setItem(row_pos, 1, QTableWidgetItem(col_type))
            
            row_pos = self.column_table.rowCount()
            self.column_table.insertRow(row_pos)

            add_item = QTableWidgetItem("Add column")
            add_item.setFlags(Qt.ItemIsEnabled)
            font = add_item.font()
            font.setItalic(True)
            add_item.setFont(font)
            add_item.setForeground(Qt.gray)

            self.column_table.setItem(row_pos, 0, add_item)
            self.column_table.setItem(row_pos, 1, QTableWidgetItem(""))  # empty for type

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load table:\n{e}")

    def add_column_to_table(self):
        if not hasattr(self, "current_table") or not self.current_table:
            QMessageBox.warning(self, "No Table", "Open a table first.")
            return

        new_name = self.new_col_name.text().strip()
        new_type = self.new_col_type.currentText()

        if not new_name:
            QMessageBox.warning(self, "Invalid", "Column name required.")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"ALTER TABLE [{self.current_table}] ADD [{new_name}] {new_type}")
            self.conn.commit()
            self.new_col_name.clear()
            self.form_widget.hide()  # hide form after adding
            QMessageBox.information(self, "Success", f"Column '{new_name}' added.")
            self.open_table_in_designer(self.current_table)  # refresh schema
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add column:\n{e}")
