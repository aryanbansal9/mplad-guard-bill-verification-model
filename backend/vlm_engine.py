import os
import io
import json
import torch
import logging
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
import google.generativeai as genai

logger = logging.getLogger("VLM_Engine")

class HybridVerificationEngine:
    def __init__(self):
        # Auto-detect SIH evaluator hardware
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.active_hardware = "NVIDIA RTX 4060 (Local Edge Qwen2-VL)" if self.device == "cuda" else "Cloud Fallback (Gemini 1.5 Flash)"
        
        self.model_id = "Qwen/Qwen2-VL-2B-Instruct"
        self.processor = None
        self.model = None
        self.is_loaded = False

    def load_model(self):
        """Loads the Edge VLM only if an NVIDIA GPU is present. Otherwise, readies the Cloud Fallback."""
        if self.device != "cuda":
            logger.warning("No CUDA GPU detected. Bypassing local VLM. System will use Gemini Cloud Fallback.")
            # Ensure you have your Gemini API key set in your environment variables for this fallback
            genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE"))
            return

        if self.is_loaded:
            return

        logger.info(f"Loading {self.model_id} into {self.device} memory...")
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            self.model_id,
            torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            device_map=self.device
        )
        
        self.is_loaded = True
        logger.info(f"Edge Model loaded successfully. Peak VRAM: {torch.cuda.memory_allocated(0) / (1024**2):.2f} MB")

    def extract_document_data(self, image_bytes: bytes) -> dict:
        """Routes the image to the GPU if available, or the Cloud if not."""
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        prompt_text = (
            "You are an expert Indian financial forensic auditor. Analyze this government procurement document, tax invoice, or completion certificate. "
            "If the document contains Hindi or regional Indian languages, translate the extracted data to English. "
            "Extract the following details in strict JSON format. Use null if a field is not present. Do not include markdown wrappers. \n"
            "{\n"
            '  "document_type": "Exact classification (e.g., Tax Invoice, Completion Certificate, Receipt)",\n'
            '  "vendor_name": "Name of the issuing contractor or shop",\n'
            '  "vendor_gstin": "15-character alphanumeric GSTIN",\n'
            '  "hsn_sac_codes": ["Array of extracted HSN/SAC codes"],\n'
            '  "invoice_date": "DD/MM/YYYY",\n'
            '  "base_amount": "Numerical value before tax",\n'
            '  "cgst_amount": "Central GST numerical value",\n'
            '  "sgst_amount": "State GST numerical value",\n'
            '  "igst_amount": "Integrated GST numerical value",\n'
            '  "total_billed_amount": "Final numerical value including all taxes",\n'
            '  "payment_status": "Paid, Pending, or Due",\n'
            '  "has_official_stamp": true or false,\n'
            '  "has_physical_signature": true or false,\n'
            '  "has_digital_signature": true or false,\n'
            '  "detected_languages": ["Array of languages detected in the image"]\n'
            "}"
        )

        if self.device == "cuda":
            return self._run_local_qwen(image, prompt_text)
        else:
            return self._run_gemini_fallback(image, prompt_text)

    def _run_local_qwen(self, image: Image.Image, prompt_text: str) -> dict:
        if not self.is_loaded:
            raise RuntimeError("VLM Model is not loaded. Call load_model() first.")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt_text},
                ],
            }
        ]

        text_prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)

        inputs = self.processor(
            text=[text_prompt],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt"
        ).to(self.device)

        logger.info("Executing local Qwen2-VL inference on Edge GPU...")
        with torch.no_grad():
            generated_ids = self.model.generate(**inputs, max_new_tokens=512)

        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        output_text = self.processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        
        return self._clean_and_parse_json(output_text)

    def _run_gemini_fallback(self, image: Image.Image, prompt_text: str) -> dict:
        logger.info("Hardware fallback triggered: Executing Gemini 1.5 Flash Cloud inference...")
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([prompt_text, image])
        return self._clean_and_parse_json(response.text)

    def _clean_and_parse_json(self, raw_text: str) -> dict:
        clean_json_str = raw_text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_json_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from engine. Raw output: {clean_json_str}")
            return {"error": "JSON Parsing Failed", "raw_output": clean_json_str}

vlm_engine = HybridVerificationEngine()