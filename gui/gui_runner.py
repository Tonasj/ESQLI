from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
import sys
import os

from .main_window import ESQLIMainWindow

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "logo.ico")

def run_app():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))
    window = ESQLIMainWindow(icon_path=ICON_PATH)
    window.show()
    sys.exit(app.exec_())
