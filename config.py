# config.py

# آدرس استریم دوربین گوشی (با اپ IP Webcam)
# در اپ IP Webcam روی Start Server بزنید و IP را وارد کنید
# PHONE_CAMERA_URL = "http://192.168.1.100:8080/video"
PHONE_CAMERA_URL = "http://10.12.91.170:8080/video"

# تنظیمات SQL Server
SQL_SERVER   = ".\mssqlserver2"
SQL_DATABASE = "PlateReaderDB"
SQL_USERNAME = "sa"
SQL_PASSWORD = "123456"
SQL_DRIVER   = "ODBC Driver 17 for SQL Server"

# تنظیمات OCR
OCR_LANGUAGES = ['fa', 'en']   # فارسی + انگلیسی (اگر فقط انگلیسی: ['en'])
USE_GPU       = False          # اگر GPU دارید True کنید

# تنظیمات تشخیص پلاک
MIN_PLATE_AREA   = 1500
MAX_PLATE_AREA   = 60000
CONFIDENCE_MIN   = 0.4

# پوشه ذخیره تصاویر پلاک‌های ثبت شده
SAVE_DIR = "captured_plates"