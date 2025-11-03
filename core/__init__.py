import importlib
import os

DEFAULT_ENGINE = "msexpress"

connect_to_sql = None
SQLConnectWorker = None



def get_available_engines():
    """Scan the core folder for submodules that define ENGINE_NAME."""
    engines = {}
    base_path = os.path.dirname(__file__)

    for folder in os.listdir(base_path):
        subpath = os.path.join(base_path, folder)
        if os.path.isdir(subpath) and os.path.exists(os.path.join(subpath, "__init__.py")):
            try:
                mod = importlib.import_module(f"core.{folder}")
                display_name = getattr(mod, "ENGINE_NAME", folder)
                engines[folder] = display_name
            except Exception:
                continue
    return engines


def load_sql_engine(engine_name: str = DEFAULT_ENGINE):
    """
    Dynamically load the SQL engine module (msexpress, mysql, etc.)
    """
    global connect_to_sql, SQLConnectWorker

    try:
        module = importlib.import_module(f"core.{engine_name}")
        connect_to_sql = getattr(module, "connect_to_sql")
        SQLConnectWorker = getattr(module, "SQLConnectWorker")
        print(f"[core] Loaded SQL engine: {engine_name}")
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not load SQL engine '{engine_name}': {e}")

load_sql_engine()