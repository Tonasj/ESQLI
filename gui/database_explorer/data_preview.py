from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QPushButton, QTableWidget, QTableWidgetItem, 
)
from PyQt5.QtCore import pyqtSignal


class DataPreviewPanel(QWidget):
    exportCurrentRequested = pyqtSignal(list, list, str)  # headers, rows(list of lists), label
    exportFullTableRequested = pyqtSignal(str)            # table name
    exportFullQueryRequested = pyqtSignal(str)            # full SQL text
    pageChangeRequested = pyqtSignal(int, int)            # new_page, page_size

    def __init__(self):
        super().__init__()
        self._build()
        self._headers = []
        self._rows = []
        self._label = ""
        self._page = 0
        self._page_size = 500
        self._current_query = None

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

        # Export row
        btn_row = QWidget(); br = QHBoxLayout(btn_row); br.setContentsMargins(0,0,0,0)
        export_current = QPushButton("📤 Export current...")
        export_current.clicked.connect(lambda: self.exportCurrentRequested.emit(self._headers, self._rows, label))
        br.addWidget(export_current)

        if query_mode:
            export_full = QPushButton("📦 Export full query...")
            export_full.clicked.connect(lambda: self.exportFullQueryRequested.emit(self._current_query or ""))
        else:
            export_full = QPushButton("📦 Export full table...")
            export_full.clicked.connect(lambda: self.exportFullTableRequested.emit(label))
        br.addWidget(export_full); br.addStretch()
        self.layout_.addWidget(btn_row)

        # Table
        table = QTableWidget(); table.setColumnCount(len(columns)); table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        # Insert rows (with correct global numbering)
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                item = QTableWidgetItem(str(v))
                table.setItem(i, j, item)

        if query_mode:
            start_row = self._page * self._page_size + 1
            end_row = start_row + len(rows) - 1
            table.setVerticalHeaderLabels([str(n) for n in range(start_row, end_row + 1)])

        self.layout_.addWidget(table)

        # Pagination (only for query mode)
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