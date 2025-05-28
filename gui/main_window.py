from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
import sys

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ESQLI - SQL Interface")
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        label = QLabel("Welcome to ESQLI")
        layout.addWidget(label)

        self.setLayout(layout)

def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
