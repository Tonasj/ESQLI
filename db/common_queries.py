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
     "CREATE TABLE [dbo].[TableName] (\n"
     "    ID INT IDENTITY(1,1) PRIMARY KEY,\n"
     "    Column1 VARCHAR(255),\n"
     "    Column2 INT,\n"
     "    CreatedAt DATETIME DEFAULT GETDATE()\n"
     ");"),

    ("Rename Table", "EXEC sp_rename '[dbo].[OldTableName]', 'NewTableName';"),
    ("Drop Table", "DROP TABLE [dbo].[TableName];"),
    ("Truncate Table", "TRUNCATE TABLE [dbo].[TableName];"),
    ("Copy Table Structure", "SELECT TOP 0 * INTO [dbo].[NewTable] FROM [dbo].[ExistingTable];"),
    ("Copy Table with Data", "SELECT * INTO [dbo].[NewTable] FROM [dbo].[ExistingTable];"),

    ("[TITLE] Alter Table", ""),
    ("Add Column", "ALTER TABLE [dbo].[TableName] ADD [NewColumn] NVARCHAR(255);"),
    ("Drop Column", "ALTER TABLE [dbo].[TableName] DROP COLUMN [ColumnName];"),
    ("Rename Column", "EXEC sp_rename '[dbo].[TableName].[OldColumnName]', 'NewColumnName', 'COLUMN';"),
    ("Change Column Type", "ALTER TABLE [dbo].[TableName] ALTER COLUMN [ColumnName] INT;"),
    ("Add Primary Key", "ALTER TABLE [dbo].[TableName] ADD CONSTRAINT PK_[TableName] PRIMARY KEY ([ColumnName]);"),
    ("Add Foreign Key", 
     "ALTER TABLE [dbo].[ChildTable] ADD CONSTRAINT FK_[ChildTable]_[ParentTable]\n"
     "FOREIGN KEY ([ParentID]) REFERENCES [dbo].[ParentTable]([ID]);"),

    ("[TITLE] Data Manipulation", ""),
    ("Insert Data", 
     "INSERT INTO [dbo].[TableName] (Column1, Column2) VALUES ('Value1', 'Value2');"),
    ("Select Data", 
     "SELECT * FROM [dbo].[TableName];"),
    ("Select with Condition", 
     "SELECT Column1, Column2 FROM [dbo].[TableName] WHERE Column1 = 'Value';"),
    ("Update Data", 
     "UPDATE [dbo].[TableName] SET Column1 = 'NewValue' WHERE ID = 1;"),
    ("Delete Data", 
     "DELETE FROM [dbo].[TableName] WHERE ID = 1;"),
    ("Count Rows", 
     "SELECT COUNT(*) FROM [dbo].[TableName];"),
    ("Order By", 
     "SELECT * FROM [dbo].[TableName] ORDER BY Column1 DESC;"),
    ("Group By", 
     "SELECT Column1, COUNT(*) AS Total FROM [dbo].[TableName] GROUP BY Column1;"),

    ("[TITLE] Joins & Relationships", ""),
    ("Inner Join", 
     "SELECT a.*, b.* FROM [dbo].[TableA] a\n"
     "INNER JOIN [dbo].[TableB] b ON a.ID = b.A_ID;"),
    ("Left Join", 
     "SELECT a.*, b.* FROM [dbo].[TableA] a\n"
     "LEFT JOIN [dbo].[TableB] b ON a.ID = b.A_ID;"),
    ("Right Join", 
     "SELECT a.*, b.* FROM [dbo].[TableA] a\n"
     "RIGHT JOIN [dbo].[TableB] b ON a.ID = b.A_ID;"),
    ("Full Join", 
     "SELECT a.*, b.* FROM [dbo].[TableA] a\n"
     "FULL OUTER JOIN [dbo].[TableB] b ON a.ID = b.A_ID;"),

    ("[TITLE] Indexes", ""),
    ("Create Index", 
     "CREATE INDEX IX_[TableName]_[ColumnName] ON [dbo].[TableName]([ColumnName]);"),
    ("Drop Index", 
     "DROP INDEX IX_[TableName]_[ColumnName] ON [dbo].[TableName];"),
    ("List Indexes", 
     "EXEC sp_helpindex '[dbo].[TableName]';"),

    ("[TITLE] Views", ""),
    ("Create View", 
     "CREATE VIEW [dbo].[ViewName] AS\n"
     "SELECT Column1, Column2 FROM [dbo].[TableName] WHERE Condition;"),
    ("Drop View", 
     "DROP VIEW [dbo].[ViewName];"),

    ("[TITLE] Stored Procedures", ""),
    ("Create Stored Procedure",
     "CREATE PROCEDURE [dbo].[ProcedureName]\n"
     "AS\n"
     "BEGIN\n"
     "    SELECT * FROM [dbo].[TableName];\n"
     "END;"),
    ("Execute Stored Procedure", "EXEC [dbo].[ProcedureName];"),
    ("Drop Stored Procedure", "DROP PROCEDURE [dbo].[ProcedureName];"),

    ("[TITLE] Utilities", ""),
    ("Show Table Schema", "EXEC sp_columns '[dbo].[TableName]';"),
    ("Show All Tables", "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo';"),
    ("Show All Columns", 
     "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS\n"
     "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'TableName';"),
]
