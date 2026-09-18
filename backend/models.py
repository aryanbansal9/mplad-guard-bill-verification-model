from pydantic import BaseModel, Field
from typing import List, Optional

class BillLineItem(BaseModel):
    item_description: str
    standardized_item: Optional[str] = None
    quantity: float
    unit_price: float

class ExtractedBillData(BaseModel):
    vendor_name: str
    bill_date: str = Field(..., description="YYYY-MM-DD format")
    total_amount: float
    work_id: Optional[str] = Field(None, description="Extracted e-Sakshi Work ID (e.g., WS/MP620/...)")
    line_items: List[BillLineItem]
    # NEW: Capturing AI extraction confidence for the Lexical Fraud check
    overall_confidence: float = Field(0.95, description="Mocked OCR confidence score until EasyOCR bounding boxes are fully mapped")

class GFRComplianceReport(BaseModel):
    risk_score: int = Field(..., description="0-30 (Safe), 31-70 (Review), 71-100 (Critical/Block)")
    risk_level: str = Field(..., description="'Low', 'Medium', or 'High'")
    flags: List[str] = Field(default_factory=list, description="List of specific anomalies triggered (e.g., Velocity, Benfords Law)")
    vendor_30d_velocity: float = Field(..., description="Total amount paid to this vendor in the last 30 days")
    is_registered_vendor: bool

class VerificationResponse(BaseModel):
    transaction_id: str
    document_classification: str
    extracted_data: ExtractedBillData
    compliance_report: GFRComplianceReport