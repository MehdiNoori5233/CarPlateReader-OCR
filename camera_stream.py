# camera_stream.py
import cv2
import time
from config import PHONE_CAMERA_URL


class PhoneCamera:
    def __init__(self, url: str = None, fallback_index: int = 0):
        self.base_url = url or PHONE_CAMERA_URL
        self.fallback_index = fallback_index
        self.cap = None

    def _try_open(self, source):
        print(f"[CAM] Trying: {source}")
        cap = cv2.VideoCapture(source)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"[CAM] ✅ Opened: {source}")
                return cap
        cap.release()
        return None

    def open(self):
        # ساخت لیست آدرس‌های ممکن
        url = self.base_url.rstrip('/')
        candidates = []

        # اگر آدرس کامل با /video داده شده، همان را تست کن
        if url.endswith('/video') or url.endswith('/videofeed'):
            candidates.append(url)
            # جایگزین
            candidates.append(url.replace('/video', '/videofeed'))
            candidates.append(url.replace('/videofeed', '/video'))
        else:
            # فقط IP داده شده، پس مسیرها را اضافه کن
            candidates.append(f"{url}/video")
            candidates.append(f"{url}/videofeed")
            candidates.append(f"{url}/mjpegfeed")

        # تلاش برای اتصال به دوربین گوشی
        for src in candidates:
            self.cap = self._try_open(src)
            if self.cap:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # کاهش تأخیر
                return self.cap

        # اگر هیچ‌کدام نشد، وب‌کم محلی
        print("[CAM] ⚠️ Phone camera failed. Using local webcam.")
        self.cap = self._try_open(self.fallback_index)
        if not self.cap:
            raise RuntimeError("Cannot open any camera!")
        return self.cap

    def read(self):
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap:
            self.cap.release()