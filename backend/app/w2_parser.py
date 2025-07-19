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

    def _clean_text(self, txt: str) -> str:
        return re.sub(r"\s+", " ", txt)

    def _parse_text(self, txt: str) -> Dict[str, Any]:
        if not txt:
            raise W2ParseError('Empty text extracted from document')
        txt = self._clean_text(txt)
        logger.info(f"Extracted W-2 text: {txt[:500]}...")  # Log first 500 chars

        data: Dict[str, Any] = {}

        # Strategy 1: Clean format with colons and dollar signs (like w2-wages-2024.pdf)
        if "Employee's social security number:" in txt and "$" in txt:
            data = self._parse_clean_format(txt)
        # Strategy 2: Jumbled format (like w2 1 page.pdf)
        elif "Employer identitication number (EIN)" in txt:
            data = self._parse_jumbled_format(txt)
        # Strategy 3: Fallback - try to extract what we can
        else:
            data = self._parse_fallback_format(txt)

        return data

    def _parse_clean_format(self, txt: str) -> Dict[str, Any]:
        """Parse clean, colon-separated format with dollar signs."""

        def extract(pattern, is_money=False):
            m = re.search(pattern, txt, re.I)
            if m:
                val = m.group(1).replace(',', '').replace('$', '').strip()
                return float(val) if is_money else val
            return None if not is_money else 0.0

        return {
            "employee_ssn": extract(r"Employee'?s? social security number[:\s]*([0-9\-]{9,})"),
            "employer_ein": extract(r"Employer identification number[:\s]*([0-9\-]{9,})"),
            "employer_name": extract(r"Employer'?s? name and address:\s*([A-Za-z0-9 ,.&'-]+)"),
            "employee_first_name": extract(r"Employee'?s? name and address:\s*([A-Za-z]+)"),
            "employee_last_name": extract(r"Employee'?s? name and address:\s*[A-Za-z]+ ([A-Za-z]+)"),
            "wages": extract(r"1[.\)]? Wages, tips, other compensation[:\s]*\$?([0-9,\.]+)", is_money=True),
            "federal_withholding": extract(r"2[.\)]? Federal income tax withheld[:\s]*\$?([0-9,\.]+)", is_money=True),
            "social_security_wages": extract(r"3[.\)]? Social security wages[:\s]*\$?([0-9,\.]+)", is_money=True),
            "social_security_tax": extract(r"4[.\)]? Social security tax withheld[:\s]*\$?([0-9,\.]+)", is_money=True),
            "medicare_wages": extract(r"5[.\)]? Medicare wages and tips[:\s]*\$?([0-9,\.]+)", is_money=True),
            "medicare_tax": extract(r"6[.\)]? Medicare tax withheld[:\s]*\$?([0-9,\.]+)", is_money=True),
            "state": extract(r"([A-Z]{2}) [0-9]{5}"),
            "employer_state_id": None,
            "state_wages": 0.0,
            "state_withholding": 0.0
        }

    def _parse_jumbled_format(self, txt: str) -> Dict[str, Any]:
        """Parse jumbled format where values follow labels in sequence."""

        data: Dict[str, Any] = {}

        # EIN, Wages, Federal Withholding (all together)
        ein_block = re.search(
            r"Employer identitication number \(EIN\) 1 Wages, tips, other compensation 2 Federal income tax withheld\s*([A-Z0-9]+)\s+([0-9]+)\s+([0-9]+)",
            txt, re.I)
        if ein_block:
            data["employer_ein"] = ein_block.group(1)
            data["wages"] = float(ein_block.group(2))
            data["federal_withholding"] = float(ein_block.group(3))
        else:
            data["employer_ein"] = None
            data["wages"] = 0.0
            data["federal_withholding"] = 0.0

        # Social Security Wages & Tax
        ss_block = re.search(
            r"3 Social security wages 4 Social security tax withheld\s*([0-9]+)\s+([0-9]+)",
            txt, re.I)
        if ss_block:
            data["social_security_wages"] = float(ss_block.group(1))
            data["social_security_tax"] = float(ss_block.group(2))
        else:
            data["social_security_wages"] = 0.0
            data["social_security_tax"] = 0.0

        # Medicare Wages & Tax
        med_block = re.search(
            r"5 Medicare wages and tips 6 Medicare tax withheld\s*([0-9]+)\s+([0-9]+)",
            txt, re.I)
        if med_block:
            data["medicare_wages"] = float(med_block.group(1))
            data["medicare_tax"] = float(med_block.group(2))
        else:
            data["medicare_wages"] = 0.0
            data["medicare_tax"] = 0.0

        # Employer name/address (grab everything after "ZIP code" up to "3 Social security wages")
        emp_addr_block = re.search(
            r"ZIP code\s*(.*?)3 Social security wages", txt, re.I)
        if emp_addr_block:
            data["employer_name"] = emp_addr_block.group(1).strip()
        else:
            data["employer_name"] = None

        # Employee SSN (try to find it)
        ssn_block = re.search(r"Employee'?s? social security number.*?([0-9]{3}-[0-9]{2}-[0-9]{4})", txt, re.I)
        if ssn_block:
            data["employee_ssn"] = ssn_block.group(1)
        else:
            data["employee_ssn"] = None

        # Employee name (not always extractable in this format)
        data["employee_first_name"] = None
        data["employee_last_name"] = None

        # State info (not present in this sample format)
        data["state"] = None
        data["employer_state_id"] = None
        data["state_wages"] = 0.0
        data["state_withholding"] = 0.0

        return data

    def _parse_fallback_format(self, txt: str) -> Dict[str, Any]:
        """Fallback parser for unknown formats - extract what we can."""

        data: Dict[str, Any] = {}

        # Try to find common patterns with flexible matching
        patterns = {
            "employee_ssn": [
                r"([0-9]{3}-[0-9]{2}-[0-9]{4})",
                r"([0-9]{9})"
            ],
            "employer_ein": [
                r"EIN.*?([0-9]{2}-[0-9]{7})",
                r"identification.*?([0-9]{2}-[0-9]{7})"
            ],
            "wages": [
                r"Wages.*?([0-9,]+\.?[0-9]*)",
                r"1.*?compensation.*?([0-9,]+\.?[0-9]*)"
            ],
            "federal_withholding": [
                r"Federal.*?withheld.*?([0-9,]+\.?[0-9]*)",
                r"2.*?Federal.*?([0-9,]+\.?[0-9]*)"
            ]
        }

        # Extract using flexible patterns
        for field, field_patterns in patterns.items():
            data[field] = None
            for pattern in field_patterns:
                match = re.search(pattern, txt, re.I)
                if match:
                    val = match.group(1).replace(',', '').strip()
                    if field in ["wages", "federal_withholding"]:
                        try:
                            data[field] = float(val)
                            break
                        except ValueError:
                            continue
                    else:
                        data[field] = val
                        break

            # Set default values for numeric fields
            if field in ["wages", "federal_withholding"] and data[field] is None:
                data[field] = 0.0

        # Set remaining fields to defaults
        for field in ["employer_name", "employee_first_name", "employee_last_name",
                      "state", "employer_state_id"]:
            if field not in data:
                data[field] = None

        for field in ["social_security_wages", "social_security_tax",
                      "medicare_wages", "medicare_tax", "state_wages", "state_withholding"]:
            if field not in data:
                data[field] = 0.0

        return data

    def _parse_pdf(self, path: str) -> str:
        if not pdfplumber:
            raise W2ParseError('pdfplumber not installed')
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                text_parts.append(text)
        full_text = "\n".join(text_parts)
        print("=== W2 Extracted Text ===")
        print(full_text)
        return full_text

    def _preprocess_image(self, img_path: str) -> str:
        if not Image:
            raise W2ParseError('Pillow not installed')
        img = Image.open(img_path)
        img = ImageOps.grayscale(img)
        img = img.filter(ImageFilter.MedianFilter())
        img = ImageOps.autocontrast(img)
        if cv2:
            try:
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
            except Exception as e:
                logger.warning(f"OpenCV processing failed: {e}, using PIL only")

        processed = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(processed.name, dpi=(300,300))
        return processed.name

    def _ocr(self, img_path: str) -> str:
        if not pytesseract:
            raise W2ParseError('pytesseract not installed')
        try:
            text = pytesseract.image_to_string(Image.open(img_path), config='--psm 6')
            return text
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise W2ParseError(f"OCR processing failed: {e}")

    def _parse_image(self, path: str) -> str:
        processed = self._preprocess_image(path)
        return self._ocr(processed)

    def parse_file(self, path: str, content_type: str = '') -> Tuple[Dict[str, Any], str]:
        try:
            if content_type == 'application/pdf' or path.lower().endswith('.pdf'):
                raw = self._parse_pdf(path)
                # Fallback: If text is too short, try OCR on first page image
                if len(raw.strip()) < 50 and pdfplumber:
                    try:
                        with pdfplumber.open(path) as pdf:
                            if pdf.pages:
                                img = pdf.pages[0].to_image(resolution=300)
                                tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                                img.save(tmp_img.name, format='PNG')
                                raw = self._ocr(tmp_img.name)
                    except Exception as e:
                        logger.warning(f"OCR fallback failed: {e}")
                return self._parse_text(raw), 'pdf'
            else:
                raw = self._parse_image(path)
                return self._parse_text(raw), 'image'
        except Exception as e:
            logger.error(f"W2ParseError: {e}")
            raise W2ParseError(str(e)) from e
