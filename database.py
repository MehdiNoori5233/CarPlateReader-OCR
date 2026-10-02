# database.py
import pyodbc
from datetime import datetime
from config import SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD, SQL_DRIVER


class PlateDatabase:
    def __init__(self):
        self.conn_str = (
            f"DRIVER={{{SQL_DRIVER}}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
            "TrustServerCertificate=yes;"
        )
        self.conn = None
        self.connect()

    def connect(self):
        try:
            self.conn = pyodbc.connect(self.conn_str, autocommit=True)
            print("[DB] Connected to SQL Server successfully.")
        except Exception as e:
            print(f"[DB] Connection failed: {e}")
            self.conn = None

    def _ensure_connection(self):
        if self.conn is None:
            self.connect()
        else:
            try:
                self.conn.cursor().execute("SELECT 1")
            except Exception:
                self.connect()

    def insert_plate(self, plate_number: str, confidence: float = None,
                     image_path: str = None, camera_name: str = "PhoneCamera"):
        self._ensure_connection()
        if self.conn is None:
            print("[DB] No connection. Skipping insert.")
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO PlateLogs (PlateNumber, Confidence, DetectedAt, ImagePath, CameraName)
                VALUES (?, ?, ?, ?, ?)
                """,
                plate_number, confidence, datetime.now(), image_path, camera_name
            )
            print(f"[DB] Inserted: {plate_number}")
            return True
        except Exception as e:
            print(f"[DB] Insert error: {e}")
            return False

    def plate_exists_recently(self, plate_number: str, seconds: int = 10) -> bool:
        """جلوگیری از ثبت تکراری پلاک در بازه زمانی کوتاه"""
        self._ensure_connection()
        if self.conn is None:
            return False
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM PlateLogs
                WHERE PlateNumber = ?
                  AND DetectedAt >= DATEADD(SECOND, -?, GETDATE())
                """,
                plate_number, seconds
            )
            return cursor.fetchone()[0] > 0
        except Exception as e:
            print(f"[DB] Query error: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()
            print("[DB] Connection closed.")