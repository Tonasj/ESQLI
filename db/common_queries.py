COMMON_SQL_QUERIES = [
    # --- [TITLE] separates the items following it to be parsed as queries under the given title ---
    ("[TITLE] Database Management", ""),
    ("Create Database", "CREATE DATABASE [DatabaseName];"),
    ("Drop Database", "DROP DATABASE [DatabaseName];"),
    ("Rename Database", "ALTER DATABASE [OldDatabaseName] MODIFY NAME = [NewDatabaseName];"),
    ("List Databases", "SELECT name FROM sys.databases;"),
    ("Use Database", "USE [DatabaseName];"),
    ("Backup Database", "BACKUP DATABASE [DatabaseName] TO DISK = 'C:\\Backups\\DatabaseName.bak';"),
    ("Restore Database", "RESTORE DATABASE [DatabaseName] FROM DISK = 'C:\\Backups\\DatabaseName.bak' WITH REPLACE;"),

    ("[TITLE] Table Management", ""),
    ("Create Table", 
     "CREATE TABLE [TableName] (\n"
     "    ID INT IDENTITY(1,1) PRIMARY KEY,\n"
     "    Column1 VARCHAR(255),\n"
     "    Column2 INT,\n"
     "    CreatedAt DATETIME DEFAULT GETDATE()\n"
     ");"),

    ("Rename Table", "EXEC sp_rename 'OldTableName', 'NewTableName';"),
    ("Drop Table", "DROP TABLE [TableName];"),
    ("Truncate Table", "TRUNCATE TABLE [TableName];"),
    ("Copy Table Structure", "SELECT TOP 0 * INTO [NewTable] FROM [ExistingTable];"),
    ("Copy Table with Data", "SELECT * INTO [NewTable] FROM [ExistingTable];"),

    ("[TITLE] Alter Table", ""),
    ("Add Column", "ALTER TABLE [TableName] ADD [NewColumn] NVARCHAR(255);"),
    ("Drop Column", "ALTER TABLE [TableName] DROP COLUMN [ColumnName];"),
    ("Rename Column", "EXEC sp_rename '[TableName].[OldColumnName]', 'NewColumnName', 'COLUMN';"),
    ("Change Column Type", "ALTER TABLE [TableName] ALTER COLUMN [ColumnName] INT;"),
    ("Add Primary Key", "ALTER TABLE [TableName] ADD CONSTRAINT PK_[TableName] PRIMARY KEY ([ColumnName]);"),
    ("Add Foreign Key", 
     "ALTER TABLE [ChildTable] ADD CONSTRAINT FK_[ChildTable]_[ParentTable]\n"
     "FOREIGN KEY ([ParentID]) REFERENCES [ParentTable]([ID]);"),

    ("[TITLE] Data Manipulation", ""),
    ("Insert Data", 
     "INSERT INTO [TableName] (Column1, Column2) VALUES ('Value1', 'Value2');"),
    ("Select Data", 
     "SELECT * FROM [TableName];"),
    ("Select with Condition", 
     "SELECT Column1, Column2 FROM [TableName] WHERE Column1 = 'Value';"),
    ("Update Data", 
     "UPDATE [TableName] SET Column1 = 'NewValue' WHERE ID = 1;"),
    ("Delete Data", 
     "DELETE FROM [TableName] WHERE ID = 1;"),
    ("Count Rows", 
     "SELECT COUNT(*) FROM [TableName];"),
    ("Order By", 
     "SELECT * FROM [TableName] ORDER BY Column1 DESC;"),
    ("Group By", 
     "SELECT Column1, COUNT(*) AS Total FROM [TableName] GROUP BY Column1;"),

    ("[TITLE] Joins & Relationships", ""),
    ("Inner Join", 
     "SELECT a.*, b.* FROM [TableA] a\n"
     "INNER JOIN [TableB] b ON a.ID = b.A_ID;"),
    ("Left Join", 
     "SELECT a.*, b.* FROM [TableA] a\n"
     "LEFT JOIN [TableB] b ON a.ID = b.A_ID;"),
    ("Right Join", 
     "SELECT a.*, b.* FROM [TableA] a\n"
     "RIGHT JOIN [TableB] b ON a.ID = b.A_ID;"),
    ("Full Join", 
     "SELECT a.*, b.* FROM [TableA] a\n"
     "FULL OUTER JOIN [TableB] b ON a.ID = b.A_ID;"),

    ("[TITLE] Indexes", ""),
    ("Create Index", 
     "CREATE INDEX IX_[TableName]_[ColumnName] ON [TableName]([ColumnName]);"),
    ("Drop Index", 
     "DROP INDEX IX_[TableName]_[ColumnName] ON [TableName];"),
    ("List Indexes", 
     "EXEC sp_helpindex '[TableName]';"),

    ("[TITLE] Views", ""),
    ("Create View", 
     "CREATE VIEW [ViewName] AS\n"
     "SELECT Column1, Column2 FROM [TableName] WHERE Condition;"),
    ("Drop View", 
     "DROP VIEW [ViewName];"),

    ("[TITLE] Stored Procedures", ""),
    ("Create Stored Procedure",
     "CREATE PROCEDURE [ProcedureName]\n"
     "AS\n"
     "BEGIN\n"
     "    SELECT * FROM [TableName];\n"
     "END;"),
    ("Execute Stored Procedure", "EXEC [ProcedureName];"),
    ("Drop Stored Procedure", "DROP PROCEDURE [ProcedureName];"),

    ("[TITLE] Utilities", ""),
    ("Show Table Schema", "EXEC sp_columns [TableName];"),
    ("Show All Tables", "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES;"),
    ("Show All Columns", 
     "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS\n"
     "WHERE TABLE_NAME = 'TableName';"),
]
