import os
import sys

def resource_path(relative_path: str) -> str:
    """
    Get absolute path to a resource, working for both development and PyInstaller builds.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        # Normal development
        base_path = os.path.abspath(os.path.dirname(__file__))
        # move up as needed
        base_path = os.path.join(base_path, "..")

    return os.path.join(base_path, relative_path)
