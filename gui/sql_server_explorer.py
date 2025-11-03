from PyQt5.QtWidgets import (QWidget, QTreeWidget, QVBoxLayout, 
QTreeWidgetItem, QPushButton, QTreeWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt

class SQLServerSidebar(QWidget):
    def __init__(self, connection, database_selected_callback=None):
        """
        :param connection: Active DB connection
        :param database_selected_callback: function to call with db name when user clicks connect
        """
        super().__init__()
        self.conn = connection
        self.database_selected_callback = database_selected_callback

        self.setMinimumWidth(200)

        layout = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Databases", "Action"])
        layout.addWidget(self.tree)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.load_structure()

    def load_structure(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sys.databases")
        for (db_name,) in cursor.fetchall():
            # Create top-level item for each database
            item = QTreeWidgetItem([db_name])
            self.tree.addTopLevelItem(item)
            
            # Create a small connect button for this database
            btn = QPushButton("🔗")
            btn.setMaximumWidth(30)
            btn.setToolTip(f"Connect to {db_name}")
            
            # Store db_name in lambda default arg
            btn.clicked.connect(lambda _, db=db_name: self.select_database(db))
            
            self.tree.setItemWidget(item, 1, btn)

        self.tree.expandAll()

    def select_database(self, db_name):
        print(f"Selected database: {db_name}")
        if self.database_selected_callback:
            self.database_selected_callback(db_name)