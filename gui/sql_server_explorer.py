from PyQt5.QtWidgets import QWidget, QTreeWidget, QVBoxLayout, QTreeWidgetItem

class SQLServerSidebar(QWidget):
    def __init__(self, connection):
        super().__init__()
        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("SQL Server Explorer")
        layout.addWidget(self.tree)

        self.conn = connection
        self.load_structure()

    def load_structure(self):
        root = QTreeWidgetItem(["Server"])
        self.tree.addTopLevelItem(root)

        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sys.databases")
        for (db_name,) in cursor.fetchall():
            QTreeWidgetItem(root, [db_name])

        self.tree.expandAll()
