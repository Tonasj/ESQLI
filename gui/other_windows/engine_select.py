from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton
from PyQt5.QtCore import Qt
from core import get_available_engines

class EngineSelectDialog(QDialog):
    """Dialog for selecting which SQL engine to use."""

    def __init__(self, app_settings, parent=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self.setWindowTitle("Select SQL Engine")
        self.setMinimumWidth(320)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        label = QLabel("Select your SQL Engine:")
        label.setAlignment(Qt.AlignLeft)
        layout.addWidget(label)

        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumHeight(30)
        self.engine_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                padding: 4px;
                font-size: 10pt;
            }
        """)

        # Load available engines
        self.engines = get_available_engines()
        print(f"[DEBUG] Available engines: {self.engines}")

        if not self.engines:
            self.engine_combo.addItem("⚠️ No engines found", "")
            self.engine_combo.setEnabled(False)
        else:
            for key, name in self.engines.items():
                self.engine_combo.addItem(name, key)

            # Restore previously selected engine
            saved_engine = self.app_settings.value("engine", "msexpress")
            index = self.engine_combo.findData(saved_engine)
            if index >= 0:
                self.engine_combo.setCurrentIndex(index)

        layout.addWidget(self.engine_combo)

        self.ok_button = QPushButton("OK")
        self.ok_button.setMinimumHeight(28)
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button, alignment=Qt.AlignRight)

    def get_selected_engine(self):
        """Return the internal engine name chosen by the user."""
        return self.engine_combo.currentData()
