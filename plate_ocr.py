# plate_ocr.py
# -*- coding: utf-8 -*-
"""
OCR مخصوص پلاک خودروهای ایرانی
الگوی پلاک: [۲ رقم] [۱ حرف فارسی] [۳ رقم] ایران [۲ رقم]
مثال: ۱۲ ب ۳۴۵ ایران ۶۷
"""

import cv2
import numpy as np
import easyocr
import re
from config import OCR_LANGUAGES, USE_GPU


# ==================== ثابت‌ها ====================

# حروف مجاز پلاک ایرانی
IRANIAN_PLATE_LETTERS = ['ب', 'ج', 'د', 'س', 'ص', 'ط', 'ق', 'ل', 'م', 'ن', 'و', 'ه', 'ی']

# معادل لاتین حروف فارسی (برای وقتی که OCR اشتباهاً لاتین می‌خونه)
LATIN_TO_PERSIAN_LETTER = {
    'B': 'ب', 'C': 'ج', 'D': 'د', 'S': 'س', 'T': 'ط',
    'G': 'ق', 'L': 'ل', 'M': 'م', 'N': 'ن', 'V': 'و',
    'H': 'ه', 'Y': 'ی', 'P': 'ب', 'A': 'ب', 'E': 'ب',
    'K': 'ک', 'F': 'ق', 'I': 'ی', 'J': 'ج', 'O': 'و',
    'Q': 'ق', 'R': 'د', 'U': 'و', 'W': 'و', 'X': 'س',
    'Z': 'ط',
}

# اصلاح اعدادی که OCR اشتباه به حرف تبدیل می‌کند
LETTER_TO_DIGIT = {
    'O': '0', 'o': '0', 'Q': '0', 'D': '0',
    'I': '1', 'i': '1', 'L': '1', 'l': '1', '|': '1',
    'Z': '2', 'z': '2',
    'E': '3',
    'A': '4',
    'S': '5', 's': '5',
    'G': '6', 'b': '6',
    'T': '7',
    'B': '8',
    'g': '9', 'q': '9',
}

# تبدیل اعداد فارسی و عربی به لاتین
PERSIAN_DIGITS = '۰۱۲۳۴۵۶۷۸۹'
ARABIC_DIGITS = '٠١٢٣٤٥٦٧٨٩'
LATIN_DIGITS = '0123456789'
DIGIT_TRANS_TABLE = str.maketrans(
    PERSIAN_DIGITS + ARABIC_DIGITS,
    LATIN_DIGITS + LATIN_DIGITS
)


# ==================== کلاس اصلی ====================

class PlateOCR:
    def __init__(self):
        print("[OCR] Loading EasyOCR model... (first run may download weights)")
        # برای پلاک ایرانی: fa (فارسی) + en (انگلیسی برای اعداد)
        self.reader = easyocr.Reader(OCR_LANGUAGES, gpu=USE_GPU, verbose=False)
        print("[OCR] Ready.")

    # ---------- پیش‌پردازش تصویر ----------

    def _preprocess(self, img):
        """
        پیش‌پردازش قوی برای بهبود دقت OCR:
        1. بزرگ‌نمایی
        2. خاکستری
        3. حذف نویز (Bilateral)
        4. بهبود کنتراست (CLAHE)
        5. آستانه‌گذاری Otsu
        6. مورفولوژی برای تمیزکاری
        """
        if img is None or img.size == 0:
            return None, None

        # 1. بزرگ‌نمایی (ارتفاع هدف: 100 پیکسل)
        h, w = img.shape[:2]
        target_h = 100
        scale = max(1.0, target_h / max(h, 1))
        if scale > 1.0:
            img = cv2.resize(img, None, fx=scale, fy=scale,
                             interpolation=cv2.INTER_CUBIC)

        # 2. خاکستری
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # 3. حذف نویز
        gray = cv2.bilateralFilter(gray, 11, 17, 17)

        # 4. بهبود کنتراست
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # 5. آستانه‌گذاری Otsu
        _, thresh = cv2.threshold(gray, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 6. تمیزکاری با مورفولوژی (کمی)
        kernel = np.ones((2, 2), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

        # اطمینان از 3 کاناله بودن برای EasyOCR
        color_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        binary_img = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

        return color_img, binary_img

    # ---------- نرمال‌سازی متن ----------

    def _normalize_digits(self, text: str) -> str:
        """تبدیل اعداد فارسی/عربی به لاتین"""
        return text.translate(DIGIT_TRANS_TABLE)

    def _remove_invalid_chars(self, text: str) -> str:
        """حذف کاراکترهای غیرمجاز"""
        # فقط حروف فارسی، حروف لاتین، اعداد و فاصله
        text = re.sub(r'[^آ-یA-Za-z0-9\s]', '', text)
        # یکسان‌سازی فاصله‌ها
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _fix_common_ocr_errors(self, text: str) -> str:
        """
        اصلاح خطاهای رایج OCR:
        - حروفی که اشتباهاً به جای عدد خونده شدن
        - اعدادی که اشتباهاً به جای حرف خونده شدن
        """
        # کلمه "ایران" رو حذف کن (چون روی همه پلاک‌ها هست)
        text = text.replace('ایران', ' ').replace('ايران', ' ')

        # حذف فاصله‌های اضافی
        text = re.sub(r'\s+', ' ', text).strip()

        # الان متن شامل: [2 رقم] [1 حرف] [5 رقم] هست
        # جدا کردن حروف و اعداد
        parts = text.split()
        fixed_parts = []

        for part in parts:
            # اگر فقط عدد بود، اصلاح کن
            if re.match(r'^[0-9]+$', part):
                # اعداد خالص، نیازی به اصلاح ندارن (مگر حروف لاتین داخلش باشه)
                fixed_parts.append(part)
            # اگر ترکیبی از حروف و اعداد بود
            elif re.search(r'[0-9]', part) and re.search(r'[A-Za-z]', part):
                # احتمالاً حروف لاتین در کنار عدد، اصلاح کن
                fixed = ''
                for ch in part:
                    if ch in LETTER_TO_DIGIT and ch.isalpha():
                        fixed += LETTER_TO_DIGIT[ch]
                    else:
                        fixed += ch
                fixed_parts.append(fixed)
            else:
                # فقط حرف
                fixed_parts.append(part)

        return ' '.join(fixed_parts)

    def _normalize_persian_letters(self, text: str) -> str:
        """یکسان‌سازی حروف فارسی (ک/گ/ی/ة)"""
        text = text.replace('ك', 'ک').replace('ي', 'ی').replace('ة', 'ه')
        text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
        return text

    # ---------- اعتبارسنجی پلاک ایرانی ----------

    def _extract_valid_plate(self, text: str):
        """
        استخراج پلاک معتبر از متن خام.
        الگوی پلاک ایرانی:
        - 2 رقم + 1 حرف + 3 رقم (سمت چپ پلاک)
        - 2 رقم (سمت راست، کد شهر)
        ترتیب واقعی: [2 رقم سری] [1 حرف] [3 رقم وسط] [2 رقم ایران]

        خروجی: (متن نرمال‌شده، True/False)
        """
        if not text:
            return "", False

        # 1. حذف "ایران"
        text = text.replace('ایران', ' ').replace('ايران', ' ')

        # 2. نرمال‌سازی حروف
        text = self._normalize_persian_letters(text)

        # 3. اصلاح خطاهای رایج
        text = self._fix_common_ocr_errors(text)

        # 4. حذف کاراکترهای غیرمجاز
        text = self._remove_invalid_chars(text)

        # 5. استخراج فقط اعداد و حروف فارسی
        # الگوی هدف: 2رقم + حرف + 5رقم  (چون 3رقم وسط + 2رقم شهر = 5 رقم پشت سر هم)
        # یا ممکنه با فاصله باشه

        # حذف فاصله‌ها برای تطبیق بهتر
        compact = re.sub(r'\s+', '', text)

        # الگوی 1: دقیقاً مطابق با پلاک ایرانی
        # 2 رقم لاتین + 1 حرف فارسی + 5 رقم لاتین
        pattern1 = r'^(\d{2})([' + ''.join(IRANIAN_PLATE_LETTERS) + r'])(\d{5})$'
        m = re.match(pattern1, compact)
        if m:
            serial, letter, numbers = m.groups()
            formatted = f"{serial} {letter} {numbers[:3]} ایران {numbers[3:]}"
            return formatted, True

        # الگوی 2: با اعداد فارسی
        compact_fa = self._normalize_digits(compact)
        m = re.match(pattern1, compact_fa)
        if m:
            serial, letter, numbers = m.groups()
            formatted = f"{serial} {letter} {numbers[:3]} ایران {numbers[3:]}"
            return formatted, True

        # الگوی 3: خیلی انعطاف‌پذیرتر
        # 2 رقم + 1 حرف (فارسی یا لاتین) + 5 رقم، حتی اگه فاصله داشته باشه
        pattern2 = r'(\d{2})\s*([آ-یA-Za-z])\s*(\d{5})'
        m = re.search(pattern2, text)
        if m:
            serial, letter, numbers = m.groups()
            # اگه حرف لاتین بود، تبدیل کن
            if letter.isascii() and letter.isalpha():
                letter = LATIN_TO_PERSIAN_LETTER.get(letter.upper(), letter)
            # اطمینان از فارسی بودن حرف
            if letter in IRANIAN_PLATE_LETTERS:
                formatted = f"{serial} {letter} {numbers[:3]} ایران {numbers[3:]}"
                return formatted, True

        # الگوی 4: هیچ حرف فارسی پیدا نشد، فقط اعداد
        # اگر 7 رقم پشت سر هم داشتیم، احتمالاً پلاک هست
        all_digits = re.sub(r'\D', '', text)
        if len(all_digits) == 7:
            # فرض کن حرف رو از دست دادیم، با حرف پیش‌فرض "ب" فرمت کن
            formatted = f"{all_digits[:2]} ? {all_digits[2:5]} ایران {all_digits[5:]}"
            return formatted, True

        # الگوی 5: تطبیق خیلی شل - فقط اگه حداقل 6 رقم داشتیم
        if len(all_digits) >= 6:
            # به عنوان پلاک نامعتبر برگردون (چون حرف نداره)
            return text.strip(), False

        return text.strip(), False

    # ---------- تابع اصلی ----------

    def read_plate(self, plate_img):
        """
        خواندن پلاک از تصویر.
        خروجی: (متن پلاک، اطمینان)
        """
        if plate_img is None or plate_img.size == 0:
            return "", 0.0

        color_img, binary_img = self._preprocess(plate_img)
        if color_img is None:
            return "", 0.0

        # دو بار OCR: رنگ و باینری
        all_results = []

        try:
            # OCR روی تصویر رنگی
            results_color = self.reader.readtext(
                color_img,
                detail=1,
                paragraph=False,
                text_threshold=0.6,
                low_text=0.3,
                link_threshold=0.4,
            )
            all_results.extend(results_color)
        except Exception as e:
            print(f"[OCR] Color OCR error: {e}")

        try:
            # OCR روی تصویر binary
            results_bin = self.reader.readtext(
                binary_img,
                detail=1,
                paragraph=False,
                text_threshold=0.5,
                low_text=0.3,
                link_threshold=0.4,
            )
            all_results.extend(results_bin)
        except Exception as e:
            print(f"[OCR] Binary OCR error: {e}")

        if not all_results:
            return "", 0.0

        # مرتب‌سازی بر اساس محور X (چپ به راست)
        all_results.sort(key=lambda r: r[0][0][0])

        # ترکیب متن‌ها
        combined_text = " ".join([r[1] for r in all_results])
        avg_conf = float(np.mean([r[2] for r in all_results]))

        # استخراج پلاک معتبر
        plate_text, is_valid = self._extract_valid_plate(combined_text)

        # اگه پلاک معتبر نبود، با اطمینان پایین برگردون
        if not is_valid:
            return plate_text, avg_conf * 0.5  # کاهش اطمینان برای پلاک نامعتبر

        # فیلتر نهایی: اطمینان قابل قبول
        if avg_conf < 0.3:
            return "", 0.0

        return plate_text, avg_conf


# ==================== تست ====================

if __name__ == "__main__":
    # تست سریع
    import sys

    if len(sys.argv) < 2:
        print("Usage: python plate_ocr.py <image_path>")
        sys.exit(1)

    img = cv2.imread(sys.argv[1])
    if img is None:
        print("Cannot read image!")
        sys.exit(1)

    ocr = PlateOCR()
    text, conf = ocr.read_plate(img)
    print(f"\n{'='*40}")
    print(f"پلاک تشخیص داده شده: {text}")
    print(f"اطمینان: {conf:.3f}")
    print(f"{'='*40}")