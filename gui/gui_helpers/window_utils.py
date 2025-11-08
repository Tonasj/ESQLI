import os
from PyQt5.QtCore import QByteArray, QSettings

def setup_app_settings():
    """
    Create (if missing) the config folder and return QSettings instances.
    Returns (gui_settings, app_settings)
    """
    base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_folder = os.path.join(base_folder, "config")
    os.makedirs(config_folder, exist_ok=True)

    gui_settings_path = os.path.join(config_folder, "gui_settings.ini")
    app_settings_path = os.path.join(config_folder, "app_settings.ini")

    gui_settings = QSettings(gui_settings_path, QSettings.IniFormat)
    app_settings = QSettings(app_settings_path, QSettings.IniFormat)
    return gui_settings, app_settings

# --- Window persistence ---
def save_window_settings(window):
    """
    Save the geometry and splitter states of a window into its gui_settings.
    Expected attributes: main_splitter, top_splitter, bottom_splitter
    """
    settings = getattr(window, "gui_settings", None)
    if not settings:
        return
    name = getattr(window, "window_name", window.__class__.__name__)
    settings.setValue(f"{name}/geometry", window.saveGeometry())

    for key in ["main_splitter", "top_splitter", "bottom_splitter"]:
        splitter = getattr(window, key, None)
        if splitter:
            settings.setValue(f"{name}/{key}", splitter.saveState())


def restore_window_settings(window):
    """
    Restore the geometry and splitter states from gui_settings.
    """
    settings = getattr(window, "gui_settings", None)
    if not settings:
        return
    
    name = getattr(window, "window_name", window.__class__.__name__)

    geometry = settings.value(f"{name}/geometry")
    if geometry:
        window.restoreGeometry(QByteArray(geometry))

    for key in ["main_splitter", "top_splitter", "bottom_splitter"]:
        splitter = getattr(window, key, None)
        state = settings.value(f"{name}/{key}")
        if splitter and state:
            splitter.restoreState(QByteArray(state))


def attach_window_persistence(window_class):
    """
    Class decorator to automatically connect save/restore window state.
    """

    orig_closeEvent = getattr(window_class, "closeEvent", None)

    def new_closeEvent(self, event):
        save_window_settings(self)
        if orig_closeEvent:
            orig_closeEvent(self, event)
        else:
            super(window_class, self).closeEvent(event)

    window_class.closeEvent = new_closeEvent
    return window_class