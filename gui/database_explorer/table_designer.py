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
    primaryKeyToggled = pyqtSignal(str, bool)      # column, is_primary
    autoIncrementToggled = pyqtSignal(str, bool)   # column, is_identity
    nullableToggled = pyqtSignal(str, bool)  # column, is_nullable

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
        self.column_table.setColumnCount(5)
        self.column_table.setHorizontalHeaderLabels(["Column Name", "Data Type", "Primary Key", "Auto Increment", "Nullable"])
        header = self.column_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)      # Column Name – fill extra space
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Data Type – adjust to text
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Primary Key – compact
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) 
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

        for col in self.current_schema:
            name, typ = col[0], col[1]
            is_primary = col[2] if len(col) > 2 else False
            is_identity = col[3] if len(col) > 3 else False

            r = self.column_table.rowCount()
            self.column_table.insertRow(r)

            # --- Column name cell ---
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)

            if is_primary or is_identity:
                name_item.setBackground(Qt.lightGray)

            self.column_table.setItem(r, 0, name_item)

            # --- Data type combobox ---
            combo = QComboBox()
            combo.addItems(self.VALID_TYPES)
            idx = combo.findText(typ.upper())
            combo.setCurrentIndex(idx if idx != -1 else 0)
            combo.currentTextChanged.connect(partial(self._on_type_changed, name))
            if is_identity:
                combo.setEnabled(False)
            self.column_table.setCellWidget(r, 1, combo)

            # --- Primary key checkbox ---
            pk_item = QTableWidgetItem()
            pk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            pk_item.setCheckState(Qt.Checked if is_primary else Qt.Unchecked)
            self.column_table.setItem(r, 2, pk_item)

            # --- Auto increment checkbox ---
            id_item = QTableWidgetItem()
            id_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            id_item.setCheckState(Qt.Checked if is_identity else Qt.Unchecked)
            if not "INT" in typ.upper():
                # Only allow auto-increment for numeric columns
                id_item.setFlags(Qt.NoItemFlags)
            self.column_table.setItem(r, 3, id_item)

            # --- Nullable checkbox ---
            nullable = col[4] if len(col) > 4 else True
            null_item = QTableWidgetItem()
            null_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            null_item.setCheckState(Qt.Checked if nullable else Qt.Unchecked)
            if is_primary:
                null_item.setFlags(Qt.NoItemFlags)
            self.column_table.setItem(r, 4, null_item)

        # --- Add "Add column" row ---
        r = self.column_table.rowCount()
        self.column_table.insertRow(r)
        add_item = QTableWidgetItem("Add column")
        add_item.setFlags(Qt.ItemIsEnabled)
        f = add_item.font()
        f.setItalic(True)
        add_item.setFont(f)
        add_item.setForeground(Qt.gray)
        self.column_table.setItem(r, 0, add_item)
        for i in range(1, 5):
            self.column_table.setItem(r, i, QTableWidgetItem(""))
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
        if row >= len(self.current_schema):  # ignore "Add column"
            return

        col_name = self.current_schema[row][0]

        # Column name changed
        if col == 0:
            old_name = self.current_schema[row][0]
            new_name = item.text().strip()
            if new_name and new_name != old_name:
                self.renameColumnRequested.emit(old_name, new_name)

        # Primary key checkbox
        elif col == 2:
            is_pk = item.checkState() == Qt.Checked
            self.primaryKeyToggled.emit(col_name, is_pk)

        # Auto-increment checkbox
        elif col == 3:
            is_auto = item.checkState() == Qt.Checked
            self.autoIncrementToggled.emit(col_name, is_auto)
        
        # Nullable checkbox
        elif col == 4:  
            is_nullable = item.checkState() == Qt.Checked
            self.nullableToggled.emit(col_name, is_nullable)

    def _on_type_changed(self, column_name, new_type):
        """Emit type change with correct bound column."""
        self.changeTypeRequested.emit(column_name, new_type)

    def _revert_checkbox(self, column_name, col_index, checked):
        """Revert a checkbox state in the table safely."""
        for row in range(self.column_table.rowCount()):
            item = self.column_table.item(row, 0)
            if item and item.text().replace("🔑 ", "") == column_name:
                target = self.column_table.item(row, col_index)
                if target:
                    self.column_table.blockSignals(True)
                    target.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                    self.column_table.blockSignals(False)
                break