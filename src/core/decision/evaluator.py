from typing import List
from src.schemas.response import EvidenceItem, ReviewNote, VerificationResponse

class ExplainableDecisionEngine:
    W_AUTH = 0.35
    W_PROJ = 0.40
    W_FIN = 0.25

    def evaluate(
        self,
        audit_id: str,
        auth_score: float,
        proj_score: float,
        fin_score: float,
        evidences: List[EvidenceItem],
        extracted_data: dict,
        hardware: str
    ) -> VerificationResponse:
        
        # Calculate Weighted Composite Confidence
        overall_score = (
            (self.W_AUTH * auth_score) +
            (self.W_PROJ * proj_score) +
            (self.W_FIN * fin_score)
        )

        review_notes = []
        has_critical = any(e.severity == "CRITICAL" for e in evidences)
        high_count = sum(1 for e in evidences if e.severity == "HIGH")

        # Absolute Veto Logic
        if has_critical or overall_score < 50.0:
            status = "INVALID"
            review_notes.append(ReviewNote(
                rule_id="RULE-VETO-REJECT",
                message="Critical fraud vectors or statutory violations detected. Immediate bill rejection.",
                action_required="Mark voucher void in PFMS/e-Sakshi; notify District Nodal Officer."
            ))
        elif high_count >= 2 or (50.0 <= overall_score < 85.0):
            status = "NEEDS REVIEW"
            review_notes.append(ReviewNote(
                rule_id="RULE-MANUAL-AUDIT",
                message="Discrepancies found requiring auditor sign-off.",
                action_required="Dispatch physical file to Chief Development Officer (CDO)."
            ))
        else:
            status = "VERIFIED"
            review_notes.append(ReviewNote(
                rule_id="RULE-AUTO-PASS",
                message="Bill passes visual forensics, project alignment, and statutory mathematical integrity.",
                action_required="Authorize stage-work payment voucher."
            ))

        return VerificationResponse(
            system_audit_id=audit_id,
            verification_status=status,
            overall_confidence=round(overall_score, 2),
            authenticity_score=round(auth_score, 2),
            project_verification_score=round(proj_score, 2),
            financial_score=round(fin_score, 2),
            document_type=extracted_data.get("document_type", "Unknown"),
            hardware_accelerator=hardware,
            extracted_fields=extracted_data,
            evidence=evidences,
            review_notes=review_notes
        )

decision_engine = ExplainableDecisionEngine()