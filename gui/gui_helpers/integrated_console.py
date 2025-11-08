import sys
import datetime
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import pyqtSignal, QObject, Qt


class ConsoleEmitter(QObject):
    """Thread-safe signal emitter for console messages."""
    message_written = pyqtSignal(str)

class EmittingStream:
    """Redirects stdout/stderr to a QTextEdit safely from any thread."""
    def __init__(self, emitter: ConsoleEmitter, debug_enabled=True):
        self.emitter = emitter
        self.debug_enabled = debug_enabled
        self._buffer = ""

    def write(self, message):
        message = message.strip()
        if not message:
            return

        if message.startswith("[DEBUG]") and not self.debug_enabled:
            return
        
        timestamp = datetime.datetime.now().strftime("%H:%M")
        self.emitter.message_written.emit(f"{timestamp} : {message.strip()}")

    def flush(self):
        pass

class IntegratedConsole(QTextEdit):
    """A QTextEdit widget that acts as an integrated console."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.emitter = ConsoleEmitter()
        self.emitter.message_written.connect(self.append_message)

    def append_message(self, message):
        self.append(message)

def redirect_std(console_widget: IntegratedConsole, debug_enabled=True):
    """Redirect print/standard output and errors to the given console widget safely."""
    stdout_stream = EmittingStream(console_widget.emitter, debug_enabled=debug_enabled)
    stderr_stream = EmittingStream(console_widget.emitter, debug_enabled=debug_enabled)
    sys.stdout = stdout_stream
    sys.stderr = stderr_stream

    console_widget.stdout_stream = stdout_stream
    console_widget.stderr_stream = stderr_stream

    return stdout_stream, stderr_stream