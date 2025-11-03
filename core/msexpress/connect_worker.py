from PyQt5.QtCore import QObject, pyqtSignal, QThread
from .connect_sql import connect_to_sql

class SQLConnectWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, host, database, username, password, use_windows_auth=False):
        super().__init__()
        self.host = host
        self.database = database
        self.username = username
        self.password = password
        self.use_windows_auth = use_windows_auth

    def run(self):
        try:
            print("[DEBUG] SQLConnectWorker.run started")
            connection = connect_to_sql(
                host=self.host,
                database=self.database,
                username=self.username,
                password=self.password,
                use_windows_auth=self.use_windows_auth
            )
            if connection is None:
                raise RuntimeError("connect_to_sql returned None")
            self.finished.emit(connection)
        except Exception as e:
            print(f"[DEBUG] Connection failed with exception: {e}")
            self.error.emit(str(e))
