import os
import io
from typing import List, Dict, Union
from pathlib import Path
import pytesseract
from PIL import Image
import numpy as np

if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class OCRCatalogProcessor:
    def process_image(self, image_path: Union[str, bytes]) -> Dict:
        try:
            if isinstance(image_path, bytes):
                image = Image.open(io.BytesIO(image_path))
            else:
                image = Image.open(image_path)
            
            text = pytesseract.image_to_string(image.convert('RGB'), lang='eng')
            products = self._extract_products(text)
            
            return {
                'raw_text': text,
                'extracted_products': products,
                'product_count': len(products)
            }
        except Exception as e:
            return {'raw_text': '', 'extracted_products': [], 'error': str(e)}
    
    def _extract_products(self, text: str) -> List[Dict]:
        import re
        products = []
        for line in text.split('\n'):
            match = re.search(r'KSh[\s]*([0-9,]+)', line)
            if match:
                price = float(match.group(1).replace(',', ''))
                name = line[:match.start()].strip(' -:')
                if name:
                    products.append({'product_name': name, 'price': price, 'currency': 'KES'})
        return products

def scan_catalog(file_path: str, file_type: str = 'auto') -> Dict:
    processor = OCRCatalogProcessor()
    return processor.process_image(file_path)
