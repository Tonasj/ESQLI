from PyQt5.QtWidgets import (QVBoxLayout,
    QDialog, QFormLayout, QLineEdit, QComboBox, 
    QPushButton, QHBoxLayout,QLabel
)

class AddNewDialog(QDialog):
    """ Modular dialog that can create either a new Database or a new Table. """
    def __init__(self, parent=None, mode="table"):
        super().__init__(parent)
        self.mode = mode
        self.columns = []
        self.setWindowTitle(f"Create New {mode.capitalize()}")
        self.resize(300, 100)
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

    def init_table_ui(self):
        form_layout = QFormLayout()
        self.table_name_input = QLineEdit()
        form_layout.addRow("Table name:", self.table_name_input)
        self.layout.addLayout(form_layout)

        self.layout.addWidget(QLabel("Columns:"))
        self.column_layout = QVBoxLayout()
        self.add_column_row()
        self.layout.addLayout(self.column_layout)

        add_col_btn = QPushButton("Add Column")
        add_col_btn.clicked.connect(self.add_column_row)
        self.layout.addWidget(add_col_btn)

    def init_database_ui(self):
        form_layout = QFormLayout()
        self.db_name_input = QLineEdit()
        form_layout.addRow("Database name:", self.db_name_input)
        self.layout.addLayout(form_layout)

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

    def get_database_name(self):
        return self.db_name_input.text().strip()