import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHeaderView, QMenu, QAction
)
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QIcon


class DatabaseTreePanel(QWidget):
    databaseSelected = pyqtSignal(str)
    tableSelected = pyqtSignal(str)
    requestAddDatabase = pyqtSignal()
    requestAddTable = pyqtSignal()
    importTableRequested = pyqtSignal(str)
    exportTableRequested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        assets_dir = os.path.join(base_dir, "assets")
        import_icon_path = os.path.join(assets_dir, "import-content.png")
        export_icon_path = os.path.join(assets_dir, "export-content.png")
        self.import_icon = QIcon(import_icon_path)
        self.export_icon = QIcon(export_icon_path)
        self.tree = QTreeWidget()
        layout.addWidget(self.tree)

        self.tree.itemDoubleClicked.connect(self._on_double)

        # --- Enable custom right-click context menu ---
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)

    # ------- Public API -------
    def show_databases(self, databases):
        self.tree.clear()
        self.tree.setHeaderLabels(["Databases", "Action"])

        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.resizeSection(1, 40)

        add_db_item = QTreeWidgetItem(["➕ Add new database..."])
        add_db_item.setData(0, Qt.UserRole, "add_new_database")
        f = add_db_item.font(0)
        f.setItalic(True)
        add_db_item.setFont(0, f)
        self.tree.addTopLevelItem(add_db_item)

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
        t = item.data(0, Qt.UserRole)
        name = item.text(0)

        if t == "add_new_database":
            self.requestAddDatabase.emit()
        elif t == "add_new_table":
            self.requestAddTable.emit()
        elif t == "table":
            self.tableSelected.emit(name)

    def _on_context_menu(self, pos: QPoint):
        """Right-click context menu handler"""
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        import_icon = self.import_icon
        export_icon = self.export_icon

        item_type = item.data(0, Qt.UserRole)
        item_name = item.text(0)

        # Only show menu for table items
        if item_type == "table":
            menu = QMenu(self)

            import_action = QAction(import_icon, "Import table data", self)
            export_action = QAction(export_icon, "Export table data", self)

            import_action.triggered.connect(lambda: self.importTableRequested.emit(item_name))
            export_action.triggered.connect(lambda: self.exportTableRequested.emit(item_name))

            menu.addAction(import_action)
            menu.addAction(export_action)
            menu.exec_(self.tree.viewport().mapToGlobal(pos))
