from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
import logging

from backend.vlm_engine import vlm_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MPLADS_API")

# Load the VLM into GPU memory when the server starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up server - Initializing Local Edge VLM...")
    vlm_engine.load_model()
    yield
    logger.info("Shutting down server - Clearing VRAM...")

app = FastAPI(
    title="MPLADS Guardian API", 
    description="100% Offline Multi-parameter anomaly detection engine using Edge VLM",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "active", "engine": "Offline Qwen2-VL Edge Architecture active"}

@app.post("/api/verify-bill")
async def verify_procurement_bill(file: UploadFile = File(...)):
    allowed_extensions = ('.png', '.jpg', '.jpeg')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Only JPG and PNG images are accepted.")

    try:
        file_bytes = await file.read()
        logger.info(f"Initiating offline verification for: {file.filename}")

        # Step 1: Direct VLM Image-to-JSON Extraction
        extracted_data = vlm_engine.extract_document_data(file_bytes)
        
        # In the next step, we will re-integrate the Rule Engine here
        # based on whether the document_type is a WCC or a Retail Bill.

        return {
            "system_audit_id": f"REQ-{uuid.uuid4().hex[:8].upper()}",
            "hardware_accelerator": vlm_engine.active_hardware,
            "extracted_data": extracted_data
        }

    except Exception as e:
        logger.error(f"Verification pipeline failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing Pipeline Error: {str(e)}")