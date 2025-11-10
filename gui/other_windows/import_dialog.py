from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt


class ImportMappingDialog(QDialog):
    """Lets the user map file headers to table columns manually."""

    def __init__(self, parent, file_headers, table_columns, initial_mapping):
        super().__init__(parent)
        self.setWindowTitle("Map Columns for Import")
        self.resize(500, 400)
        self.file_headers = file_headers
        self.table_columns = table_columns
        self.mapping = initial_mapping.copy()

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QVBoxLayout(inner)
        scroll.setWidget(inner)

        self.combo_boxes = {}

        for fh in file_headers:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"File Column: {fh}"))
            combo = QComboBox()
            combo.addItem("(ignore)")
            combo.addItems(table_columns)
            if initial_mapping.get(fh) in table_columns:
                combo.setCurrentText(initial_mapping[fh])
            self.combo_boxes[fh] = combo
            row.addWidget(combo)
            form.addLayout(row)

        layout.addWidget(scroll)

        # Buttons
        btn_layout = QHBoxLayout()
        ok = QPushButton("Import")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(ok)
        btn_layout.addWidget(cancel)
        layout.addLayout(btn_layout)

    def get_mapping(self):
        result = {}
        for fh, combo in self.combo_boxes.items():
            val = combo.currentText()
            result[fh] = None if val == "(ignore)" else val
        return result
