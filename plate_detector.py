# plate_detector.py
import cv2
import numpy as np
import imutils
from config import MIN_PLATE_AREA, MAX_PLATE_AREA


class PlateDetector:
    """
    تشخیص ناحیه پلاک با استفاده از:
    1) فیلتر دوطرفه (Bilateral Filter)
    2) Canny Edge Detection
    3) پیدا کردن کانتورهای مستطیلی با نسبت ابعاد مناسب پلاک
    """

    def __init__(self):
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))

    def preprocess(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 11, 17, 17)
        edged = cv2.Canny(gray, 30, 200)
        return gray, edged

    def find_candidates(self, frame):
        gray, edged = self.preprocess(frame)
        cnts = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:30]

        candidates = []
        for c in cnts:
            area = cv2.contourArea(c)
            if area < MIN_PLATE_AREA or area > MAX_PLATE_AREA:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.018 * peri, True)

            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect = w / float(h)
                # نسبت طول به عرض پلاک ایرانی/اروپایی بین 2 تا 6
                if 1.8 <= aspect <= 6.5:
                    candidates.append((x, y, w, h))

        return candidates, gray

    def crop_plate(self, frame, box):
        x, y, w, h = box
        pad = 5
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(frame.shape[1], x + w + pad)
        y2 = min(frame.shape[0], y + h + pad)
        return frame[y1:y2, x1:x2]

    def draw_boxes(self, frame, boxes, labels=None):
        out = frame.copy()
        for i, (x, y, w, h) in enumerate(boxes):
            cv2.rectangle(out, (x, y), (x + w, y + h), (0, 255, 0), 2)
            if labels and i < len(labels) and labels[i]:
                cv2.putText(out, labels[i], (x, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        return out