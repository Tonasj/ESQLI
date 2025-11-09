import pytest
from PyQt5.QtWidgets import QApplication, QMessageBox, QPushButton
from PyQt5.QtCore import Qt, QTimer

# ---------------------------
#  EngineSelectDialog tests
# ---------------------------

@pytest.fixture
def fake_app_settings(qtbot):
    """Return a fake QSettings-like object for testing."""
    class FakeSettings(dict):
        def value(self, key, default=None, type=None):
            return self.get(key, default)
        def setValue(self, key, value):
            self[key] = value
    return FakeSettings()

@pytest.fixture
def fake_get_engines(monkeypatch):
    """Patch get_available_engines() to return fake engines."""
    monkeypatch.setattr(
        "core.get_available_engines",
        lambda: {"msexpress": "Microsoft SQL Express", "mysql": "MySQL"}
    )

def test_engine_select_dialog_loads_engines(qtbot, fake_app_settings, fake_get_engines):
    from gui.other_windows.engine_select import EngineSelectDialog

    dlg = EngineSelectDialog(fake_app_settings)
    qtbot.addWidget(dlg)

    # Should populate the combo with engines
    assert dlg.engine_combo.count() == 2
    assert dlg.engine_combo.itemText(0) == "Microsoft SQL Express"
    assert dlg.engine_combo.itemData(0) == "msexpress"

def test_engine_select_dialog_remembers_previous(qtbot, fake_app_settings, fake_get_engines):
    from gui.other_windows.engine_select import EngineSelectDialog

    fake_app_settings["engine"] = "mysql"
    dlg = EngineSelectDialog(fake_app_settings)
    qtbot.addWidget(dlg)

    current_data = dlg.engine_combo.currentData()
    assert current_data == "mysql"

def test_get_selected_engine_returns_key(qtbot, fake_app_settings, fake_get_engines):
    from gui.other_windows.engine_select import EngineSelectDialog

    dlg = EngineSelectDialog(fake_app_settings)
    qtbot.addWidget(dlg)
    dlg.engine_combo.setCurrentIndex(1)
    assert dlg.get_selected_engine() == "mysql"

# ============================================================
#  DatabaseTreePanel tests
# ============================================================

def test_show_databases_populates_tree(qtbot):
    from gui.database_explorer.tree_panel import DatabaseTreePanel

    panel = DatabaseTreePanel()
    qtbot.addWidget(panel)

    panel.show_databases(["master", "testdb"])

    top_items = [panel.tree.topLevelItem(i).text(0) for i in range(panel.tree.topLevelItemCount())]
    # Includes the "Add new database" and two databases
    assert "➕ Add new database..." in top_items
    assert "master" in top_items
    assert "testdb" in top_items

    # Each DB should have a button
    btn = panel.tree.itemWidget(panel.tree.topLevelItem(1), 1)
    assert btn and btn.toolTip() == "Connect to master"


def test_database_button_emits_signal(qtbot):
    from gui.database_explorer.tree_panel import DatabaseTreePanel

    panel = DatabaseTreePanel()
    qtbot.addWidget(panel)
    panel.show_databases(["prod"])

    with qtbot.waitSignal(panel.databaseSelected, timeout=1000) as blocker:
        btn = panel.tree.itemWidget(panel.tree.topLevelItem(1), 1)
        qtbot.mouseClick(btn, Qt.LeftButton)
    assert blocker.args == ["prod"]


def test_show_database_objects_and_double_click(qtbot):
    from gui.database_explorer.tree_panel import DatabaseTreePanel

    panel = DatabaseTreePanel()
    qtbot.addWidget(panel)
    panel.show_database_objects(["users", "orders"])

    # Tree should have a "Tables" node with children
    tables_item = panel.tree.topLevelItem(0)
    assert tables_item.text(0) == "Tables"
    child_names = [tables_item.child(i).text(0) for i in range(tables_item.childCount())]
    assert "users" in child_names
    assert "orders" in child_names

    # Double-click “Add new table…” emits requestAddTable
    add_tbl_item = tables_item.child(0)
    with qtbot.waitSignal(panel.requestAddTable, timeout=1000):
        panel._on_double(add_tbl_item, 0)

    # Double-click normal table emits tableSelected
    tbl_item = tables_item.child(1)
    with qtbot.waitSignal(panel.tableSelected, timeout=1000) as blocker:
        panel._on_double(tbl_item, 0)
    assert blocker.args == ["users"]


# ============================================================
#  TableDesignerPanel tests
# ============================================================

@pytest.fixture
def table_designer(qtbot):
    from gui.database_explorer.table_designer import TableDesignerPanel
    panel = TableDesignerPanel()
    qtbot.addWidget(panel)
    return panel


def test_load_schema_creates_rows(table_designer):
    schema = [
        ("id", "INT", True, True, False),
        ("name", "VARCHAR(255)", False, False, True),
    ]
    table_designer.load_schema(schema)
    assert table_designer.column_table.rowCount() == 3  # includes "Add column" row
    assert table_designer.column_table.item(0, 0).text() == "id"
    assert table_designer.column_table.item(1, 0).text() == "name"
    assert "Add column" in table_designer.column_table.item(2, 0).text()


def test_double_click_add_row_shows_form(table_designer, qtbot):
    schema = [("id", "INT", True, True, False)]
    table_designer.load_schema(schema)
    table_designer.show()                 # ✅ ensure visibility
    qtbot.waitExposed(table_designer)
    last_row = table_designer.column_table.rowCount() - 1
    assert not table_designer.form.isVisible()
    table_designer._maybe_show_form(last_row, 0)
    assert table_designer.form.isVisible()


def test_emit_add_valid_column(table_designer, qtbot):
    table_designer.new_name.setText("new_col")
    table_designer.new_type.setCurrentText("FLOAT")
    with qtbot.waitSignal(table_designer.addColumnRequested, timeout=1000) as blocker:
        table_designer._emit_add()
    assert blocker.args == ["new_col", "FLOAT"]


def test_emit_add_without_name_warns(table_designer, qtbot, monkeypatch):
    # Prevent real QMessageBox dialog
    called = {}
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: called.setdefault("warn", True))
    table_designer.new_name.clear()
    table_designer._emit_add()
    assert called.get("warn")


def test_type_changed_emits_signal(table_designer, qtbot):
    schema = [("id", "INT", True, True, False)]
    table_designer.load_schema(schema)
    with qtbot.waitSignal(table_designer.changeTypeRequested, timeout=1000) as blocker:
        table_designer._on_type_changed(0, "VARCHAR(255)")
    assert blocker.args == ["id", "VARCHAR(255)"]


def test_item_changed_emits_correct_signals(table_designer, qtbot):
    schema = [("id", "INT", True, True, False), ("name", "VARCHAR(255)", False, False, True)]
    table_designer.load_schema(schema)
    table = table_designer.column_table

    # Rename column
    item = table.item(1, 0)
    with qtbot.waitSignal(table_designer.renameColumnRequested, timeout=1000):
        item.setText("new_name")

    # Toggle PK checkbox
    item = table.item(1, 2)
    with qtbot.waitSignal(table_designer.primaryKeyToggled, timeout=1000):
        item.setCheckState(Qt.Checked)

    # Toggle AutoIncrement checkbox
    item = table.item(1, 3)
    with qtbot.waitSignal(table_designer.autoIncrementToggled, timeout=1000):
        item.setCheckState(Qt.Checked)

    # Toggle Nullable checkbox
    item = table.item(1, 4)
    with qtbot.waitSignal(table_designer.nullableToggled, timeout=1000):
        item.setCheckState(Qt.Unchecked)


def test_revert_checkbox_sets_back(table_designer):
    schema = [("id", "INT", True, True, False)]
    table_designer.load_schema(schema)
    # Force a wrong state and revert
    item = table_designer.column_table.item(0, 2)
    item.setCheckState(Qt.Unchecked)
    table_designer._revert_checkbox("id", 2, True)
    assert table_designer.column_table.item(0, 2).checkState() == Qt.Checked

# ============================================================
#  QueryEditorPanel tests
# ============================================================

@pytest.fixture
def query_editor(qtbot, monkeypatch):
    from gui.database_explorer.query_editor import QueryEditorPanel

    # Patch external dependencies
    monkeypatch.setattr("gui.gui_helpers.query_editor_utils.SQLEditor", lambda *a, **kw: DummyEditor())
    monkeypatch.setattr("gui.gui_helpers.query_editor_utils.SQLHighlighter", lambda *a, **kw: DummyHighlighter())
    monkeypatch.setattr("core.file_utils.save_query_to_file", lambda *a, **kw: None)
    monkeypatch.setattr("core.file_utils.open_query_from_file", lambda *a, **kw: None)

    panel = QueryEditorPanel()
    qtbot.addWidget(panel)
    return panel


class DummyEditor:
    def __init__(self):
        self._text = ""
        self._callback = None
        self._changed_callbacks = []
    def toPlainText(self):
        return self._text
    def setPlainText(self, text):
        self._text = text
        for cb in self._changed_callbacks:
            cb()
    def append(self, text):
        self._text += text
    def clear(self):
        self._text = ""
    def document(self):
        return self
    def textChanged(self, cb=None):
        if cb:
            self._changed_callbacks.append(cb)
    def init_completer(self):
        return True


class DummyHighlighter:
    def __init__(self, *a, **kw):
        pass
    def apply_uppercase_keywords(self):
        pass


def test_initial_tab_exists(query_editor):
    assert query_editor.tabs.count() == 1
    assert hasattr(query_editor.tabs.widget(0), "editor")


def test_add_tab_creates_new_editor(query_editor):
    query_editor.add_tab("Extra")
    assert query_editor.tabs.count() == 2
    tab = query_editor.tabs.widget(1)
    assert hasattr(tab, "editor")
    assert hasattr(tab, "highlighter")


def test_set_context_inserts_header_in_empty_editor(query_editor):
    query_editor.set_context("testdb", "users", ["users"])
    editor = query_editor.tabs.widget(0).editor
    text = editor.toPlainText()
    assert "USE testdb;" in text
    assert "-- Current table: `users`" in text


def test_close_tab_removes_tab(query_editor):
    query_editor.add_tab("Temp")
    count_before = query_editor.tabs.count()
    query_editor._close_tab(1)
    assert query_editor.tabs.count() == count_before - 1


def test_emit_run_signal_emitted(query_editor, qtbot):
    tab = query_editor.tabs.widget(0)
    tab.editor.setPlainText("SELECT 1;")
    with qtbot.waitSignal(query_editor.runQueryRequested, timeout=1000) as blocker:
        query_editor._emit_run()
    query, page, size = blocker.args
    assert "SELECT 1" in query
    assert size == 500


def test_show_message_sets_color_and_text(query_editor):
    query_editor.show_message("OK", "ok")
    assert "color" in query_editor.message.styleSheet()
    assert "OK" in query_editor.message.text()


# ============================================================
#  DataPreviewPanel tests
# ============================================================

@pytest.fixture
def data_preview(qtbot):
    from gui.database_explorer.data_preview import DataPreviewPanel
    panel = DataPreviewPanel()
    qtbot.addWidget(panel)
    return panel


def test_show_table_data_creates_table(data_preview):
    cols = ["id", "name"]
    rows = [[1, "Alice"], [2, "Bob"]]
    data_preview.show_table_data(cols, rows, "people")
    assert data_preview._headers == cols
    assert len(data_preview._rows) == 2
    assert data_preview._table_widget.rowCount() == 2


def test_edit_cell_emits_signal(monkeypatch, data_preview, qtbot):
    cols = ["id", "name"]
    rows = [[1, "Alice"]]
    data_preview.show_table_data(cols, rows, "people")
    data_preview.set_primary_key_info(True, 0)

    # Patch QMessageBox to auto-return Yes
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)

    item = data_preview._table_widget.item(0, 1)
    with qtbot.waitSignal(data_preview.cellUpdateRequested, timeout=1000) as blocker:
        item.setText("Alicia")

    args = blocker.args
    assert args[0] == "people"
    assert args[1] == "name"
    assert args[3] == "Alicia"


def test_query_mode_renders_pagination(data_preview):
    cols = ["id"]
    rows = [[i] for i in range(5)]
    data_preview.show_query_results(cols, rows, page=0, page_size=5, query="SELECT *")

    # Flatten widgets recursively
    def find_buttons(layout):
        found = []
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if isinstance(w, QPushButton):
                found.append(w)
            elif hasattr(w, "layout") and callable(w.layout):
                sub = w.layout()
                if sub:
                    found.extend(find_buttons(sub))
        return found

    buttons = find_buttons(data_preview.layout_)
    assert any(isinstance(btn, QPushButton) for btn in buttons)


# ============================================================
#  AddRowDialog tests
# ============================================================

@pytest.fixture
def add_row_dialog(qtbot):
    from gui.other_windows.dialog import AddRowDialog
    columns = [
        ("id", "INT", True, True, False),
        ("name", "VARCHAR(50)", False, False, True),
        ("created", "DATE", False, False, True),
    ]
    dlg = AddRowDialog(None, "users", columns)
    qtbot.addWidget(dlg)
    return dlg


def test_add_row_dialog_skips_identity_field(add_row_dialog):
    vals = add_row_dialog.get_values()
    assert "id" not in vals  # identity skipped
    assert "name" in vals


def test_add_row_dialog_accepts_valid_input(monkeypatch, add_row_dialog):
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Unexpected warning")))
    add_row_dialog.inputs["name"].setText("Alice")
    add_row_dialog._on_accept()
    vals = add_row_dialog.get_values()
    assert vals["name"] == "Alice"


# ============================================================
#  AddNewDialog tests
# ============================================================

@pytest.fixture
def add_new_dialog_table(qtbot):
    from gui.other_windows.dialog import AddNewDialog
    dlg = AddNewDialog(mode="table")
    qtbot.addWidget(dlg)
    return dlg


def test_add_new_dialog_adds_columns(add_new_dialog_table):
    # Add another column dynamically
    before = len(add_new_dialog_table.columns)
    add_new_dialog_table.add_column_row()
    after = len(add_new_dialog_table.columns)
    assert after == before + 1


def test_get_table_definition_returns_expected(add_new_dialog_table):
    # Fill first column row
    name_widget, type_widget, pk_widget, ai_widget, null_widget = add_new_dialog_table.columns[0]
    name_widget.setText("id")
    pk_widget.setChecked(True)
    ai_widget.setChecked(True)
    null_widget.setChecked(False)
    table_name, cols = add_new_dialog_table.get_table_definition()
    assert isinstance(cols, list)
    assert cols[0][0] == "id"
    assert cols[0][2]  # is_pk