import re
import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM

from modules.data.receipt_data import ItemData, ReceiptData
from .base import AIModel

MODEL_NAME = "microsoft/Florence-2-base"

class FlorenceModel(AIModel):
    """Receipt reader based on Microsoft Florence-2 Model."""

    def __init__(self) -> None:
        """Initialize the model and processor."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        # Florence-2 requires trust_remote_code=True
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME, 
            trust_remote_code=True,
            torch_dtype=self.torch_dtype,
            attn_implementation="eager"
        ).to(self.device)
        
        self.processor = AutoProcessor.from_pretrained(
            MODEL_NAME, 
            trust_remote_code=True
        )

    def run(self, image: Image.Image) -> ReceiptData:
        """Retrieve data from the receipt."""
        # 1. Run Inference
        generated_text = self._inference(image)
        
        # Debug: Print what the model actually saw
        print(f"--- Florence-2 Raw Output ---\n{generated_text}\n-----------------------------")

        # 2. Parse Text into Objects
        return self._formatting(generated_text)

    def _inference(self, image: Image.Image) -> str:
        """Run the actual model generation."""
        if image.mode != "RGB":
            image = image.convert("RGB")

        task_prompt = "<OCR>"
        
        inputs = self.processor(
            text=task_prompt, 
            images=image, 
            return_tensors="pt"
        ).to(self.device, self.torch_dtype)

        # Generate output with use_cache=False to prevent "shape" error
        generated_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            do_sample=False,
            num_beams=3,
            use_cache=False 
        )

        generated_text = self.processor.batch_decode(
            generated_ids, 
            skip_special_tokens=False
        )[0]

        parsed_answer = self.processor.post_process_generation(
            generated_text, 
            task=task_prompt, 
            image_size=(image.width, image.height)
        )

        return parsed_answer.get(task_prompt, "")

    def _formatting(self, text: str) -> ReceiptData:
        items: list[ItemData] = []
        detected_total = 0.0

        # Name: ([a-zA-Z0-9\s\-\(\)\.&]+?) 
        # Price: (\d+[.,][\d.,]+)
        pattern = re.compile(r"([a-zA-Z0-9\s\-\(\)\.&]+?)(\d+[.,][\d.,]+)")

        matches = pattern.findall(text)

        for name_raw, price_raw in matches:
            name = name_raw.strip()
            name = name.strip(".,- ")
            
            clean_price = _parse_price_idr(price_raw)
            
            if len(name) < 2 or clean_price == 0:
                continue

            lower_name = name.lower()

            if "total" in lower_name and "sub" not in lower_name:
                detected_total = clean_price
            elif any(keyword in lower_name for keyword in ["sub", "total", "tax", "pajak", "service", "layanan", "discount", "diskon", "cash", "kembali"]):
                continue
            else:
                # If price is huge (e.g. > 1 million for Chicken), it likely includes the quantity "1" at the front.
                # Expected: 190,000. Detected: 1,190,000 or 1190000.
                if clean_price > 1000000 and str(int(clean_price)).startswith('1'):
                     pass

                items.append(
                    ItemData(
                        name=name,
                        count=1, 
                        total_price=clean_price
                    )
                )

        if detected_total == 0.0 and items:
            detected_total = sum(item.total_price for item in items)
            
        if not items:
            items.append(ItemData(name="Unread Receipt", count=1, total_price=0.0))

        return ReceiptData(items={it.id: it for it in items}, total=detected_total)


def _parse_price_idr(price_str: str) -> float:
    """Parses IDR prices, robust to OCR noise."""
    try:
        clean_str = re.sub(r'[^\d.,]', '', price_str)
        
        if '.' not in clean_str and ',' not in clean_str:
            return float(clean_str)

        # If comma is at the end "159,000" -> remove comma
        if ',' in clean_str and '.' not in clean_str:
            return float(clean_str.replace(',', ''))
            
        # If dot is at the end "190.000" -> remove dot
        if '.' in clean_str and ',' not in clean_str:
            return float(clean_str.replace('.', ''))

        # Mixed "1.190,000" or "1,190.000"
        last_comma = clean_str.rfind(',')
        last_dot = clean_str.rfind('.')

        if last_comma > last_dot: 
            return float(clean_str.replace('.', '').replace(',', '.'))
        else:
            return float(clean_str.replace(',', ''))

    except ValueError:
        return 0.0