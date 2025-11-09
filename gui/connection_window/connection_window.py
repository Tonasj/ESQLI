import os
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QComboBox, QPushButton,
    QLineEdit, QSplitter, QMessageBox, QRadioButton,
    QButtonGroup, QFormLayout, QDesktopWidget, QHBoxLayout, QCheckBox,
    QStyledItemDelegate, QStyle, QListView, QStyleOptionViewItem
)
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, QThread, QRect, pyqtSignal, QTimer, QEvent

from core import SQLConnectWorker
from gui.database_explorer.main_window import DatabaseExplorerWindow
from gui.gui_helpers.window_utils import setup_app_settings, restore_window_settings, save_window_settings

from cryptography.fernet import Fernet

PLACEHOLDER_TEXT = "Select host"
LAST_USED_HOST_KEY = "last_used_host"

# --- Encryption utilities ---
def get_encryption_key():
    """
    Ensure there is a persistent encryption key for passwords.
    """
    from gui.gui_helpers.window_utils import find_project_root
    base_folder = find_project_root()
    config_folder = os.path.join(base_folder, "config")
    os.makedirs(config_folder, exist_ok=True)
    key_path = os.path.join(config_folder, "encryption.key")

    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read()

    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    return key


def encrypt_password(password: str) -> str:
    if not password:
        return ""
    key = get_encryption_key()
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    if not encrypted:
        return ""
    try:
        key = get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return ""

# ---------------- Delete button delegate ----------------
class DeleteButtonDelegate(QStyledItemDelegate):
    delete_requested = pyqtSignal(int)

    _BTN_W = 18
    _BTN_H = 16
    _BTN_MARGINS = 4

    def _btn_rect(self, option: 'QStyleOptionViewItem') -> QRect:
        h = max(self._BTN_H, option.rect.height() - 2 * self._BTN_MARGINS)
        y = option.rect.y() + (option.rect.height() - h) // 2
        x = option.rect.right() - (self._BTN_W + 4)
        return QRect(x, y, self._BTN_W, h)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.row() == 0:
            return
        btn = self._btn_rect(option)
        painter.save()
        if option.state & QStyle.State_MouseOver:
            painter.fillRect(btn, option.palette.highlight().color().lighter(170))
        painter.drawText(btn, Qt.AlignCenter, "×")
        painter.restore()

# ---------------- Connection window ----------------
class ConnectionWindow(QWidget):
    def __init__(self, icon_path=None):
        super().__init__()
        self.gui_settings, self.app_settings = setup_app_settings()
        self.icon_path = icon_path
        self.window_name = "ConnectionWindow"
        self.db_connection = None
        self.last_error_message = ""

        self.init_ui()
        restore_window_settings(self)

    # ---------------- UI ----------------
    def init_ui(self):
        self.setWindowTitle("ESQLI - SQL Interface")
        self.resize(500, 240)
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        if self.icon_path:
            self.setWindowIcon(QIcon(self.icon_path))

        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # -------- Form Layout --------
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setVerticalSpacing(6)

        self.label = QLabel("Welcome to ESQLI")
        form.addRow(self.label)

        # -------- Host input with per-item delete --------
        self.host_input = QComboBox()
        self.host_input.setEditable(True)
        self.host_input.setInsertPolicy(QComboBox.NoInsert)
        self.host_input.setMinimumWidth(260)

        # --- Assign a custom QListView first ---
        list_view = QListView()
        list_view.setMouseTracking(True)
        list_view.setUniformItemSizes(True)
        list_view.viewport().setAttribute(Qt.WA_Hover, True) 
        list_view.setStyleSheet("QListView::item { padding-right: 24px; }")  # space for ×
        self.host_input.setView(list_view)

        # --- Create delegate ---
        self.host_delegate = DeleteButtonDelegate(self.host_input.view())
        self.host_delegate.delete_requested.connect(self.delete_host_by_index)
        self.host_input.view().setItemDelegate(self.host_delegate)

        # --- Intercept clicks on the popup ---
        list_view.viewport().installEventFilter(self)

        # -------- Model and host loading --------
        saved_hosts = self.app_settings.value("hosts", [])
        if isinstance(saved_hosts, str):
            saved_hosts = [saved_hosts]

        # Filter out empties and any accidental placeholder that may have been saved previously
        saved_hosts = [
            h for h in saved_hosts
            if isinstance(h, str) and h.strip() and h.strip() != PLACEHOLDER_TEXT
        ]

        self.host_model = QStandardItemModel(self.host_input)
        self.host_input.setModel(self.host_model)

        # Placeholder first row (clicking it clears the line edit)
        placeholder = QStandardItem(PLACEHOLDER_TEXT)
        placeholder.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.host_model.appendRow(placeholder)

        # Populate saved hosts (dedup in case settings had dupes)
        seen = set()
        for h in saved_hosts:
            key = h.casefold()
            if key in seen:
                continue
            seen.add(key)
            self.host_model.appendRow(QStandardItem(h))

        # --- Load last used host ---
        last_used_host = self.app_settings.value(LAST_USED_HOST_KEY, "").strip()
        matched_index = None

        if last_used_host:
            for row in range(1, self.host_model.rowCount()):
                item = self.host_model.item(row)
                if item and item.text().strip().casefold() == last_used_host.casefold():
                    matched_index = row
                    break

        if matched_index is not None:
            self.host_input.setCurrentIndex(matched_index)
            self.host_input.setCurrentText(last_used_host)
        else:
            # Start at placeholder but keep the line edit empty
            self.host_input.setCurrentIndex(0)
            self.host_input.setCurrentText("")

        # Save typed host automatically on focus loss
        self.host_input.lineEdit().editingFinished.connect(self.save_host_on_focus_loss)
        # If placeholder selected, clear text
        self.host_input.currentIndexChanged.connect(self.on_host_changed)

        form.addRow(QLabel("Host:"), self.host_input)

        # --- Authentication type ---
        self.windows_auth_radio = QRadioButton("Windows authentication")
        self.sql_auth_radio = QRadioButton("SQL server authentication")
        self.windows_auth_radio.setChecked(True)
        self.auth_group = QButtonGroup()
        self.auth_group.addButton(self.windows_auth_radio)
        self.auth_group.addButton(self.sql_auth_radio)
        auth_widget = QWidget()
        auth_layout = QVBoxLayout(auth_widget)
        auth_layout.setContentsMargins(0, 0, 0, 0)
        auth_layout.addWidget(self.windows_auth_radio)
        auth_layout.addWidget(self.sql_auth_radio)
        form.addRow(QLabel("Authentication:"), auth_widget)
        self.windows_auth_radio.toggled.connect(self.update_auth_ui)

        # --- Username + Remember ---
        user_row = QVBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setDisabled(True)
        self.remember_username_check = QCheckBox("Remember username")
        user_row.addWidget(self.username_input)
        user_row.addWidget(self.remember_username_check)
        form.addRow(QLabel("Username:"), user_row)

        # --- Password + Remember ---
        password_row = QVBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setDisabled(True)
        self.remember_password_check = QCheckBox("Remember password")
        self.remember_password_check.setEnabled(False)
        password_row.addWidget(self.password_input)
        password_row.addWidget(self.remember_password_check)
        form.addRow(QLabel("Password:"), password_row)

        # Restore saved credentials
        saved_username = self.app_settings.value("saved_username", "")
        saved_password_enc = self.app_settings.value("saved_password_enc", "")
        remember_username = self.app_settings.value("remember_username", False, type=bool)
        remember_password = self.app_settings.value("remember_password", False, type=bool)

        if remember_username:
            self.username_input.setText(saved_username)
            self.remember_username_check.setChecked(True)

        if remember_password:
            self.password_input.setText(decrypt_password(saved_password_enc))
            self.remember_password_check.setChecked(True)

        # --- Connect button ---
        self.button = QPushButton("Connect")
        self.button.clicked.connect(self.handle_submit)
        form.addRow(self.button)

        # Wrap up
        container = QWidget()
        container.setLayout(form)
        splitter.addWidget(container)

        self.update_auth_ui()

    # ---------------- Authentication UI ----------------
    def update_auth_ui(self):
        is_windows = self.windows_auth_radio.isChecked()

        self.username_input.setDisabled(is_windows)
        self.password_input.setDisabled(is_windows)
        self.remember_username_check.setEnabled(not is_windows)
        self.remember_password_check.setEnabled(not is_windows)

        if is_windows:
            self.username_input.clear()
            self.password_input.clear()
            self.remember_username_check.setChecked(False)
            self.remember_password_check.setChecked(False)

    # ---------------- Host persistence ----------------
    def get_saved_hosts(self):
        hosts = self.app_settings.value("hosts", [])
        if isinstance(hosts, str):
            hosts = [hosts]
        return hosts

    def save_hosts(self, hosts):
        self.app_settings.setValue("hosts", hosts)

    def on_host_changed(self, index: int):
        """Clear the editable text if placeholder selected."""
        if index == 0:
            # show blank in the line edit when user selects placeholder
            QTimer.singleShot(0, lambda: self.host_input.lineEdit().clear())

    def save_host_on_focus_loss(self):
        """Automatically save entered host when leaving the field."""
        host = self.host_input.currentText().strip()
        if not host or host == PLACEHOLDER_TEXT:
            return

        # Case-insensitive dedupe against settings
        hosts = self.get_saved_hosts()
        hosts_clean = [
            h for h in hosts
            if isinstance(h, str) and h.strip() and h.strip() != PLACEHOLDER_TEXT
        ]
        if host.casefold() in (h.casefold() for h in hosts_clean):
            return

        # Persist
        hosts_clean.append(host)
        self.save_hosts(hosts_clean)

        # Also ensure not already in the model (case-insensitive)
        for row in range(self.host_model.rowCount()):
            item = self.host_model.item(row)
            if item and item.text().strip().casefold() == host.casefold():
                break
        else:
            self.host_model.appendRow(QStandardItem(host))


    def delete_host_by_index(self, row_index: int):
        """Delete host from model & settings (row_index from the view)."""
        # Guard: ignore placeholder row
        if row_index == 0:
            return

        item = self.host_model.item(row_index)
        if not item:
            return
        host = item.text().strip()
        if not host:
            return

        # remove from settings
        hosts = self.get_saved_hosts()
        if host in hosts:
            hosts.remove(host)
            self.save_hosts(hosts)

        # if currently selected, clear field and move selection to placeholder
        if self.host_input.currentText().strip() == host:
            self.host_input.setCurrentIndex(0)
            self.host_input.setCurrentText("")

        # remove from model
        self.host_model.removeRow(row_index)

    # ---------------- Connection logic ----------------
    def handle_submit(self):
        host = self.host_input.currentText().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        windows_auth = self.windows_auth_radio.isChecked()

        # Remember credentials
        if self.remember_username_check.isChecked():
            self.app_settings.setValue("saved_username", username)
            self.app_settings.setValue("remember_username", True)
        else:
            self.app_settings.remove("saved_username")
            self.app_settings.setValue("remember_username", False)

        if self.remember_password_check.isChecked():
            encrypted_pw = encrypt_password(password)
            self.app_settings.setValue("saved_password_enc", encrypted_pw)
            self.app_settings.setValue("remember_password", True)
        else:
            self.app_settings.remove("saved_password_enc")
            self.app_settings.setValue("remember_password", False)

        self.label.setText("Connecting...")
        self.button.setEnabled(False)
        self.host_input.setDisabled(True)

        print(f"[DEBUG] Connecting to {host} (windows_auth={windows_auth})")

        self.app_settings.setValue(LAST_USED_HOST_KEY, host)

        self.thread = QThread()
        self.worker = SQLConnectWorker(host, username, password, windows_auth)
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


    # ---------------- Callbacks ----------------
    def on_connection_success(self, connection):
        self.db_connection = connection
        self.label.setText("Connected successfully!")
        self.button.setEnabled(True)
        self.host_input.setDisabled(False)
        self.open_database_explorer()

    def on_connection_error(self, error_msg):
        self.last_error_message = error_msg
        self.label.setText("Connection failed!")
        self.button.setEnabled(True)
        self.host_input.setDisabled(False)
        QMessageBox.critical(self, "Connection Error", f"Failed to connect:\n{error_msg}")

    # ---------------- Explorer launch ----------------
    def open_database_explorer(self, db_name=None):
        print(f"[DEBUG] Connected: {self.db_connection}")
        try:
            if not hasattr(self, "open_explorers"):
                self.open_explorers = []

            if self.open_explorers:
                explorer = self.open_explorers[0]
                explorer.controller.conn = self.db_connection
                explorer.selected_database = db_name
                explorer.connection_window = self
                explorer.tree_panel.clear()
                explorer.refresh_databases()
                explorer.show()
                explorer.raise_()
                explorer.activateWindow()
            else:
                explorer = DatabaseExplorerWindow(
                    connection=self.db_connection, database=db_name, connection_window=self
                )
                self.open_explorers.append(explorer)
                explorer.show()

            save_window_settings(self)
            self.hide()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Database Explorer:\n{e}")
            print(f"⚠️ Error opening explorer: {e}")

    def eventFilter(self, obj, event):
        # Intercept clicks inside the popup list
        if obj is self.host_input.view().viewport() and event.type() == QEvent.MouseButtonRelease:
            view = self.host_input.view()
            index = view.indexAt(event.pos())

            # Only handle valid, non-placeholder rows
            if index.isValid() and index.row() > 0:
                item_rect = view.visualRect(index)
                # Recreate the delete button rect as drawn by the delegate
                x = item_rect.right() - (self.host_delegate._BTN_W + 4)
                y = item_rect.y() + (item_rect.height() - self.host_delegate._BTN_H) // 2
                btn_rect = QRect(x, y, self.host_delegate._BTN_W, self.host_delegate._BTN_H)

                if btn_rect.contains(event.pos()):
                    self.delete_host_by_index(index.row())

                    # Optional: keep popup open to show the result
                    QTimer.singleShot(0, self.host_input.showPopup)

                    # Stop further handling (don’t select / close popup)
                    return True

        # Default behaviour
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        save_window_settings(self)
        super().closeEvent(event)
