import pandas as pd
from PyQt5.QtWidgets import (
    QMessageBox, QInputDialog, QFileDialog, QProgressDialog
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from db.db_utils import get_table_row_count


# ---------------------- Worker ----------------------
class ExportWorker(QThread):
    progress = pyqtSignal(int)     # progress percentage
    status = pyqtSignal(str)       # status text updates ("Finalizing...", etc.)
    finished = pyqtSignal(str)     # success message
    failed = pyqtSignal(str)       # error message

    def __init__(self, data, headers, file_path, format_choice):
        super().__init__()
        self.data = data
        self.headers = headers
        self.file_path = file_path
        self.format_choice = format_choice

    def run(self):
        try:
            # Normalize to DataFrame
            if isinstance(self.data, pd.DataFrame):
                df = self.data
            elif self.data and isinstance(self.data[0], dict):
                df = pd.DataFrame(self.data)
            else:
                df = pd.DataFrame(self.data, columns=self.headers)

            total_rows = len(df)
            if total_rows == 0:
                raise ValueError("No data to export.")

            # --- Export by format ---
            if self.format_choice == "CSV":
                df.to_csv(self.file_path, index=False)

            elif self.format_choice == "JSON":
                df.to_json(self.file_path, orient="records", indent=2)

            elif self.format_choice == "Excel":
                writer = pd.ExcelWriter(self.file_path, engine="openpyxl")
                rows_per_sheet = 10_000
                total_sheets = (total_rows + rows_per_sheet - 1) // rows_per_sheet

                for idx, start in enumerate(range(0, total_rows, rows_per_sheet)):
                    end = min(start + rows_per_sheet, total_rows)
                    chunk = df.iloc[start:end]
                    sheet_name = f"Sheet{idx + 1}"
                    chunk.to_excel(writer, index=False, sheet_name=sheet_name)

                    # Cap progress at 95%
                    percent = int((end / total_rows) * 95)
                    self.progress.emit(min(percent, 95))

                # Notify UI we’re finalizing
                self.status.emit("Finalizing Excel file…")
                writer.close()
                self.progress.emit(100)

            # Final success
            self.finished.emit(f"✅ Exported successfully to:\n{self.file_path}")

        except Exception as e:
            self.failed.emit(str(e))


# ---------------------- Connection Resolver ----------------------
def _resolve_conn(self):
    conn = getattr(self, "conn", None)
    if conn is not None:
        return conn
    controller = getattr(self, "controller", None)
    if controller is not None:
        conn = getattr(controller, "conn", None)
    if conn is None:
        raise RuntimeError("No database connection available on this window/controller.")
    return conn


# ---------------------- Paginated Export ----------------------
def export_paginated_data(self, fetch_func, identifier, fetch_args=None, is_query=False):
    """Generic paginated data exporter used by both table and query exports."""
    try:
        chunk_size, ok = QInputDialog.getInt(
            self,
            "Export Chunk Size",
            "Enter number of rows to fetch per batch:",
            10000, 1000, 1000000, 1000,
        )
        if not ok:
            return

        conn = _resolve_conn(self)
        all_data, headers, total_rows, page = [], None, None, 0

        if not is_query:
            total_rows = get_table_row_count(conn, identifier)
            if total_rows == 0:
                QMessageBox.warning(self, "No Data", f"No data found in table '{identifier}'.")
                return
            iterator = fetch_func(conn, identifier, chunk_size)
        else:
            iterator = None

        while True:
            if is_query:
                if not fetch_args or not str(fetch_args).strip():
                    raise ValueError("Empty or invalid SQL query provided for export.")
                cols, rows = fetch_func(conn, fetch_args, page, chunk_size)
                if not cols and not rows:
                    break
            else:
                try:
                    cols, rows = next(iterator)
                except StopIteration:
                    break

            if headers is None:
                headers = cols

            batch_data = [dict(zip(cols, row)) for row in rows]
            all_data.extend(batch_data)

            if is_query:
                if len(rows) < chunk_size:
                    break
                page += 1

        if not all_data:
            QMessageBox.warning(
                self, "No Data",
                f"No rows found for {'query' if is_query else f'table {identifier}'}."
            )
            return

        export_data_to_file(
            self,
            all_data,
            headers,
            identifier if not is_query else "query_results",
        )

    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to export data:\n{e}")
        print(f"⚠️ Error exporting data from {identifier}: {e}")


# ---------------------- Data Export (threaded) ----------------------
def export_data_to_file(self, data, headers, table_name):
    """Export given data (list of dicts or DataFrame) to CSV, JSON, or Excel — threaded."""
    try:
        if not data:
            QMessageBox.warning(self, "No Data", "There is no data to export.")
            return

        format_options = ["CSV", "JSON", "Excel"]
        format_choice, ok = QInputDialog.getItem(
            self, "Export Format", "Select the format to export:",
            format_options, 0, False,
        )
        if not ok or not format_choice:
            return

        default_name = f"{table_name}.{format_choice.lower() if format_choice != 'Excel' else 'xlsx'}"
        file_filter = (
            "CSV Files (*.csv)" if format_choice == "CSV"
            else "JSON Files (*.json)" if format_choice == "JSON"
            else "Excel Files (*.xlsx)"
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Export {table_name} as {format_choice}", default_name, file_filter,
        )
        if not file_path:
            return  # user cancelled

        # --- Launch threaded export ---
        progress_dialog = QProgressDialog("Exporting data, please wait...", "Cancel", 0, 100, self)
        progress_dialog.setWindowTitle(f"Exporting {table_name}")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setAutoClose(False)
        progress_dialog.setAutoReset(False)
        progress_dialog.show()

        worker = ExportWorker(data, headers, file_path, format_choice)
        self._export_thread = worker  # Keep reference

        worker.progress.connect(progress_dialog.setValue)
        worker.status.connect(progress_dialog.setLabelText)
        worker.finished.connect(lambda msg: (
            progress_dialog.close(),
            QMessageBox.information(self, "Export Successful", msg)
        ))
        worker.failed.connect(lambda err: (
            progress_dialog.close(),
            QMessageBox.critical(self, "Export Failed", f"❌ {err}")
        ))
        progress_dialog.canceled.connect(worker.terminate)

        worker.start()

    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to export data:\n{e}")
        print(f"⚠️ Error exporting data: {e}")
