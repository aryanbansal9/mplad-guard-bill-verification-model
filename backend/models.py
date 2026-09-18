from pydantic import BaseModel, Field
from typing import List, Optional

class BillLineItem(BaseModel):
    item_description: str = Field(..., description="Raw text of the item from the bill (e.g., 'Eent')")
    standardized_item: Optional[str] = Field(None, description="Mapped standardized item via FuzzyWuzzy (e.g., 'Brick')")
    quantity: float
    unit_price: float

class ExtractedBillData(BaseModel):
    vendor_name: str = Field(..., description="Name of the supplier/vendor")
    bill_date: str
    total_amount: float = Field(..., description="Total invoice amount to check against GFR 154")
    line_items: List[BillLineItem]

class GFRComplianceReport(BaseModel):
    is_compliant: bool
    flag_reason: Optional[str] = Field(None, description="Detailed explanation if flagged for evasion")
    vendor_frequency_count: int = Field(..., description="Number of times this vendor appears in the district DB")
    confidence_score: float

class VerificationResponse(BaseModel):
    transaction_id: str
    document_classification: str = Field(..., description="'Handwritten Receipt', 'Digital Tax Invoice', etc.")
    extracted_data: ExtractedBillData
    compliance_report: GFRComplianceReport