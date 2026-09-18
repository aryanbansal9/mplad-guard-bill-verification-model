from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid

# Internal schemas
from backend.models import VerificationResponse, ExtractedBillData, GFRComplianceReport, BillLineItem

app = FastAPI(
    title="MPLADS Guardian API", 
    description="AI-powered backend for GFR 154 compliance and bill verification",
    version="1.0.0"
)

# Allow the frontend to communicate with the FastAPI backend securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {"status": "active", "module": "MPLADS Guardian Engine"}

@app.post("/api/verify-bill", response_model=VerificationResponse)
async def verify_procurement_bill(file: UploadFile = File(...)):
    """
    Ingests a raw bill image, runs OCR, standardizes items, and checks GFR Rule 154.
    """
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Only JPG/PNG images are allowed.")

    # =============================================================
    # MOCK RESPONSE (Allows frontend testing while we build the AI)
    # =============================================================
    mock_extracted = ExtractedBillData(
        vendor_name="Shri Ram Building Materials",
        bill_date="2026-08-15",
        total_amount=49999.00,  # Flag: Just under the 50k threshold limit
        line_items=[
            BillLineItem(item_description="Eent", standardized_item="Brick", quantity=1000, unit_price=10.0),
            BillLineItem(item_description="Cement", standardized_item="Cement", quantity=50, unit_price=799.98)
        ]
    )

    mock_compliance = GFRComplianceReport(
        is_compliant=False,
        flag_reason="GFR 154 Violation Alert: Total amount exactly at ₹49,999 evasion threshold. Vendor flagged 6 times in District.",
        vendor_frequency_count=6,
        confidence_score=0.92
    )

    return VerificationResponse(
        transaction_id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
        document_classification="Handwritten Receipt (Kaccha Bill)",
        extracted_data=mock_extracted,
        compliance_report=mock_compliance
    )