import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv
from backend.models import ExtractedBillData, BillLineItem

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLM_Parser")

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is missing from the .env file!")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Using gemini-1.5-flash for lightning-fast hackathon responses
model = genai.GenerativeModel('gemini-1.5-flash')

def parse_raw_text_to_json(raw_text: str) -> ExtractedBillData:
    """
    Passes the messy OCR text to Gemini to extract structured fields.
    Forces the LLM to return a strict JSON payload.
    """
    prompt = f"""
    You are an AI data extractor for the Indian government's MPLADS scheme.
    Extract the following information from the provided raw OCR text of a handwritten procurement bill.
    
    Return ONLY a valid JSON object matching this exact schema:
    {{
        "vendor_name": "Name of the shop or supplier (String)",
        "bill_date": "YYYY-MM-DD (String)",
        "total_amount": float (Total bill amount),
        "line_items": [
            {{
                "item_description": "Raw name of the item (String)",
                "quantity": float,
                "unit_price": float
            }}
        ]
    }}
    
    Rules:
    - If a value is missing, infer it from context or use a sensible default (e.g., 0.0 for amounts, "Unknown" for strings).
    - Do not include markdown formatting or code blocks in your response. Just the raw JSON.
    
    Raw OCR Text:
    {raw_text}
    """
    
    try:
        logger.info("Sending OCR text to Gemini for structuring...")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        
        # Parse the JSON string returned by Gemini
        extracted_dict = json.loads(response.text)
        
        # Validate and convert to our Pydantic model
        structured_data = ExtractedBillData(**extracted_dict)
        logger.info(f"Successfully structured data for vendor: {structured_data.vendor_name}")
        
        return structured_data
        
    except Exception as e:
        logger.error(f"LLM Parsing failed: {str(e)}")
        # Fallback empty data if LLM fails during live demo
        return ExtractedBillData(
            vendor_name="LLM_Extraction_Failed",
            bill_date="1970-01-01",
            total_amount=0.0,
            line_items=[]
        )