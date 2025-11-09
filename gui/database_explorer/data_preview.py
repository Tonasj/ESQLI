from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer


class DataPreviewPanel(QWidget):
    exportCurrentRequested = pyqtSignal(list, list, str)  # headers, rows(list of lists), label
    exportFullTableRequested = pyqtSignal(str)            # table name
    exportFullQueryRequested = pyqtSignal(str)            # full SQL text
    addTableItemRequested = pyqtSignal(str)               # add item to table
    pageChangeRequested = pyqtSignal(int, int)            # new_page, page_size
    cellUpdateRequested = pyqtSignal(str, str, object, 
                                     object, list, list)  # table_name, column_name, pk_value, new_value, row_values, headers

    def __init__(self):
        super().__init__()
        self._build()
        self._headers = []
        self._rows = []
        self._label = ""
        self._page = 0
        self._page_size = 500
        self._current_query = None
        self._table_widget = None
        self._pk_index = 0
        self._has_primary_key = False  # <-- new flag

    # ------- New helper -------
    def set_primary_key_info(self, has_pk: bool, pk_index: int = 0):
        """Called by parent to inform whether the current table has a PK."""
        self._has_primary_key = has_pk
        self._pk_index = pk_index

    # ------- Core UI -------
    def _build(self):
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)

    def clear(self, reset_query=True):
        while self.layout_.count():
            w = self.layout_.takeAt(0).widget()
            if w:
                w.setParent(None)
        self._headers, self._rows, self._label = [], [], ""
        if reset_query:
            self._current_query = None

    # ------- Public API -------
    def show_table_data(self, columns, rows, label):
        self._current_query = None
        self._render(columns, rows, label, query_mode=False)

    def show_query_results(self, columns, rows, page, page_size, query=None):
        self._page, self._page_size = page, page_size
        self._current_query = query
        self._render(columns, rows, label="query_results", query_mode=True)

    # ------- Internals -------
    def _render(self, columns, rows, label, query_mode):
        self.clear(reset_query=not query_mode)
        if not columns or rows is None:
            return
        self._headers, self._rows, self._label = list(columns), list(rows), label

        # --- Export buttons ---
        btn_row = QWidget()
        br = QHBoxLayout(btn_row)
        br.setContentsMargins(0, 0, 0, 0)

        export_current = QPushButton("📤 Export current...")
        export_current.clicked.connect(lambda: self.exportCurrentRequested.emit(self._headers, self._rows, label))
        br.addWidget(export_current)

        if query_mode:
            export_full = QPushButton("📦 Export full query...")
            export_full.clicked.connect(lambda: self.exportFullQueryRequested.emit(self._current_query or ""))
        else:
            export_full = QPushButton("📦 Export full table...")
            export_full.clicked.connect(lambda: self.exportFullTableRequested.emit(label))
            add_item = QPushButton("🆕 Add new item")
            add_item.clicked.connect(lambda: self.addTableItemRequested.emit(label))
            br.addWidget(add_item)

        br.addWidget(export_full)
        br.addStretch()
        self.layout_.addWidget(btn_row)

        # --- Table setup ---
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(False)

        self._table_widget = table

        # Fill rows
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                item = QTableWidgetItem(str(v))
                if not query_mode:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                table.setItem(i, j, item)

        if query_mode:
            start_row = self._page * self._page_size + 1
            end_row = start_row + len(rows) - 1
            table.setVerticalHeaderLabels([str(n) for n in range(start_row, end_row + 1)])

        self.layout_.addWidget(table)

        # --- Enable editing only in table mode ---
        if not query_mode:
            table.itemChanged.connect(lambda item: self._on_cell_edited(item, label))
        else:
            try:
                table.itemChanged.disconnect()
            except TypeError:
                pass

        # --- Pagination (query mode only) ---
        if query_mode:
            nav = QWidget()
            nl = QHBoxLayout(nav)
            nl.setContentsMargins(0, 0, 0, 0)
            prev_btn = QPushButton("⬅️ Previous")
            next_btn = QPushButton("➡️ Next")

            prev_btn.setEnabled(self._page > 0)
            next_btn.setEnabled(len(rows) == self._page_size)

            prev_btn.clicked.connect(lambda: self.pageChangeRequested.emit(self._page - 1, self._page_size))
            next_btn.clicked.connect(lambda: self.pageChangeRequested.emit(self._page + 1, self._page_size))

            nl.addWidget(prev_btn)
            nl.addWidget(next_btn)
            nl.addStretch()
            self.layout_.addWidget(nav)

    # ------- Editing -------
    def _on_cell_edited(self, item, table_name):
        """Prompt to confirm and emit an update when a cell is edited."""
        row = item.row()
        col = item.column()
        new_value = item.text()
        column_name = self._headers[col]
        old_value = str(self._rows[row][col]) if row < len(self._rows) else None

        if new_value == old_value:
            return

        # Choose identifier (PK value or row index)
        if self._has_primary_key:
            try:
                pk_value = self._rows[row][self._pk_index]
            except Exception:
                pk_value = None
        else:
            pk_value = row  # fallback: use row index

        def confirm_and_emit():
            confirm = QMessageBox.question(
                self,
                "Confirm Update",
                f"Update column '{column_name}' in row {row + 1}?\n\n"
                f"Old value: {old_value}\nNew value: {new_value}",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm == QMessageBox.No:
                self._table_widget.blockSignals(True)
                item.setText(old_value)
                self._table_widget.blockSignals(False)
                return

            # Emit: table, column, pk_or_row, new value
            try:
                self.cellUpdateRequested.emit(table_name, column_name, pk_value, new_value, list(self._rows[row]), list(self._headers))
            except Exception as e:
                print("Error editing cell:", e)


        QTimer.singleShot(0, confirm_and_emit)
