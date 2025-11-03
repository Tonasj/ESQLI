import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit
)
from PyQt5.QtCore import QSettings, Qt, QByteArray
from gui.integrated_console import IntegratedConsole, redirect_std

class DatabaseExplorerView(QWidget):
    def __init__(self, connection=None, database=None):
        super().__init__()
        self.conn = connection
        self.selected_database = database

        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
        config_folder = os.path.join(base_folder, "config")  
        os.makedirs(config_folder, exist_ok=True)
        
        gui_settings_path = os.path.join(config_folder, "gui_settings.ini")  
        app_settings_path = os.path.join(config_folder, "app_settings.ini")  

        self.gui_settings = QSettings(gui_settings_path, QSettings.IniFormat)  
        self.app_settings = QSettings(app_settings_path, QSettings.IniFormat)  

        self.setWindowTitle(f"Database Explorer - {database}" if database else "Database Explorer")
        self.setGeometry(100, 100, 1000, 600)

        if self.gui_settings:
            self.restore_window_settings()
        main_layout = QVBoxLayout(self)
        vertical_splitter = QSplitter(Qt.Vertical)
        top_splitter = QSplitter(Qt.Horizontal)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Database Objects"])
        top_splitter.addWidget(self.tree)
        top_splitter.setSizes([250, 750])

        self.content_area = QTextEdit()
        self.content_area.setReadOnly(True)
        top_splitter.addWidget(self.content_area)

        vertical_splitter.addWidget(top_splitter)

        self.console = IntegratedConsole()
        vertical_splitter.addWidget(self.console)
        vertical_splitter.setSizes([400, 200])

        main_layout.addWidget(vertical_splitter)

        redirect_std(self.console)

        self.populate_tree_structure()

        if self.conn and self.selected_database:
            self.load_database_data(self.conn, self.selected_database)

    def populate_tree_structure(self):
        """Just create empty folders without loading tables yet."""
        self.tables_item = QTreeWidgetItem(["Tables"])
        self.views_item = QTreeWidgetItem(["Views"])
        self.procedures_item = QTreeWidgetItem(["Stored Procedures"])

        self.tree.addTopLevelItem(self.tables_item)
        self.tree.addTopLevelItem(self.views_item)
        self.tree.addTopLevelItem(self.procedures_item)
        self.tree.expandAll()

    def load_database_data(self, connection, database):
        """Load actual tables/views/procedures after connection."""
        self.conn = connection
        self.selected_database = database
        self.setWindowTitle(f"Database Explorer - {database}")

        cursor = self.conn.cursor()
        cursor.execute(f"USE [{self.selected_database}]")

        # Load tables
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        for (table_name,) in cursor.fetchall():
            QTreeWidgetItem(self.tables_item, [table_name])

        # Optionally load views and procedures in similar way
        self.tree.expandAll()

    def closeEvent(self, event):
        self.save_window_settings()
        super().closeEvent(event)

    def save_window_settings(self):
        if self.gui_settings:
            self.gui_settings.setValue("explorer_geometry", self.saveGeometry())

    def restore_window_settings(self):
        if self.gui_settings:
            geometry = self.gui_settings.value("explorer_geometry")
            if geometry:
                if isinstance(geometry, QByteArray):
                    self.restoreGeometry(geometry)
                else:
                    self.restoreGeometry(QByteArray(geometry))