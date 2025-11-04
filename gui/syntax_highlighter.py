from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor
from PyQt5.QtCore import QRegularExpression
import re

SQL_KEYWORDS = [
    # Core SQL
    "ADD", "ALL", "ALTER", "AND", "ANY", "AS", "ASC", "AUTHORIZATION",
    "BACKUP", "BEGIN", "BETWEEN", "BREAK", "BROWSE", "BULK", "BY",
    "CASCADE", "CASE", "CHECK", "CHECKPOINT", "CLOSE", "CLUSTERED",
    "COALESCE", "COLLATE", "COLUMN", "COMMIT", "COMPUTE", "CONSTRAINT",
    "CONTAINS", "CONTAINSTABLE", "CONTINUE", "CONVERT", "CREATE", "CROSS",
    "CURRENT", "CURRENT_DATE", "CURRENT_TIME", "CURRENT_TIMESTAMP",
    "CURRENT_USER", "CURSOR", "DATABASE", "DBCC", "DEALLOCATE", "DECLARE",
    "DEFAULT", "DELETE", "DENY", "DESC", "DISK", "DISTINCT", "DISTRIBUTED",
    "DOUBLE", "DROP", "DUMP", "ELSE", "END", "ERRLVL", "ESCAPE", "EXCEPT",
    "EXEC", "EXECUTE", "EXISTS", "EXIT", "EXTERNAL", "FETCH", "FILE",
    "FILLFACTOR", "FOR", "FOREIGN", "FREETEXT", "FREETEXTTABLE", "FROM",
    "FULL", "FUNCTION", "GOTO", "GRANT", "GROUP", "HAVING", "HOLDLOCK",
    "IDENTITY", "IDENTITY_INSERT", "IDENTITYCOL", "IF", "IN", "INDEX",
    "INNER", "INSERT", "INTERSECT", "INTO", "IS", "JOIN", "KEY", "KILL",
    "LEFT", "LIKE", "LINENO", "LOAD", "MERGE", "NATIONAL", "NOCHECK",
    "NONCLUSTERED", "NOT", "NULL", "NULLIF", "OF", "OFF", "OFFSETS",
    "ON", "OPEN", "OPENDATASOURCE", "OPENQUERY", "OPENROWSET", "OPENXML",
    "OPTION", "OR", "ORDER", "OUTER", "OVER", "PERCENT", "PIVOT", "PLAN",
    "PRECISION", "PRIMARY", "PRINT", "PROC", "PROCEDURE", "PUBLIC",
    "RAISERROR", "READ", "READTEXT", "RECONFIGURE", "REFERENCES",
    "REPLICATION", "RESTORE", "RESTRICT", "RETURN", "REVERT", "REVOKE",
    "RIGHT", "ROLLBACK", "ROWCOUNT", "ROWGUIDCOL", "RULE", "SAVE",
    "SCHEMA", "SECURITYAUDIT", "SELECT", "SEMANTICKEYPHRASETABLE",
    "SEMANTICSIMILARITYDETAILSTABLE", "SEMANTICSIMILARITYTABLE",
    "SESSION_USER", "SET", "SETUSER", "SHUTDOWN", "SOME", "STATISTICS",
    "SYSTEM_USER", "TABLE", "TABLESAMPLE", "TEXTSIZE", "THEN", "TO",
    "TOP", "TRAN", "TRANSACTION", "TRIGGER", "TRUNCATE", "TSEQUAL",
    "UNION", "UNIQUE", "UNPIVOT", "UPDATE", "UPDATETEXT", "USE", "USER",
    "VALUES", "VARYING", "VIEW", "WAITFOR", "WHEN", "WHERE", "WHILE",
    "WITH", "WITHIN GROUP", "WRITETEXT"
]


SQL_TYPES = [
    "INT", "INTEGER", "SMALLINT", "BIGINT", "TINYINT",
    "FLOAT", "REAL", "DOUBLE", "DECIMAL", "NUMERIC", "MONEY", "SMALLMONEY",
    "CHAR", "NCHAR", "VARCHAR", "NVARCHAR", "TEXT", "NTEXT",
    "DATE", "TIME", "DATETIME", "SMALLDATETIME", "DATETIME2", "DATETIMEOFFSET",
    "BIT", "BINARY", "VARBINARY", "IMAGE", "UNIQUEIDENTIFIER",
    "XML", "CURSOR", "TABLE"
]

SQL_FUNCTIONS = [
    "COUNT", "SUM", "AVG", "MIN", "MAX",
    "GETDATE", "SYSDATETIME", "NEWID", "ROW_NUMBER", "RANK", "DENSE_RANK",
    "NTILE", "ISNULL", "COALESCE", "NULLIF", "CAST", "CONVERT", "TRY_CONVERT",
    "UPPER", "LOWER", "LEN", "SUBSTRING", "REPLACE", "LTRIM", "RTRIM",
    "ROUND", "ABS", "POWER", "FLOOR", "CEILING",
    "NOW", "YEAR", "MONTH", "DAY", "DATEPART", "DATENAME",
    "SYSTEM_USER", "SESSION_USER", "USER_NAME", "HOST_NAME", "DB_NAME"
]

class SQLHighlighter(QSyntaxHighlighter):
    def __init__(self, document, editor=None):
        super().__init__(document)
        self.rules = []
        self.editor = editor  # optional reference to QTextEdit
        self._is_updating = False  # recursion guard

        # --- Keyword style ---
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0077cc"))
        keyword_format.setFontWeight(QFont.Bold)
        for word in SQL_KEYWORDS:
            pattern = QRegularExpression(rf"\b{word}\b", QRegularExpression.CaseInsensitiveOption)
            self.rules.append((pattern, keyword_format))

        # --- Type style ---
        type_format = QTextCharFormat()
        type_format.setForeground(QColor("#8e44ad"))
        for word in SQL_TYPES:
            pattern = QRegularExpression(rf"\b{word}\b", QRegularExpression.CaseInsensitiveOption)
            self.rules.append((pattern, type_format))

        # --- Function style ---
        func_format = QTextCharFormat()
        func_format.setForeground(QColor("#009688"))
        for word in SQL_FUNCTIONS:
            pattern = QRegularExpression(rf"\b{word}\b", QRegularExpression.CaseInsensitiveOption)
            self.rules.append((pattern, func_format))

        # --- String style ---
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#e74c3c"))  # red
        self.rules.append((QRegularExpression(r"'([^'\\]|\\.)*'"), string_format))
        self.rules.append((QRegularExpression(r'"([^"\\]|\\.)*"'), string_format))

        # --- Comment style ---
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#7f8c8d"))
        self.rules.append((QRegularExpression(r"--[^\n]*"), comment_format))
        self.rules.append(
            (QRegularExpression(r"/\*.*?\*/", QRegularExpression.DotMatchesEverythingOption), comment_format)
        )

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                start = match.capturedStart()
                length = match.capturedLength()
                if length > 0:
                    self.setFormat(start, length, fmt)

    # --- Keyword Auto Uppercase (safe) ---
    def apply_uppercase_keywords(self):
        """Uppercase SQL keywords safely without recursion or cursor jumps."""
        if self._is_updating or not self.editor:
            return

        self._is_updating = True
        cursor = self.editor.textCursor()
        block = cursor.block()
        if not block.isValid():
            self._is_updating = False
            return

        text = block.text()
        new_text = text

        # Regex replacement — fast and case-insensitive
        for word in SQL_KEYWORDS:
            new_text = re.sub(rf"\b{word}\b", word.upper(), new_text, flags=re.IGNORECASE)

        if new_text != text:
            pos_in_block = cursor.position() - block.position()
            cursor.beginEditBlock()
            cursor.setPosition(block.position())
            cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
            cursor.insertText(new_text)
            cursor.endEditBlock()

            # restore cursor
            cursor.setPosition(block.position() + min(len(new_text), pos_in_block))
            self.editor.setTextCursor(cursor)

        self._is_updating = False