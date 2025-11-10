import difflib
import pandas as pd
import re
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from gui.other_windows.import_dialog import ImportMappingDialog


def import_data_to_table(parent, controller, table_name):
    """
    High-level import routine for JSON, CSV, and XLSX.
    Handles reading, schema validation, and mapping dialog.
    """

    if not table_name:
        QMessageBox.warning(parent, "No Table Selected", "Please select a table first.")
        return

    # 1️⃣ Pick a file
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Select Data File to Import",
        "",
        "Data Files (*.csv *.json *.xlsx)"
    )
    if not file_path:
        return

    # 2️⃣ Read file via pandas
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.endswith(".json"):
            df = pd.read_json(file_path)
        elif file_path.endswith(".xlsx"):
            df = pd.read_excel(file_path)
        else:
            QMessageBox.warning(parent, "Invalid File", "Only CSV, JSON or XLSX files are supported.")
            return
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Failed to read file:\n{e}")
        return

    if df.empty:
        QMessageBox.warning(parent, "Empty File", "The selected file contains no data.")
        return

    file_headers = list(df.columns)
    table_schema = controller.fetch_table_schema(table_name)  # [("id","INT",pk), ("name","TEXT",...)]
    table_columns = []
    ignored_columns = []
    for col_info in table_schema:
        # expected tuple: (name, type, is_primary?, is_identity?)
        # but adapt if your fetch_table_schema() returns fewer fields
        name = col_info[0]
        is_pk = False
        is_identity = False

        # Try to detect PK or identity flags from schema info
        if len(col_info) >= 3:
            is_pk = bool(col_info[2])
        if len(col_info) >= 4:
            is_identity = bool(col_info[3])

        if is_pk or is_identity:
            ignored_columns.append(name)
            continue

        table_columns.append(name)

    if ignored_columns:
        print(f"[INFO] Ignoring columns for import: {', '.join(ignored_columns)}")

    # 3️⃣ Header mismatch check
    if len(file_headers) != len(table_columns):
        diff = len(file_headers) - len(table_columns)
        msg = (
            f"The file has {len(file_headers)} columns, "
            f"but the table '{table_name}' has {len(table_columns)}.\n\n"
        )
        if diff > 0:
            msg += (
                "The file contains **more** columns than the table.\n"
                "Would you like to choose which columns to import?"
            )
        else:
            msg += (
                "The file contains **fewer** columns than the table.\n"
                "Would you like to automatically add missing columns?"
            )
        choice = QMessageBox.question(
            parent,
            "Column Mismatch",
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if choice == QMessageBox.No:
            return
        # Mapping step still happens below

    # 4️⃣ Fuzzy matching
    mapping = {}
    norm_table_cols = { _normalize_name(c): c for c in table_columns }

    for fh in file_headers:
        norm_fh = _normalize_name(fh)

        # --- Exact normalized match ---
        if norm_fh in norm_table_cols:
            mapping[fh] = norm_table_cols[norm_fh]
            continue

        # --- Case-insensitive / close fuzzy match ---
        match = difflib.get_close_matches(norm_fh, norm_table_cols.keys(), n=1, cutoff=0.7)
        if match:
            mapping[fh] = norm_table_cols[match[0]]
        else:
            mapping[fh] = None

    # 5️⃣ Show mapping dialog
    dialog = ImportMappingDialog(
        parent=parent,
        file_headers=file_headers,
        table_columns=table_columns,
        initial_mapping=mapping,
    )
    if dialog.exec_() != dialog.Accepted:
        return

    final_mapping = dialog.get_mapping()

    # Drop ignored columns
    df = df[[col for col in final_mapping if final_mapping[col]]]
    df.columns = [final_mapping[col] for col in df.columns]

    # 6️⃣ Insert into table
    try:
        inserted = controller.bulk_insert(table_name, df)
        QMessageBox.information(
            parent,
            "Import Complete",
            f"✅ Successfully imported {inserted} rows into '{table_name}'."
        )
        return inserted

    except Exception as e:
        QMessageBox.critical(parent, "Import Error", f"Failed to import data:\n{e}")

def _normalize_name(name: str) -> str:
    """Normalize column names for case-insensitive fuzzy matching."""
    if not name:
        return ""
    # Lowercase, remove underscores/spaces/specials
    return re.sub(r'[^a-z0-9]', '', name.strip().lower())