import sys
import datetime
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import pyqtSignal, QObject, Qt


class ConsoleEmitter(QObject):
    """Thread-safe signal emitter for console messages."""
    message_written = pyqtSignal(str)

class EmittingStream:
    """Redirects stdout/stderr to a QTextEdit safely from any thread."""
    def __init__(self, emitter: ConsoleEmitter):
        self.emitter = emitter

    def write(self, message):
        if message.strip():
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

def redirect_std(console_widget: IntegratedConsole):
    """Redirect print/standard output and errors to the given console widget safely."""
    sys.stdout = EmittingStream(console_widget.emitter)
    sys.stderr = EmittingStream(console_widget.emitter)