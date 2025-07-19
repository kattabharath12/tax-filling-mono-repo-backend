import os
import re
import tempfile
import logging
from typing import Dict, Any, Tuple

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
    import cv2
except ImportError:
    cv2 = None

from app.errors import W2ParseError

logger = logging.getLogger("w2_parser")
logging.basicConfig(level=logging.INFO)

class W2Parser:
    """Robust W-2 parser for both text-based and scanned PDFs."""

    # Each field has a list of patterns to try, for flexibility
    _patterns = {
        'employee_ssn': [
            re.compile(r"Employee'?s? social security number[:\s]*([0-9\-]{9,})", re.I),
            re.compile(r"SSN[:\s]*([0-9\-]{9,})", re.I),
        ],
        'employer_ein': [
            re.compile(r"Employer identification number \\(EIN\\)[:\s]*([A-Z0-9\-]+)", re.I),
            re.compile(r"Employer'?s? EIN[:\s]*([0-9\-]{9,})", re.I),
        ],
        'employer_name': [
            re.compile(r"Employer'?s? name, address, and ZIP code[:\s]*([A-Z ,0-9]+)", re.I),
            re.compile(r"Employer'?s? name[:\s]*([A-Z ,0-9]+)", re.I),
        ],
        'employee_first_name': [
            re.compile(r"Employee'?s? first name and initial[:\s]*([A-Z ]+)", re.I),
        ],
        'employee_last_name': [
            re.compile(r"Last name[:\s]*([A-Z ]+)", re.I),
        ],
        'wages': [
            re.compile(r"1[\\s\\.]?\\s*Wages, tips, other compensation[:\\s]*([0-9,\\.]+)", re.I),
            re.compile(r"Wages, tips, other compensation[:\\s]*([0-9,\\.]+)", re.I),
        ],
        'federal_withholding': [
            re.compile(r"2[\\s\\.]?\\s*Federal income tax withheld[:\\s]*([0-9,\\.]+)", re.I),
            re.compile(r"Federal income tax withheld[:\\s]*([0-9,\\.]+)", re.I),
        ],
        'social_security_wages': [
            re.compile(r"3[\\s\\.]?\\s*Social security wages[:\\s]*([0-9,\\.]+)", re.I),
            re.compile(r"Social security wages[:\\s]*([0-9,\\.]+)", re.I),
        ],
        'social_security_tax': [
            re.compile(r"4[\\s\\.]?\\s*Social security tax withheld[:\\s]*([0-9,\\.]+)", re.I),
            re.compile(r"Social security tax withheld[:\\s]*([0-9,\\.]+)", re.I),
        ],
        'medicare_wages': [
            re.compile(r"5[\\s\\.]?\\s*Medicare wages and tips[:\\s]*([0-9,\\.]+)", re.I),
            re.compile(r"Medicare wages and tips[:\\s]*([0-9,\\.]+)", re.I),
        ],
        'medicare_tax': [
            re.compile(r"6[\\s\\.]?\\s*Medicare tax withheld[:\\s]*([0-9,\\.]+)", re.I),
            re.compile(r"Medicare tax withheld[:\\s]*([0-9,\\.]+)", re.I),
        ],
        'state': [
            re.compile(r"15[\\s\\.]?\\s*State[:\\s]*([A-Z]{2})", re.I),
            re.compile(r"State[:\\s]*([A-Z]{2})", re.I),
        ],
        'employer_state_id': [
            re.compile(r"Employer'?s? state ID number[:\\s]*([A-Z0-9]+)", re.I),
        ],
        'state_wages': [
            re.compile(r"16[\\s\\.]?\\s*State wages, tips, etc[:\\s]*([0-9,\\.]+)", re.I),
            re.compile(r"State wages, tips, etc[:\\s]*([0-9,\\.]+)", re.I),
        ],
        'state_withholding': [
            re.compile(r"17[\\s\\.]?\\s*State income tax[:\\s]*([0-9,\\.]+)", re.I),
            re.compile(r"State income tax[:\\s]*([0-9,\\.]+)", re.I),
        ],
    }

    def _clean_text(self, txt: str) -> str:
        return re.sub(r"\s+", " ", txt)

    def _extract_field(self, patterns, txt, is_number=False):
        for pat in patterns:
            m = pat.search(txt)
            if m:
                val = m.group(1).replace(',', '').strip()
                if is_number:
                    try:
                        return float(val)
                    except Exception:
                        continue
                return val
        return None if not is_number else 0.0

    def _parse_text(self, txt: str) -> Dict[str, Any]:
        if not txt:
            raise W2ParseError('Empty text extracted from document')
        txt = self._clean_text(txt)
        logger.info(f"Extracted W-2 text: {txt[:500]}...")  # Log first 500 chars
        data: Dict[str, Any] = {}
        # Map which fields are numbers
        number_fields = {
            'wages', 'federal_withholding', 'social_security_wages', 'social_security_tax',
            'medicare_wages', 'medicare_tax', 'state_wages', 'state_withholding'
        }
        for key, patterns in self._patterns.items():
            data[key] = self._extract_field(patterns, txt, is_number=(key in number_fields))
        return data

    def _parse_pdf(self, path: str) -> str:
        if not pdfplumber:
            raise W2ParseError('pdfplumber not installed')
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                text_parts.append(text)
        return "\n".join(text_parts)

    def _preprocess_image(self, img_path: str) -> str:
        if not Image:
            raise W2ParseError('Pillow not installed')
        img = Image.open(img_path)
        img = ImageOps.grayscale(img)
        img = img.filter(ImageFilter.MedianFilter())
        img = ImageOps.autocontrast(img)
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
        processed = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(processed.name, dpi=(300,300))
        return processed.name

    def _ocr(self, img_path: str) -> str:
        if not pytesseract:
            raise W2ParseError('pytesseract not installed')
        text = pytesseract.image_to_string(Image.open(img_path), config='--psm 6')
        return text

    def _parse_image(self, path: str) -> str:
        processed = self._preprocess_image(path)
        return self._ocr(processed)

    def parse_file(self, path: str, content_type: str = '') -> Tuple[Dict[str, Any], str]:
        try:
            if content_type == 'application/pdf' or path.lower().endswith('.pdf'):
                raw = self._parse_pdf(path)
                # Fallback: If text is too short, try OCR on first page image
                if len(raw.strip()) < 50 and pdfplumber:
                    with pdfplumber.open(path) as pdf:
                        if pdf.pages:
                            img = pdf.pages[0].to_image(resolution=300)
                            tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                            img.save(tmp_img.name, format='PNG')
                            raw = self._ocr(tmp_img.name)
                return self._parse_text(raw), 'pdf'
            else:
                raw = self._parse_image(path)
                return self._parse_text(raw), 'image'
        except Exception as e:
            logger.error(f"W2ParseError: {e}")
            raise W2ParseError(str(e)) from e
