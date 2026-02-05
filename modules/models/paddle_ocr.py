import numpy as np
import re
from PIL import Image
from paddleocr import PaddleOCR
from modules.data.receipt_data import ItemData, ReceiptData
from .base import AIModel

class PaddleOCRModel(AIModel):
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)

    def run(self, image: Image.Image) -> ReceiptData:
        img_array = np.array(image.convert("RGB"))
        result = self.ocr.ocr(img_array, cls=True)
        
        raw_elements = []
        if result and result[0]:
            for line in result[0]:
                box = line[0]
                text = line[1][0]
                # Calculate center Y and height of the text box
                y_top = box[0][1]
                y_bottom = box[2][1]
                y_center = (y_top + y_bottom) / 2
                height = y_bottom - y_top
                x_start = box[0][0]
                raw_elements.append({"text": text, "y": y_center, "x": x_start, "h": height})

        # Dynamic threshold based on average text height
        if raw_elements:
            avg_height = sum(e['h'] for e in raw_elements) / len(raw_elements)
            # Group items only if they are within 40% of the text height vertically
            threshold = avg_height * 0.4 
        else:
            threshold = 10

        lines = self._group_text_to_lines(raw_elements, threshold=threshold)
        
        print("--- PaddleOCR Grouped Lines ---")
        for l in lines: print(l)
        print("--------------------------------")

        return self._formatting(lines)
    
    def _group_text_to_lines(self, elements, threshold=20):
        if not elements: return []
        
        # Sort by vertical position (Y)
        elements.sort(key=lambda x: x['y'])
        
        grouped_lines = []
        if not elements: return []
        
        current_group = [elements[0]]
        
        for i in range(1, len(elements)):
            if abs(elements[i]['y'] - elements[i-1]['y']) <= threshold:
                current_group.append(elements[i])
            else:
                # Sort the current line by X (left to right) before merging
                current_group.sort(key=lambda x: x['x'])
                line_text = " ".join([item['text'] for item in current_group])
                grouped_lines.append(line_text)
                current_group = [elements[i]]
        
        # Add the last group
        current_group.sort(key=lambda x: x['x'])
        grouped_lines.append(" ".join([item['text'] for item in current_group]))
        
        return grouped_lines

    def _formatting(self, lines: list[str]) -> ReceiptData:
        items = []
        detected_total = 0.0
        
        # Look for a name followed by a number that has . or , inside it
        price_pattern = re.compile(r"(.+?)\s+(\d+[.,][\d.,]+)")

        for line in lines:
            line = line.strip()
            match = price_pattern.search(line)
            
            if match:
                name_part = match.group(1).strip()
                price_str = match.group(2).strip()
                
                clean_price = self._parse_price(price_str)
                lower_name = name_part.lower()

                # Filter out Non-items
                if "total" in lower_name and "sub" not in lower_name:
                    detected_total = clean_price
                elif any(k in lower_name for k in ["tax", "pajak", "service", "sub", "disc", "pax", "qty"]):
                    continue
                elif len(name_part) > 2:
                    # Clean quantity "1 " from start or end
                    name_part = re.sub(r'^\d+\s+', '', name_part)
                    name_part = re.sub(r'\s+\d+$', '', name_part)

                    items.append(ItemData(name=name_part, count=1, total_price=clean_price))

        # Fallback: Sum items if no total found
        if detected_total == 0 and items:
            detected_total = sum(i.total_price for i in items)

        # SAFETY: If no items found, return a placeholder to prevent 'KeyError: total_price'
        if not items:
            print("Warning: PaddleOCR found no items. Returning dummy.")
            items.append(ItemData(name="OCR Failed to read items", count=1, total_price=0.0))

        return ReceiptData(items={it.id: it for it in items}, total=detected_total)

    def _parse_price(self, p_str):
        """Standardizes Indonesian price formats."""
        try:
            # Remove all non-numeric chars except . and ,
            clean = re.sub(r'[^\d.,]', '', p_str)
            
            # If both exist (e.g. 1.250,00)
            if ',' in clean and '.' in clean:
                if clean.rfind(',') > clean.rfind('.'): # Comma is decimal
                    return float(clean.replace('.', '').replace(',', '.'))
                else: # Dot is decimal
                    return float(clean.replace(',', ''))
            
            # If only one exists, treat it as thousands separator for IDR
            # (e.g. 59.000 or 59,000)
            return float(clean.replace(',', '').replace('.', ''))
        except:
            return 0.0