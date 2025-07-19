import os
import re
import tempfile
from typing import Dict, Any, Tuple

# Optional heavy imports guarded – they might not exist in every env
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    Image = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import cv2  # OpenCV for deskew / threshold
except ImportError:
    cv2 = None

from app.errors import W2ParseError

TESSERACT_CONFIG_NUM = "--psm 6 -c tessedit_char_whitelist=0123456789.
"

class W2Parser:
    """Parse W-2 data from PDFs or images with advanced OCR preprocessing."""

    _patterns = {
        # Employer + Employee Info
        'employer_name': re.compile(r"Employer's name\s*:?\s*(.+?)\s{2,}"),
        'employee_name': re.compile(r"Employee's name(?:\s+)?(.+?)\s{2,}"),
        'employer_ein': re.compile(r"Employer's EIN\s*:?\s*([0-9\-]{10})"),
        # Federal boxes
        'wages': re.compile(r"Wages, tips, other comp\.\s*\$?([0-9,\.]+)"),
        'federal_withholding': re.compile(r"Federal income tax withheld\s*\$?([0-9,\.]+)"),
        # Social security / Medicare
        'social_security_wages': re.compile(r"Social security wages\s*\$?([0-9,\.]+)"),
        'social_security_tax': re.compile(r"Social security tax withheld\s*\$?([0-9,\.]+)"),
        'medicare_wages': re.compile(r"Medicare wages and tips\s*\$?([0-9,\.]+)"),
        'medicare_tax': re.compile(r"Medicare tax withheld\s*\$?([0-9,\.]+)"),
        # State boxes
        'state_wages': re.compile(r"State wages, tips, etc\.\s*\$?([0-9,\.]+)"),
        'state_withholding': re.compile(r"State income tax\s*\$?([0-9,\.]+)"),
    }

    def _clean_text(self, txt: str) -> str:
        return re.sub(r"\s+", " ", txt)

    def _extract_number(self, pattern: re.Pattern, txt: str) -> float:
        m = pattern.search(txt)
        if m:
            return float(m.group(1).replace(',', ''))
        return 0.0

    def _parse_text(self, txt: str) -> Dict[str, Any]:
        if not txt:
            raise W2ParseError('Empty text extracted from document')
        txt = self._clean_text(txt)
        data: Dict[str, Any] = {}
        for key, pat in self._patterns.items():
            if 'withholding' in key or 'wages' in key or 'tax' in key:
                data[key] = self._extract_number(pat, txt)
            else:
                m = pat.search(txt)
                data[key] = m.group(1).strip() if m else None
        return data

    # PDF Parsing
    def _parse_pdf(self, path: str) -> str:
        if not pdfplumber:
            raise W2ParseError('pdfplumber not installed')
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text_parts.append(page.extract_text() or '')
        return "
".join(text_parts)

    # Image OCR helpers
    def _preprocess_image(self, img_path: str) -> str:
        if not Image:
            raise W2ParseError('Pillow not installed')
        img = Image.open(img_path)
        # Convert to grayscale for better OCR accuracy
        img = ImageOps.grayscale(img)
        # Increase contrast / sharpness
        img = img.filter(ImageFilter.MedianFilter())
        img = ImageOps.autocontrast(img)
        # Deskew using OpenCV if available
        if cv2:
            cv_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            coords = cv2.findNonZero(cv2.threshold(cv_img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1])
            if coords is not None:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                (h, w) = cv_img.shape[:2]
                M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
                cv_img = cv2.warpAffine(cv_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                cv2.imwrite(tmp.name, cv_img)
                img = Image.open(tmp.name)
        # Save temp processed image
        processed = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(processed.name, dpi=(300,300))
        return processed.name

    def _ocr(self, img_path: str) -> str:
        if not pytesseract:
            raise W2ParseError('pytesseract not installed')
        # digits config for numeric lines helps accuracy but we first run generic
        text = pytesseract.image_to_string(Image.open(img_path), config='--psm 6')
        return text

    def _parse_image(self, path: str) -> str:
        processed = self._preprocess_image(path)
        return self._ocr(processed)

    # Public parse
    def parse_file(self, path: str, content_type: str = '') -> Tuple[Dict[str, Any], str]:
        try:
            if content_type == 'application/pdf' or path.lower().endswith('.pdf'):
                raw = self._parse_pdf(path)
                return self._parse_text(raw), 'pdf'
            else:
                raw = self._parse_image(path)
                return self._parse_text(raw), 'image'
        except Exception as e:
            raise W2ParseError(str(e)) from e
