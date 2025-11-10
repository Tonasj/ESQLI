from PyQt5.QtWidgets import (
QWidget, QVBoxLayout, QHBoxLayout, 
QPushButton, QLabel, QTabWidget, 
QWidget as QtWidget, QCheckBox,
QSizePolicy)
from PyQt5.QtCore import pyqtSignal, Qt
from gui.gui_helpers.query_editor_utils import SQLHighlighter, SQLEditor
from core.file_utils import save_query_to_file, open_query_from_file


class QueryEditorPanel(QWidget):
    runQueryRequested = pyqtSignal(str, int, int)  # query, page, page_size
    openCommonQueriesRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._context = {"db": None, "table": None, "tables": []}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 0)
        layout.setSpacing(2)

        # Buttons
        btn_row = QHBoxLayout()
        run_btn = QPushButton("▶️ Run Query")
        new_tab_btn = QPushButton("➕ New Query Tab")
        common_btn = QPushButton("❔ Common SQL Queries")
        warning_label = QPushButton("⚠️")
        warning_label.setToolTip(
            "Queries may execute in parts.\n"
            "If one statement fails (like dropping a table twice), others may still run successfully.\n"
            "The output may show as failed even if earlier statements executed.\n"
            "Make sure to separate statements with ';'"
        )
        warning_label.setFlat(True)
        warning_label.setFocusPolicy(Qt.NoFocus)
        warning_label.setCursor(Qt.WhatsThisCursor)  # Optional: nice visual hint
        warning_label.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: orange;
                font-size: 12pt;
            }
            QPushButton:hover {
                color: red;
            }
        """)
        warning_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.auto_context_chk = QCheckBox("Auto-use active database")
        self.auto_context_chk.setChecked(True)
        self.auto_context_chk.setToolTip("When enabled, automatically update editors with the active database and table context")
        self.auto_context_chk.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn_row.addWidget(run_btn)
        btn_row.addWidget(new_tab_btn)
        btn_row.addWidget(warning_label)
        btn_row.addStretch()
        btn_row.addWidget(common_btn)
        layout.addLayout(btn_row)
        layout.addWidget(self.auto_context_chk)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        layout.addWidget(self.tabs)

        # Message label (global fallback)
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)

        # Connections
        run_btn.clicked.connect(self._emit_run)
        new_tab_btn.clicked.connect(lambda: self.add_tab("New Query"))
        common_btn.clicked.connect(self.openCommonQueriesRequested.emit)

        # Start with one tab
        self.add_tab("Query")

    # ------- Public API -------
    def set_context(self, db_name=None, table_name=None, tables=None):
        """Update database/table context and refresh autocomplete in all editors."""
        if not getattr(self, "auto_context_chk", None) or not self.auto_context_chk.isChecked():
            # skip automatic context updates
            return
        
        old_context = dict(self._context)
        self._context.update({"db": db_name, "table": table_name, "tables": tables or []})

        contextual_header = ""
        if db_name:
            contextual_header += f"USE {db_name};\n"
        if table_name:
            contextual_header += f"-- Current table: `{table_name}`\n"

        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            editor = getattr(tab, "editor", None)
            if editor is None:
                continue

            current_text = editor.toPlainText().strip()

            # Case 1: Empty editor → fill it
            if not current_text:
                editor.setPlainText(contextual_header)

            # Case 2: It already had the *previous* context → replace with the new one
            elif old_context["db"] and current_text.startswith(f"USE {old_context['db']}"):
                lines = current_text.splitlines()
                rest = "\n".join(line for line in lines if not line.lower().startswith(("use ", "-- current table:")))
                editor.setPlainText(contextual_header + rest.strip())

            # Always refresh autocomplete
            try:
                editor.init_completer()
            except Exception:
                pass

    def show_message(self, text: str, kind: str = "info"):
        """Display query result or error message only in the active tab."""
        color = {"ok": "green", "warn": "orange", "err": "red"}.get(kind, "#333")

        self.message.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.message.setText(text)

    # ------- Internals -------
    def add_tab(self, title="Query"):
        # Create a new SQL query editor tab, like the original UI.
        tab = QtWidget()
        lo = QVBoxLayout(tab); lo.setContentsMargins(0,0,0,0)

        # Editor
        def get_tables():
            return list(self._context.get("tables") or [])

        editor = SQLEditor(get_table_names_callback=get_tables)
        highlighter = SQLHighlighter(editor.document(), editor)
        editor.textChanged.connect(highlighter.apply_uppercase_keywords)

        lo.addWidget(editor)

        # Save/Open row
        row = QHBoxLayout()
        save_btn = QPushButton("💾 Save Query")
        open_btn = QPushButton("📂 Open Query")
        save_btn.setToolTip("Save the current SQL query to a file")
        open_btn.setToolTip("Open a SQL file into this editor")
        save_btn.clicked.connect(lambda: save_query_to_file(self, editor))
        open_btn.clicked.connect(lambda: open_query_from_file(self, editor))
        row.addWidget(save_btn); row.addWidget(open_btn); row.addStretch()
        lo.addLayout(row)

        # Store refs on tab
        tab.editor = editor
        tab.highlighter = highlighter

        # Add to tabs
        self.tabs.addTab(tab, title)
        self.tabs.setCurrentWidget(tab)

        # Prefill contextual header & init completer
        self.set_context(
            db_name=self._context.get("db"),
            table_name=self._context.get("table"),
            tables=self._context.get("tables"),
        )

        # Tabs closability like original
        self.tabs.setTabsClosable(self.tabs.count() > 1)

    def _close_tab(self, index):
        if self.tabs.count() > 1:
            w = self.tabs.widget(index)
            w.deleteLater()
            self.tabs.removeTab(index)
        else:
            tab = self.tabs.widget(0)
            tab.editor.clear()
        self.tabs.setTabsClosable(self.tabs.count() > 1)

    def _emit_run(self):
        tab = self.tabs.currentWidget()
        if tab is None or not hasattr(tab, "editor"):
            return
        query = tab.editor.toPlainText()
        self.runQueryRequested.emit(query, 0, 500)
