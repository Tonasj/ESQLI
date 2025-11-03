import os
from PyQt5.QtWidgets import (
QWidget, QLabel, QVBoxLayout, QComboBox, QPushButton,
QLineEdit, QHBoxLayout, QSplitter, QMessageBox, QRadioButton, QButtonGroup, QFormLayout
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings, QByteArray, Qt, QThread

from core import SQLConnectWorker
from gui.sql_server_explorer import SQLServerSidebar
from gui.database_explorer_window import DatabaseExplorerWindow

class ConnectionWindow(QWidget):
    def __init__(self, icon_path=None):
        super().__init__()
        base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
        config_folder = os.path.join(base_folder, "config")  
        os.makedirs(config_folder, exist_ok=True)  

        gui_settings_path = os.path.join(config_folder, "gui_settings.ini")  
        app_settings_path = os.path.join(config_folder, "app_settings.ini")  

        self.gui_settings = QSettings(gui_settings_path, QSettings.IniFormat)  
        self.app_settings = QSettings(app_settings_path, QSettings.IniFormat)  

        self.icon_path = icon_path  
        self.db_connection = None  
        self.last_error_message = ""  

        self.init_ui()  
        self.restore_window_settings()  

    def init_ui(self):  
        self.setWindowTitle("ESQLI - SQL Interface")  
        self.setGeometry(100, 100, 800, 600)  

        if self.icon_path:  
            self.setWindowIcon(QIcon(self.icon_path))  

        self.layout = QVBoxLayout()  
        self.splitter = QSplitter(Qt.Horizontal)  
        self.layout.addWidget(self.splitter)  
        self.setLayout(self.layout)  

        # Left panel: connection form  
        self.connect_widget = QWidget()  
        form_layout = QFormLayout()  
        form_layout.setLabelAlignment(Qt.AlignLeft)  
        form_layout.setVerticalSpacing(6)  

        self.label = QLabel("Welcome to ESQLI")  
        form_layout.addRow(self.label)  

        self.host_input = QComboBox()  
        self.host_input.setEditable(True)  
        saved_hosts = self.app_settings.value("hosts", ["localhost"])  
        if isinstance(saved_hosts, str):  
            saved_hosts = [saved_hosts]  
        for host in saved_hosts:  
            self.host_input.addItem(host)  
        form_layout.addRow(QLabel("Host:"), self.host_input)  

        # Authentication  
        self.windows_auth_radio = QRadioButton("Windows authentication")
        self.sql_auth_radio = QRadioButton("SQL server authentication")
        self.windows_auth_radio.setChecked(True)

        self.auth_group = QButtonGroup()
        self.auth_group.addButton(self.windows_auth_radio)
        self.auth_group.addButton(self.sql_auth_radio)

        # Wrap radios in a QWidget with QVBoxLayout
        auth_widget = QWidget()
        auth_layout = QVBoxLayout(auth_widget)
        auth_layout.setContentsMargins(0, 0, 0, 0)
        auth_layout.addWidget(self.windows_auth_radio)
        auth_layout.addWidget(self.sql_auth_radio)

        form_layout.addRow(QLabel("Authentication:"), auth_widget)

        self.windows_auth_radio.toggled.connect(self.update_auth_ui)  

        self.username_input = QLineEdit()  
        self.username_input.setDisabled(True)  
        form_layout.addRow(QLabel("Username:"), self.username_input)  

        self.password_input = QLineEdit()  
        self.password_input.setEchoMode(QLineEdit.Password)  
        self.password_input.setDisabled(True)  
        form_layout.addRow(QLabel("Password:"), self.password_input)  

        self.database_input = QLineEdit()  
        self.database_input.setPlaceholderText("Optional (default: master)")  
        form_layout.addRow(QLabel("Database:"), self.database_input)  

        self.button = QPushButton("Connect")  
        self.button.clicked.connect(self.handle_submit)  
        form_layout.addRow(self.button)  

        self.connect_widget.setLayout(form_layout)  
        self.splitter.addWidget(self.connect_widget)  

        # Right panel placeholder  
        self.placeholder_right = QLabel("Connect to a database to see tables")  
        self.placeholder_right.setAlignment(Qt.AlignCenter)  
        self.splitter.addWidget(self.placeholder_right)  

    def update_auth_ui(self):  
        is_windows = self.windows_auth_radio.isChecked()  
        self.username_input.setDisabled(is_windows)  
        self.password_input.setDisabled(is_windows)  
        if is_windows:  
            self.username_input.clear()  
            self.password_input.clear()  

    def handle_submit(self):  
        host = self.host_input.currentText().strip()  
        username = self.username_input.text().strip()  
        password = self.password_input.text().strip()  
        database = self.database_input.text().strip() or "master"  
        windows_auth = self.windows_auth_radio.isChecked()  

        self.label.setText("Connecting...")  
        self.button.setEnabled(False)  
        self.host_input.setDisabled(True)  

        print(f"[DEBUG] Starting connection thread: host={host}, db={database}, windows_auth={windows_auth}")  

        self.thread = QThread()  
        self.worker = SQLConnectWorker(host, database, username, password, windows_auth)  
        self.worker.moveToThread(self.thread)  

        self.thread.started.connect(self.worker.run)  
        self.worker.finished.connect(self.on_connection_success)  
        self.worker.error.connect(self.on_connection_error)  

        self.worker.finished.connect(self.thread.quit)  
        self.worker.finished.connect(self.worker.deleteLater)  
        self.worker.error.connect(self.thread.quit)  
        self.worker.error.connect(self.worker.deleteLater)  
        self.thread.finished.connect(self.thread.deleteLater)  

        self.thread.start()  

    def on_connection_success(self, connection):  
        self.db_connection = connection  
        print("[DEBUG] Connected:", connection)  
        self.label.setText("Connected successfully!")  
        self.button.setEnabled(True)  
        self.host_input.setDisabled(False)  

        # Show sidebar
        self.show_sidebar()

    def on_connection_error(self, error_msg):
        self.last_error_message = error_msg
        self.label.setText("Connection failed!")
        self.button.setEnabled(True)
        self.host_input.setDisabled(False)
        QMessageBox.critical(self, "Connection Error", f"Failed to connect:\n{error_msg}")

    def show_sidebar(self):  
        if not self.db_connection:  
            print("[ERROR] Cannot show sidebar: db_connection is None")  
            return  

        try:  
            if hasattr(self, 'placeholder_right'):  
                self.placeholder_right.setParent(None)  
                del self.placeholder_right  
            if hasattr(self, 'sidebar'):  
                self.sidebar.setParent(None)  
                del self.sidebar  

            self.sidebar = SQLServerSidebar(
                self.db_connection, 
                database_selected_callback=self.open_database_explorer
            )
            self.splitter.addWidget(self.sidebar)  
            self.splitter.setSizes([300, 200])  
            print("[DEBUG] Sidebar shown successfully")  

        except Exception as e:  
            print(f"[ERROR] Failed to create sidebar: {e}")  
            QMessageBox.critical(self, "Sidebar Error", f"Failed to create sidebar:\n{e}")  

    def closeEvent(self, event):  
        self.save_window_settings()  
        super().closeEvent(event)  

    def save_window_settings(self):  
        self.gui_settings.setValue("geometry", self.saveGeometry())  

    def restore_window_settings(self):  
        geometry = self.gui_settings.value("geometry")  
        if geometry:  
            if isinstance(geometry, QByteArray):  
                self.restoreGeometry(geometry)  
            else:  
                self.restoreGeometry(QByteArray(geometry))

    def open_database_explorer(self, db_name):
        # If no open_explorers list, create it
        if not hasattr(self, 'open_explorers'):
            self.open_explorers = []

        # Reuse the first explorer if it exists
        if self.open_explorers:
            explorer = self.open_explorers[0]
            explorer.load_database_data(self.db_connection, db_name)
            explorer.raise_()  # bring to front
            explorer.activateWindow()
        else:
            # fallback (should not happen if gui_runner sets it up)
            explorer = DatabaseExplorerWindow(self.db_connection, db_name, self.gui_settings)
            self.open_explorers.append(explorer)
            explorer.show()

        self.save_window_settings()
        self.close()