from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout,
    QWidget, QScrollArea, QApplication, QLineEdit, QFrame, QLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect
from PyQt5.QtGui import QFont
from db.common_queries import COMMON_SQL_QUERIES


# --- FlowLayout implementation (auto-wraps buttons) ---
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=6):
        super().__init__(parent)
        self.itemList = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def doLayout(self, rect, testOnly):
        x, y = rect.x(), rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing()
            spaceY = self.spacing()
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


# --- CommonQueriesDialog ---
class CommonQueriesDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Common SQL Queries")
        self.setGeometry(200, 150, 720, 420)
        self.setMinimumSize(QSize(700, 500))
        self.setWindowFlags(self.windowFlags() | Qt.Window)

        self.all_items = []
        self.groups = {}

        main_layout = QVBoxLayout(self)

        # --- Search Bar ---
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search queries...")
        self.search_box.setFont(QFont("Segoe UI", 10))
        self.search_box.setMinimumHeight(28)
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 6px 10px;
                border: 1px solid #bbb;
                border-radius: 8px;
                background-color: #fcfcfc;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
                background-color: #ffffff;
            }
        """)
        self.search_box.textChanged.connect(self.filter_queries)
        main_layout.addWidget(self.search_box)

        # --- Group Navigation Buttons (FlowLayout) ---
        self.group_nav = QWidget()
        self.group_nav_layout = FlowLayout(self.group_nav, spacing=8)
        main_layout.addWidget(self.group_nav)

        # --- Scroll Area for Queries ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(8)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # --- Group queries & build UI ---
        self.group_queries()
        self.populate_groups()

    def group_queries(self):
        """Convert COMMON_SQL_QUERIES into grouped dict based on [TITLE] markers."""
        self.groups = {}
        current_group = "Miscellaneous"

        for name, query in COMMON_SQL_QUERIES:
            if name.startswith("[TITLE]"):
                current_group = name.replace("[TITLE]", "").strip()
                self.groups[current_group] = []
            else:
                self.groups.setdefault(current_group, []).append((name, query))

    def populate_groups(self):
        """Create group sections with headers and query items."""
        for group_name, queries in self.groups.items():
            # --- Group Header ---
            header = QLabel(f"📁 <b>{group_name}</b>")
            header.setStyleSheet("QLabel { font-size: 13pt; margin-top: 10px; color: #2c3e50; }")
            self.scroll_layout.addWidget(header)

            # Add navigation button (auto-size)
            btn = QPushButton(group_name)
            btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #bbb;
                    border-radius: 6px;
                    padding: 6px 12px;
                }
                QPushButton:hover {
                    background-color: #e2e2e2;
                }
            """)
            btn.clicked.connect(lambda _, name=group_name: self.scroll_to_group(name))
            self.group_nav_layout.addWidget(btn)

            # --- Add query items ---
            for name, query in queries:
                item_widget = self.create_query_item(name, query)
                self.scroll_layout.addWidget(item_widget)
                self.all_items.append((name.lower(), group_name, item_widget))

            # Divider
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color: #ddd;")
            self.scroll_layout.addWidget(line)

        self.scroll_layout.addStretch()

    def create_query_item(self, name, query):
        """Creates a block with query label, text box, and copy button."""
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(4)

        # Query name
        label = QLabel(f"<b>{name}</b>")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        vbox.addWidget(label)

        # Query text box
        text_box = QTextEdit()
        text_box.setPlainText(query)
        text_box.setReadOnly(True)
        text_box.setFont(QFont("Consolas", 10))
        doc_height = text_box.document().lineCount() * 20
        text_box.setFixedHeight(max(70, int(doc_height)))
        vbox.addWidget(text_box)

        # Bottom bar with copy button
        btn_layout = QHBoxLayout()
        copy_btn = QPushButton("⿻ Copy")
        copy_btn.setFixedWidth(100)
        copy_btn.clicked.connect(lambda _, q=query: self.copy_to_clipboard(q))
        btn_layout.addWidget(copy_btn, alignment=Qt.AlignLeft)
        btn_layout.addStretch()
        vbox.addLayout(btn_layout)

        # Styling
        text_box.setStyleSheet("""
            QWidget {
                border: 1px solid #ccc;
                background-color: #f9f9f9;
            }
        """)
        return container

    def copy_to_clipboard(self, text):
        QApplication.clipboard().setText(text)

    def filter_queries(self, text):
        """Filter query widgets based on search input."""
        text = text.lower().strip()
        for name, group, widget in self.all_items:
            widget.setVisible(text in name if text else True)

    def scroll_to_group(self, group_name):
        """Scroll to the group header."""
        for i in range(self.scroll_layout.count()):
            item = self.scroll_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QLabel) and group_name in widget.text():
                self.scroll_area.verticalScrollBar().setValue(widget.y())
                break
