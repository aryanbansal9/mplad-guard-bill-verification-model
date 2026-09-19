from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
import logging

# Import the new modular architecture
from src.core.extractor.vlm_engine import vlm_engine
from src.core.verifiers.rule_engine import rule_engine
from src.core.decision.evaluator import decision_engine
from src.schemas.response import VerificationResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MPLADS_API")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up server - Initializing Local Edge VLM...")
    vlm_engine.load_model()
    yield
    logger.info("Shutting down server - Clearing VRAM...")

app = FastAPI(
    title="MPLADS Guardian API", 
    description="Explainable Document Decision Engine",
    version="4.0.0", 
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
    return {"status": "active", "architecture": "Phase 1 - Enterprise Explainable Engine"}

@app.post("/api/verify-bill", response_model=VerificationResponse)
async def verify_procurement_bill(file: UploadFile = File(...)):
    allowed_extensions = ('.png', '.jpg', '.jpeg')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Only JPG and PNG images are supported.")

    try:
        file_bytes = await file.read()
        logger.info(f"Initiating verification pipeline for: {file.filename}")

        # Layer 1: Extraction (Qwen2-VL / Gemini Fallback)
        extracted_data = vlm_engine.extract_document_data(file_bytes)

        # Layer 2: Verification Engines (Authenticity, Project, Financial)
        auth_score, proj_score, fin_score, evidences = rule_engine.analyze_bill(extracted_data)

        # Layer 3: Explainable Decision & Scoring
        audit_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
        
        final_report = decision_engine.evaluate(
            audit_id=audit_id,
            auth_score=auth_score,
            proj_score=proj_score,
            fin_score=fin_score,
            evidences=evidences,
            extracted_data=extracted_data,
            hardware=vlm_engine.active_hardware
        )

        return final_report

    except Exception as e:
        logger.error(f"Verification pipeline failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing Pipeline Error: {str(e)}")