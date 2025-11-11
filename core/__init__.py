import importlib
import os
import sys

DEFAULT_ENGINE = "msexpress"

connect_to_sql = None
SQLConnectWorker = None


def get_available_engines():
    """
    Debug version – prints what it sees.
    """
    engines = {}
    base_path = os.path.dirname(__file__)
    print(f"[DEBUG] Scanning base path: {base_path}")

    # --- Gather potential engines ---
    if getattr(sys, "frozen", False):
        print("[DEBUG] Running in PyInstaller (frozen) mode")
        potential_engines = ["msexpress"]
    else:
        print("[DEBUG] Running in development mode")
        entries = os.listdir(base_path)
        print(f"[DEBUG] Found entries: {entries}")
        potential_engines = [
            name for name in entries
            if os.path.isdir(os.path.join(base_path, name))
            and os.path.exists(os.path.join(base_path, name, "__init__.py"))
        ]
        print(f"[DEBUG] Potential engines: {potential_engines}")

    # --- Import and collect display names ---
    for folder in potential_engines:
        try:
            mod = importlib.import_module(f"core.{folder}")
            display_name = getattr(mod, "ENGINE_NAME", folder)
            engines[folder] = display_name
            print(f"[DEBUG] Loaded engine '{folder}' as '{display_name}'")
        except Exception as e:
            print(f"[WARN] Could not load engine '{folder}': {e}")

    print(f"[DEBUG] Final engines dict: {engines}")
    return engines



def load_sql_engine(engine_name: str = DEFAULT_ENGINE):
    """
    Dynamically load the SQL engine module (e.g. msexpress, mysql, etc.).
    """
    global connect_to_sql, SQLConnectWorker

    try:
        module = importlib.import_module(f"core.{engine_name}")
        connect_to_sql = getattr(module, "connect_to_sql")
        SQLConnectWorker = getattr(module, "SQLConnectWorker")
        print(f"[core] Loaded SQL engine: {engine_name}")
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not load SQL engine '{engine_name}': {e}")


# --- PyInstaller compatibility ---
if getattr(sys, "frozen", False):
    # Explicitly import submodules so PyInstaller includes them
    try:
        import core.msexpress
        import core.msexpress.connect_sql
        import core.msexpress.connect_worker
    except ImportError as e:
        print(f"[WARN] Could not import engine during freeze: {e}")

# Auto-load default
try:
    load_sql_engine()
except Exception as e:
    print(f"[ERROR] Failed to load default SQL engine '{DEFAULT_ENGINE}': {e}")
