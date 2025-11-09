from PyQt5.QtWidgets import (QVBoxLayout, QDateEdit,
    QDialog, QFormLayout, QLineEdit, QComboBox, 
    QPushButton, QHBoxLayout, QLabel, QMessageBox,
    QCheckBox
)
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtCore import QLocale, QDate

class AddRowDialog(QDialog):
    """Dialog for inserting a new row into an existing table."""
    def __init__(self, parent, table_name, columns):
        """
        columns: list of (col_name, col_type) tuples,
                 e.g. [("id", "INT"), ("name", "VARCHAR(50)"), ("price", "FLOAT")]
        """
        super().__init__(parent)
        self.table_name = table_name
        self.columns = columns
        self.values = {}
        self.setWindowTitle(f"Add Row to {table_name}")
        self.resize(400, 200)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.inputs = {}

        for col_name, col_type, is_primary, is_identity, is_nullable in self.columns:
            upper_type = col_type.upper()

            # --- Choose widget type based on data type ---
            if "DATE" in upper_type:
                edit = QDateEdit()
                edit.setDisplayFormat("dd.MM.yyyy")   # User sees day.month.year
                edit.setCalendarPopup(True)
                edit.setDate(QDate.currentDate())
            else:
                edit = QLineEdit()
                edit.setPlaceholderText(col_type)

                # Numeric input restriction
                if "INT" in upper_type:
                    edit.setValidator(QIntValidator())
                elif any(t in upper_type for t in ["FLOAT", "REAL", "DECIMAL", "NUMERIC"]):
                    validator = QDoubleValidator()
                    validator.setLocale(QLocale())  # locale-aware
                    edit.setValidator(validator)

            # --- Disable primary key / identity fields ---
            if is_identity or (is_primary and "INT" in upper_type):
                edit.setReadOnly(True)
                edit.setPlaceholderText("(auto-generated)")
                edit.setStyleSheet("background-color: #eee; color: #666;")

            form_layout.addRow(QLabel(f"{col_name}:"), edit)
            self.inputs[col_name] = edit

        layout.addLayout(form_layout)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("Insert")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        ok_btn.clicked.connect(self._on_accept)
        cancel_btn.clicked.connect(self.reject)

    # ---------------- Validation & Data Retrieval ----------------
    def _on_accept(self):
        """Ensure all validated fields are correct before closing."""
        # Example validation: if field has an invalid number
        for col, edit in self.inputs.items():
            if isinstance(edit, QDateEdit) or not edit.isEnabled() or edit.isReadOnly():
                continue
            validator = edit.validator()
            if validator:
                state, _, _ = validator.validate(edit.text(), 0)
                if state != validator.Acceptable and edit.text().strip():
                    QMessageBox.warning(
                        self,
                        "Invalid Input",
                        f"Invalid value for '{col}'. Please enter a valid number."
                    )
                    return
        self.accept()

    def get_values(self):
        """Return a dict of {column: value} for the new row, excluding identity columns."""
        result = {}
        for (col_name, col_type, is_primary, is_identity, is_nullable) in self.columns:
            edit = self.inputs[col_name]
            if is_identity:
                # Skip auto-increment columns entirely
                continue

            if isinstance(edit, QDateEdit):
                val = edit.date().toString("yyyy-MM-dd")
            else:
                val = edit.text().strip().replace(',', '.')
            result[col_name] = None if val == "" else val
        return result


class AddNewDialog(QDialog):
    """ Modular dialog that can create either a new Database or a new Table. """
    def __init__(self, parent=None, mode="table"):
        super().__init__(parent)
        self.mode = mode
        self.columns = []
        self.setWindowTitle(f"Create New {mode.capitalize()}")
        self.resize(450, 200)
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        if self.mode == "table":
            self.init_table_ui()
        elif self.mode == "database":
            self.init_database_ui()
        else:
            raise ValueError("Invalid dialog mode. Use 'table' or 'database'.")
        self.init_buttons()

    # ---------------- Table creation UI ----------------
    def init_table_ui(self):
        form_layout = QFormLayout()
        self.table_name_input = QLineEdit()
        form_layout.addRow("Table name:", self.table_name_input)
        self.layout.addLayout(form_layout)

        self.layout.addWidget(QLabel("<b>Columns:</b>"))
        self.column_layout = QVBoxLayout()
        self.add_column_row()  # first row
        self.layout.addLayout(self.column_layout)

        add_col_btn = QPushButton("Add Column")
        add_col_btn.clicked.connect(self.add_column_row)
        self.layout.addWidget(add_col_btn)

    # ---------------- Database creation UI ----------------
    def init_database_ui(self):
        form_layout = QFormLayout()
        self.db_name_input = QLineEdit()
        form_layout.addRow("Database name:", self.db_name_input)
        self.layout.addLayout(form_layout)

    # ---------------- Bottom buttons ----------------
    def init_buttons(self):
        btn_layout = QHBoxLayout()
        self.create_btn = QPushButton(f"Create {self.mode.capitalize()}")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addStretch()
        btn_layout.addWidget(self.create_btn)
        btn_layout.addWidget(self.cancel_btn)
        self.layout.addLayout(btn_layout)
        self.create_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    # ---------------- Add column row ----------------
    def add_column_row(self):
        row_layout = QHBoxLayout()

        col_name = QLineEdit()
        col_name.setPlaceholderText("Column name")

        col_type = QComboBox()
        col_type.addItems(["INT", "VARCHAR(255)", "FLOAT", "DATE", "BIT"])

        pk_checkbox = QCheckBox("PK")
        ai_checkbox = QCheckBox("Auto")
        null_checkbox = QCheckBox("NULL")
        null_checkbox.setChecked(True)

        # Auto Increment only valid for INT
        def on_type_changed(t):
            ai_checkbox.setEnabled("INT" in t.upper())
        col_type.currentTextChanged.connect(on_type_changed)
        on_type_changed(col_type.currentText())

        # Enforce only one primary key
        def on_pk_toggled(state):
            if state:
                for widgets in self.columns:
                    if widgets[2] is not pk_checkbox:
                        widgets[2].setChecked(False)
        pk_checkbox.toggled.connect(on_pk_toggled)

        # disable NULL if PK is checked
        def on_pk_null_interlock(state):
            if state:
                null_checkbox.setChecked(False)
                null_checkbox.setEnabled(False)
            else:
                null_checkbox.setEnabled(True)
        pk_checkbox.toggled.connect(on_pk_null_interlock)

        # disable PK if Auto is checked (Auto implies PK often, but optional)
        def on_auto_pk_link(state):
            if state:
                pk_checkbox.setChecked(True)
        ai_checkbox.toggled.connect(on_auto_pk_link)

        # Layout composition
        row_layout.addWidget(col_name)
        row_layout.addWidget(col_type)
        row_layout.addWidget(pk_checkbox)
        row_layout.addWidget(ai_checkbox)
        row_layout.addWidget(null_checkbox)
        self.column_layout.addLayout(row_layout)
        self.columns.append((col_name, col_type, pk_checkbox, ai_checkbox, null_checkbox))

    # ---------------- Table Definition Builder ----------------
    def get_table_definition(self):
        table_name = self.table_name_input.text().strip()
        cols = []
        for name_widget, type_widget, pk_widget, ai_widget, null_widget in self.columns:
            name = name_widget.text().strip()
            ctype = type_widget.currentText()
            is_pk = pk_widget.isChecked()
            is_auto = ai_widget.isChecked()
            is_nullable = null_widget.isChecked()
            if name:
                cols.append((name, ctype, is_pk, is_auto, is_nullable))
        return table_name, cols

    def get_database_name(self):
        return self.db_name_input.text().strip()