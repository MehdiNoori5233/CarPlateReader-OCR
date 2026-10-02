# main.py
# -*- coding: utf-8 -*-
import cv2
import os
import time
from datetime import datetime

from config import SAVE_DIR, CONFIDENCE_MIN
from camera_stream import PhoneCamera
from plate_detector import PlateDetector
from plate_ocr import PlateOCR
from database import PlateDatabase


def ensure_save_dir():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR, exist_ok=True)


def main():
    ensure_save_dir()

    print("=" * 55)
    print("   Plate Reader | OpenCV + EasyOCR + SQL Server")
    print("=" * 55)

    # ---------- راه‌اندازی اجزا ----------
    cam = PhoneCamera()
    cap = cam.open()

    detector = PlateDetector()
    ocr = PlateOCR()
    db = PlateDatabase()

    last_saved = {}          # جلوگیری از ثبت تکراری
    DUPLICATE_WINDOW = 8     # ثانیه
    frame_count = 0

    print("[INFO] Press 'q' to quit, 's' to save snapshot.")

    # ---------- حلقه اصلی ----------
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("[WARN] Frame grab failed. Retrying...")
            time.sleep(0.3)
            continue

        frame_count += 1
        display = frame.copy()

        # هر ۵ فریم یک بار پردازش سنگین انجام بشه (بهبود سرعت)
        if frame_count % 5 == 0:
            try:
                candidates, _ = detector.find_candidates(frame)
            except Exception as e:
                print(f"[DETECT] Error: {e}")
                candidates = []

            labels = []

            # ---------- پردازش هر کاندید پلاک ----------
            for box in candidates[:3]:
                try:
                    plate_img = detector.crop_plate(frame, box)
                    text, conf = ocr.read_plate(plate_img)
                except Exception as e:
                    print(f"[OCR] Error: {e}")
                    labels.append("")
                    continue

                # اگه پلاک معتبر نبود، رد شو
                if not text or "?" in text or conf < CONFIDENCE_MIN:
                    labels.append("")
                    continue

                labels.append(f"{text} ({conf:.2f})")
                now = time.time()

                # چک تکراری در حافظه
                if text in last_saved and (now - last_saved[text]) < DUPLICATE_WINDOW:
                    continue

                # چک تکراری در دیتابیس
                try:
                    if db.plate_exists_recently(text, seconds=DUPLICATE_WINDOW):
                        last_saved[text] = now
                        continue
                except Exception as e:
                    print(f"[DB] Duplicate check error: {e}")

                # ذخیره تصویر پلاک
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                safe_text = text.replace(" ", "_").replace("/", "-").replace("?", "X")
                img_path = os.path.join(SAVE_DIR, f"{safe_text}_{ts}.jpg")
                cv2.imwrite(img_path, plate_img)

                # ذخیره در دیتابیس
                try:
                    db.insert_plate(text, conf, img_path, camera_name="PhoneCamera")
                except Exception as e:
                    print(f"[DB] Insert error: {e}")

                last_saved[text] = now
                print(f"[OK] پلاک: {text} | اطمینان: {conf:.2f} | ذخیره: {img_path}")

            # ---------- رسم کادرها روی تصویر ----------
            display = detector.draw_boxes(display, candidates, labels)

        # ---------- نمایش تصویر ----------
        cv2.imshow("Plate Reader - Press q to quit", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            snap = os.path.join(SAVE_DIR, f"snapshot_{ts}.jpg")
            cv2.imwrite(snap, frame)
            print(f"[SNAP] {snap}")

    # ---------- پاکسازی ----------
    cam.release()
    cv2.destroyAllWindows()
    db.close()
    print("[INFO] Exited.")


if __name__ == "__main__":
    main()