from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QHeaderView, QLineEdit, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt
from functools import partial


class TableDesignerPanel(QWidget):
    addColumnRequested = pyqtSignal(str, str)      # name, type
    renameColumnRequested = pyqtSignal(str, str)   # old, new
    changeTypeRequested = pyqtSignal(str, str)     # column, new_type

    VALID_TYPES = ["INT", "VARCHAR(255)", "FLOAT", "DATE", "BIT"]

    def __init__(self):
        super().__init__()
        self.current_schema = []  # [(name, type)]
        self._build()

    def _build(self):
        self.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 0)

        # Table
        self.column_table = QTableWidget()
        self.column_table.setColumnCount(2)
        self.column_table.setHorizontalHeaderLabels(["Column Name", "Data Type"])
        self.column_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.column_table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.column_table)

        # Add form (hidden by default)
        self.form = QWidget()
        self.form.hide()
        form_layout = QVBoxLayout(self.form)
        form_layout.addWidget(QLabel("<b>Add Column</b>"))
        row = QHBoxLayout()
        self.new_name = QLineEdit()
        self.new_type = QComboBox()
        self.new_type.addItems(self.VALID_TYPES)
        row.addWidget(QLabel("Name:"))
        row.addWidget(self.new_name)
        row.addWidget(QLabel("Type:"))
        row.addWidget(self.new_type)
        form_layout.addLayout(row)
        btns = QHBoxLayout()
        add_btn = QPushButton("Add Column")
        cancel_btn = QPushButton("Cancel")
        add_btn.clicked.connect(self._emit_add)
        cancel_btn.clicked.connect(self.form.hide)
        btns.addWidget(add_btn)
        btns.addWidget(cancel_btn)
        btns.addStretch()
        form_layout.addLayout(btns)
        layout.addWidget(self.form)

        self.column_table.cellDoubleClicked.connect(self._maybe_show_form)

    # -------- Public API --------
    def load_schema(self, schema):
        """Load table schema and make type combos editable per column."""
        self.current_schema = list(schema)
        self.column_table.blockSignals(True)
        self.column_table.setRowCount(0)

        for name, typ in self.current_schema:
            r = self.column_table.rowCount()
            self.column_table.insertRow(r)

            # editable name
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)
            self.column_table.setItem(r, 0, name_item)

            # data type combobox
            combo = QComboBox()
            combo.addItems(self.VALID_TYPES)
            idx = combo.findText(typ.upper())
            combo.setCurrentIndex(idx if idx != -1 else 0)
            combo.currentTextChanged.connect(partial(self._on_type_changed, name))
            self.column_table.setCellWidget(r, 1, combo)

        # Add "Add column" row
        r = self.column_table.rowCount()
        self.column_table.insertRow(r)
        add_item = QTableWidgetItem("Add column")
        add_item.setFlags(Qt.ItemIsEnabled)
        f = add_item.font()
        f.setItalic(True)
        add_item.setFont(f)
        add_item.setForeground(Qt.gray)
        self.column_table.setItem(r, 0, add_item)
        self.column_table.setItem(r, 1, QTableWidgetItem(""))
        self.column_table.blockSignals(False)

    def clear(self):
        self.current_schema = []
        self.column_table.setRowCount(0)
        self.form.hide()

    # -------- Internals --------
    def _maybe_show_form(self, row, col):
        if row == self.column_table.rowCount() - 1:
            self.form.show()
            self.new_name.setFocus()

    def _emit_add(self):
        name = self.new_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid", "Column name required.")
            return
        self.addColumnRequested.emit(name, self.new_type.currentText())
        self.new_name.clear()
        self.form.hide()

    def _on_item_changed(self, item):
        row, col = item.row(), item.column()
        if col != 0:
            return
        if row >= len(self.current_schema):  # ignore "Add column"
            return
        old_name = self.current_schema[row][0]
        new_name = item.text().strip()
        if not new_name or new_name == old_name:
            return
        self.renameColumnRequested.emit(old_name, new_name)

    def _on_type_changed(self, column_name, new_type):
        """Emit type change with correct bound column."""
        self.changeTypeRequested.emit(column_name, new_type)
