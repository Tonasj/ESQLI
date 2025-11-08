from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSettings
import sys
import os

from .connection_window.connection_window import ConnectionWindow
from .database_explorer.main_window import DatabaseExplorerWindow
from .other_windows.engine_select import EngineSelectDialog
from core import load_sql_engine

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
ICON_PATH = os.path.join(ASSETS_DIR, "logo.ico")


def run_app():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(ICON_PATH))

    # ---- Prepare config ----
    base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_folder = os.path.join(base_folder, "config")
    os.makedirs(config_folder, exist_ok=True)
    app_settings_path = os.path.join(config_folder, "app_settings.ini")
    app_settings = QSettings(app_settings_path, QSettings.IniFormat)

    # ---- Show engine selection dialog ----
    saved_engine = app_settings.value("engine", None)
    if not saved_engine:
        dialog = EngineSelectDialog(app_settings)
        if dialog.exec_() != dialog.Accepted:
            print("Engine selection cancelled. Exiting.")
            sys.exit(0)
        selected_engine = dialog.get_selected_engine()
        app_settings.setValue("engine", selected_engine)
    else:
        selected_engine = saved_engine

    # ---- Load the chosen engine ----
    try:
        load_sql_engine(selected_engine)
    except Exception as e:
        print(f"Failed to load SQL engine '{selected_engine}': {e}")
        sys.exit(1)
        
    # ---- Launch database explorer first (empty) ----
    explorer = DatabaseExplorerWindow()
    explorer.show()

    # ---- Launch connection window ----
    window = ConnectionWindow(icon_path=ICON_PATH)
    window.open_explorers = [explorer]  # keep reference
    window.show()

    sys.exit(app.exec_())
