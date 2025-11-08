from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton

from core import get_available_engines

class EngineSelectDialog(QDialog):
    """Dialog for selecting which SQL engine to use."""

    def __init__(self, app_settings, parent=None):
        super().__init__(parent)
        self.app_settings = app_settings
        self.setWindowTitle("Select SQL Engine")
        self.setMinimumWidth(300)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select your SQL Engine:"))

        self.engine_combo = QComboBox()
        self.engines = get_available_engines()  # {'msexpress': 'Microsoft SQL Express', ...}
        for key, name in self.engines.items():
            self.engine_combo.addItem(name, key)

        saved_engine = self.app_settings.value("engine", "msexpress")
        index = self.engine_combo.findData(saved_engine)
        if index >= 0:
            self.engine_combo.setCurrentIndex(index)

        layout.addWidget(self.engine_combo)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        layout.addWidget(self.ok_button)

        self.setLayout(layout)

    def get_selected_engine(self):
        """Return the internal engine name chosen by the user."""
        key = self.engine_combo.currentData()
        return key
