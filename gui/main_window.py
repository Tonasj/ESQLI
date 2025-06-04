import os
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QComboBox, QPushButton,
    QLineEdit, QHBoxLayout, QSplitter, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings, QByteArray, Qt, QThread

from core import SQLConnectWorker
from gui.sql_server_explorer import SQLServerSidebar

class ESQLIMainWindow(QWidget):
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

        self.connect_widget = QWidget()
        form_layout = QVBoxLayout()

        self.label = QLabel("Welcome to ESQLI")
        form_layout.addWidget(self.label)

        self.host_input = QComboBox()
        self.host_input.setEditable(True)
        saved_hosts = self.app_settings.value("hosts", ["localhost"])
        if isinstance(saved_hosts, str):
            saved_hosts = [saved_hosts]
        for host in saved_hosts:
            self.host_input.addItem(host)
        form_layout.addWidget(QLabel("Host:"))
        form_layout.addWidget(self.host_input)

        

        self.windows_auth_radio = QRadioButton("Windows authentication")
        self.sql_auth_radio = QRadioButton("SQL server authentication")
        self.windows_auth_radio.setChecked(True)

        self.auth_group = QButtonGroup()
        self.auth_group.addButton(self.windows_auth_radio)
        self.auth_group.addButton(self.sql_auth_radio)

        windows_auth_layout = QHBoxLayout()
        windows_auth_layout.addWidget(self.windows_auth_radio)
        form_layout.addLayout(windows_auth_layout)

        sql_auth_layout = QHBoxLayout()
        sql_auth_layout.addWidget(self.sql_auth_radio)
        form_layout.addLayout(sql_auth_layout)

        self.windows_auth_radio.toggled.connect(self.update_auth_ui)

        self.username_input = QLineEdit()
        form_layout.addWidget(QLabel("Username:"))
        form_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addWidget(QLabel("Password:"))
        form_layout.addWidget(self.password_input)

        self.database_input = QLineEdit()
        self.database_input.setPlaceholderText("Optional (default: master)")
        form_layout.addWidget(QLabel("Database:"))
        form_layout.addWidget(self.database_input)

        self.button = QPushButton("Connect")
        self.button.clicked.connect(self.handle_submit)
        form_layout.addWidget(self.button)

        self.connect_widget.setLayout(form_layout)
        self.splitter.addWidget(self.connect_widget)

        self.update_auth_ui()
        self.last_error_message = ""

    def handle_submit(self):
        host = self.host_input.currentText().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        database = self.database_input.text().strip() or "master"
        windows_auth = self.windows_auth_radio.isChecked()

        self.label.setText("Connecting...")

        self.thread = QThread()
        self.worker = SQLConnectWorker(host, database, username, password, windows_auth)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_connection_success)
        self.worker.error.connect(self.on_connection_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

        self.thread.finished.connect(lambda: setattr(self, 'thread', None))
        self.thread.finished.connect(lambda: setattr(self, 'worker', None))

    def on_connection_success(self, connection):
        self.db_connection = connection
        self.label.setText("Connected successfully!")
        self.show_sidebar()

    def on_connection_error(self, error_msg):
        self.last_error_message = error_msg
        self.label.setText("Failed to connect")
        self.button.setEnabled(True)

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Connection Error")
        dlg.setIcon(QMessageBox.Critical)
        dlg.setText("Failed to connect to the database.")
        dlg.setInformativeText(error_msg)
        dlg.exec_()

    def update_auth_ui(self):
        if self.windows_auth_radio.isChecked():
            self.username_input.setDisabled(True)
            self.password_input.setDisabled(True)
        else:
            self.username_input.setDisabled(False)
            self.password_input.setDisabled(False)

    def show_sidebar(self):
        if self.db_connection:
            self.sidebar = SQLServerSidebar(self.db_connection)
            self.splitter.addWidget(self.sidebar)
            self.splitter.setSizes([250, 550])  # Adjust as needed

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
