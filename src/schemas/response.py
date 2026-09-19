from pydantic import BaseModel, Field
from typing import List, Literal

class EvidenceItem(BaseModel):
    issue: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    evidence: str
    source: str

class ReviewNote(BaseModel):
    rule_id: str
    message: str
    action_required: str

class VerificationResponse(BaseModel):
    system_audit_id: str
    verification_status: Literal["VERIFIED", "NEEDS REVIEW", "INVALID"]
    overall_confidence: float = Field(..., ge=0.0, le=100.0)
    authenticity_score: float = Field(..., ge=0.0, le=100.0)
    project_verification_score: float = Field(..., ge=0.0, le=100.0)
    financial_score: float = Field(..., ge=0.0, le=100.0)
    document_type: str
    hardware_accelerator: str
    extracted_fields: dict
    evidence: List[EvidenceItem]
    review_notes: List[ReviewNote]