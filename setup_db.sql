IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'PlateReaderDB')
BEGIN
    CREATE DATABASE PlateReaderDB;
END
GO

USE PlateReaderDB;
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'PlateLogs')
BEGIN
    CREATE TABLE PlateLogs (
        Id           INT IDENTITY(1,1) PRIMARY KEY,
        PlateNumber  NVARCHAR(50)   NOT NULL,
        Confidence   FLOAT          NULL,
        DetectedAt   DATETIME       DEFAULT GETDATE(),
        ImagePath    NVARCHAR(500)  NULL,
        CameraName   NVARCHAR(100)  NULL
    );

    CREATE INDEX IX_PlateLogs_PlateNumber ON PlateLogs(PlateNumber);
    CREATE INDEX IX_PlateLogs_DetectedAt  ON PlateLogs(DetectedAt);
END
GO