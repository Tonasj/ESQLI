import os
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QComboBox, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings, QByteArray

from core import connect_to_sql

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

        self.init_ui()
        self.restore_window_settings()

    def init_ui(self):
        self.setWindowTitle("ESQLI - SQL Interface")
        self.setGeometry(100, 100, 600, 400)

        if self.icon_path:
            self.setWindowIcon(QIcon(self.icon_path))

        layout = QVBoxLayout()

        self.label = QLabel("Welcome to ESQLI")
        layout.addWidget(self.label)

        self.host_input = QComboBox()
        self.host_input.setEditable(True)

        saved_hosts = self.app_settings.value("hosts", ["localhost"])
        if isinstance(saved_hosts, str):
            saved_hosts = [saved_hosts]

        for host in saved_hosts:
            self.host_input.addItem(host)

        layout.addWidget(self.host_input)

        self.button = QPushButton("Submit")
        self.button.clicked.connect(self.handle_submit)
        layout.addWidget(self.button)

        self.setLayout(layout)

    def handle_submit(self):
        host = self.host_input.currentText()

        try:
            connect_to_sql(host)
            self.label.setText(f"Connected to: {host}")
        except Exception as e:
            self.label.setText(f"Failed to connect: {e}")

        hosts = [self.host_input.itemText(i) for i in range(self.host_input.count())]
        if host not in hosts:
            self.host_input.addItem(host)
            hosts.append(host)
            self.app_settings.setValue("hosts", hosts)

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
