import os
from PyQt5.QtWidgets import (
    QFileDialog,
    QMessageBox,
)
def save_query_to_file(self, editor):
    """
    Opens a file explorer dialog to save the query text.
    """
    try:
        # Suggest a default file name
        default_name = "query.sql"
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog if os.name == "posix" else QFileDialog.Options()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save SQL Query",
            default_name,
            "SQL Files (*.sql);;Text Files (*.txt);;All Files (*)",
            options=options
        )

        if not file_path:
            return  # user cancelled

        query_text = editor.toPlainText().strip()
        if not query_text:
            QMessageBox.warning(self, "Empty Query", "Nothing to save — the query editor is empty.")
            return

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(query_text)

        QMessageBox.information(self, "Saved", f"Query saved successfully to:\n{file_path}")

    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to save query:\n{e}")
        print(f"⚠️ Error saving query: {e}")

def open_query_from_file(self, editor):
    """
    Opens a file dialog to load a SQL query into the current editor.
    """
    try:
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog if os.name == "posix" else QFileDialog.Options()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SQL Query",
            "",
            "SQL Files (*.sql);;Text Files (*.txt);;All Files (*)",
            options=options
        )

        if not file_path:
            return  # user cancelled

        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        if not file_content.strip():
            QMessageBox.warning(self, "Empty File", "The selected file is empty.")
            return

        # Confirm overwrite if editor already has text
        if editor.toPlainText().strip():
            reply = QMessageBox.question(
                self,
                "Overwrite Editor",
                "This will replace the current editor contents. Continue?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        editor.setPlainText(file_content)
        QMessageBox.information(self, "Loaded", f"Query loaded from:\n{file_path}")

    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to open query file:\n{e}")
        print(f"⚠️ Error opening query: {e}")