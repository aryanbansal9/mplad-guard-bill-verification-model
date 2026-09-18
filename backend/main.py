from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import logging

# AI Models & Engine Modules
from backend.models import VerificationResponse
from backend.ocr_engine import extract_raw_text_from_image
from backend.llm_parser import parse_raw_text_to_json
from backend.rule_engine import evaluate_gfr_154_compliance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MPLADS_API")

app = FastAPI(
    title="MPLADS Guardian API", 
    description="Multi-parameter anomaly detection engine for GFR 154 compliance and bill verification",
    version="2.0.0"
)

# Secure cross-origin access for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "active", "engine": "MPLADS Guardian Advanced Rules Engine v2"}

@app.post("/api/verify-bill", response_model=VerificationResponse)
async def verify_procurement_bill(file: UploadFile = File(...)):
    """
    1. Reads incoming physical procurement bill / UC document.
    2. Runs OpenCV preprocessing & EasyOCR extraction.
    3. Normalizes unstructured text into structured JSON via Gemini LLM.
    4. Executes multi-parameter GFR 154 audit (velocity, price benchmarks, ghost vendors).
    """
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Only JPG and PNG document images are accepted.")

    try:
        # Read raw image buffer
        image_bytes = await file.read()
        logger.info(f"Initiating verification for: {file.filename}")

        # Step A: Computer Vision & OCR Extraction
        raw_text = extract_raw_text_from_image(image_bytes)
        
        # Step B: LLM Schema Parsing
        extracted_data = parse_raw_text_to_json(raw_text)
        
        # Step C: Multi-Parameter Contextual Anomaly Engine
        # (Standardizes inventory, audits prices, verifies GFR 154 threshold, checks 30d velocity & ghost vendors)
        compliance_report = evaluate_gfr_154_compliance(extracted_data)

        # Return standardized verification payload
        return VerificationResponse(
            transaction_id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
            document_classification="Handwritten Receipt (Kaccha Bill)",
            extracted_data=extracted_data,
            compliance_report=compliance_report
        )

    except Exception as e:
        logger.error(f"Verification pipeline failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing Pipeline Error: {str(e)}")