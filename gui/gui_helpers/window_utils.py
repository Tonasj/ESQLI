import os
from PyQt5.QtCore import QByteArray, QSettings

def find_project_root():
    current = os.path.abspath(__file__)
    while True:
        parent = os.path.dirname(current)
        if os.path.basename(parent).lower() == "esqli" or parent == current:
            return parent
        current = parent

def setup_app_settings():
    """
    Create (if missing) the config folder and return QSettings instances.
    Ensures absolute file paths and always uses ESQLI/config.
    """
    # Find project root (folder that contains 'ESQLI')
    base_folder = find_project_root()
    config_folder = os.path.normpath(os.path.join(base_folder, "config"))
    os.makedirs(config_folder, exist_ok=True)

    gui_settings_path = os.path.normpath(os.path.join(config_folder, "gui_settings.ini"))
    app_settings_path = os.path.normpath(os.path.join(config_folder, "app_settings.ini"))

    # Debug print: check final resolved paths

    # Use fully qualified (absolute) paths to ensure Qt doesn't relativize them
    gui_settings = QSettings(os.path.abspath(gui_settings_path), QSettings.IniFormat)
    app_settings = QSettings(os.path.abspath(app_settings_path), QSettings.IniFormat)

    # --- Ensure 'localhost' exists in app_settings hosts list ---
    hosts = app_settings.value("hosts", [])
    # Normalize value to a list of strings
    if hosts is None:
        hosts = []
    elif isinstance(hosts, str):
        hosts = [hosts]
    elif not isinstance(hosts, (list, tuple)):
        hosts = []
    if isinstance(hosts, str):
        hosts = [hosts]

    # Clean and normalize
    hosts = [h.strip() for h in hosts if isinstance(h, str) and h.strip()]
    if not any(h.casefold() == "localhost" for h in hosts):
        hosts.insert(0, "localhost")  # make it appear first
        app_settings.setValue("hosts", hosts)
        app_settings.sync()
        print("[DEBUG] Added 'localhost' to hosts list in app_settings.")

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