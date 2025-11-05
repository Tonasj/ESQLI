from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QHeaderView
from PyQt5.QtCore import pyqtSignal, Qt


class DatabaseTreePanel(QWidget):
    databaseSelected = pyqtSignal(str)
    tableSelected = pyqtSignal(str)
    requestAddDatabase = pyqtSignal()
    requestAddTable = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree = QTreeWidget()
        layout.addWidget(self.tree)

        self.tree.itemDoubleClicked.connect(self._on_double)

    # ------- Public API -------
    def show_databases(self, databases):
        """Show list of databases with a 🔗 connect button beside each."""
        self.tree.clear()
        self.tree.setHeaderLabels(["Databases", "Action"])

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 40)

        # “Add new database …” entry
        add_db_item = QTreeWidgetItem(["➕ Add new database..."])
        add_db_item.setData(0, Qt.UserRole, "add_new_database")
        f = add_db_item.font(0)
        f.setItalic(True)
        add_db_item.setFont(0, f)
        self.tree.addTopLevelItem(add_db_item)

        # Regular database entries with buttons
        for name in databases:
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.UserRole, "database")
            self.tree.addTopLevelItem(item)

            btn = QPushButton("🔗")
            btn.setToolTip(f"Connect to {name}")
            btn.setMaximumWidth(30)
            btn.clicked.connect(lambda _, db=name: self.databaseSelected.emit(db))
            self.tree.setItemWidget(item, 1, btn)

        self.tree.expandAll()

    def show_database_objects(self, tables):
        """Show objects (tables, views, procedures) of a selected database."""
        self.tree.clear()
        self.tree.setHeaderLabels(["Database Objects"])

        tables_item = QTreeWidgetItem(["Tables"])
        self.tree.addTopLevelItem(tables_item)

        add_tbl = QTreeWidgetItem(tables_item, ["➕ Add new table..."])
        add_tbl.setData(0, Qt.UserRole, "add_new_table")
        f = add_tbl.font(0)
        f.setItalic(True)
        add_tbl.setFont(0, f)

        for t in tables:
            ti = QTreeWidgetItem(tables_item, [t])
            ti.setData(0, Qt.UserRole, "table")

        self.tree.expandAll()

    def clear(self):
        self.tree.clear()

    # ------- Internals -------
    def _on_double(self, item, column):
        """Handle double-click only for 'add new …' and table items."""
        t = item.data(0, Qt.UserRole)
        name = item.text(0)

        if t == "add_new_database":
            self.requestAddDatabase.emit()
        elif t == "add_new_table":
            self.requestAddTable.emit()
        elif t == "table":
            self.tableSelected.emit(name)
