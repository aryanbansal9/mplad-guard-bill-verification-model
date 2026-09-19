import sqlite3
import os
import re
import logging
from difflib import SequenceMatcher
from src.schemas.response import EvidenceItem

logger = logging.getLogger("RuleEngine")

# Point to the database in the root folder
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "mplads_guardian.db")

class GFRComplianceEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def _get_db_connection(self):
        if not os.path.exists(self.db_path):
            logger.warning(f"Database not found at {self.db_path}.")
            return None
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _clean_number(self, value) -> float:
        if value is None: return 0.0
        cleaned = re.sub(r"[^\d.]", "", str(value))
        try: return float(cleaned)
        except ValueError: return 0.0

    def _fuzzy_similarity(self, a: str, b: str) -> float:
        if not a or not b: return 0.0
        return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

    def analyze_bill(self, extracted_data: dict):
        evidences = []
        auth_score = 100.0
        proj_score = 100.0
        fin_score = 100.0

        # --- 1. Authenticity & Forensics ---
        if not extracted_data.get("has_official_stamp"):
            auth_score -= 30.0
            evidences.append(EvidenceItem(
                issue="Missing Official Seal", 
                severity="HIGH", 
                evidence="No official executing agency stamp detected on document surface.", 
                source="Forensic Vision Model"
            ))
        
        if not extracted_data.get("has_physical_signature") and not extracted_data.get("has_digital_signature"):
            auth_score -= 35.0
            evidences.append(EvidenceItem(
                issue="Missing Signatures", 
                severity="CRITICAL", 
                evidence="Document lacks authorized executive signatures.", 
                source="Forensic Vision Model"
            ))

        gstin = extracted_data.get("vendor_gstin")
        if gstin and str(gstin).lower() != "null":
            if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", str(gstin).upper()):
                auth_score -= 40.0
                evidences.append(EvidenceItem(
                    issue="Invalid GSTIN Format", 
                    severity="CRITICAL", 
                    evidence=f"Extracted GSTIN '{gstin}' is invalid. Potential shell company.", 
                    source="GST Statutory Registry"
                ))

        # --- 2. Financial Math ---
        base = self._clean_number(extracted_data.get("base_amount"))
        cgst = self._clean_number(extracted_data.get("cgst_amount"))
        sgst = self._clean_number(extracted_data.get("sgst_amount"))
        igst = self._clean_number(extracted_data.get("igst_amount"))
        
        # Fallbacks to support both the old and new prompt schemas
        total = self._clean_number(extracted_data.get("total_billed_amount")) or self._clean_number(extracted_data.get("final_amount")) or self._clean_number(extracted_data.get("expenditure"))

        if total > 0:
            calculated_tax = cgst + sgst + igst
            calculated_total = base + calculated_tax
            if abs(total - calculated_total) > 2.0:
                fin_score -= 35.0
                evidences.append(EvidenceItem(
                    issue="Tax Math Mismatch", 
                    severity="HIGH", 
                    evidence=f"Base ({base}) + Taxes ({calculated_tax}) does not equal Total Billed ({total}).", 
                    source="Bill Arithmetic Audit"
                ))

        # --- 3. Project Cross-Verification (e-Sakshi SQLite) ---
        name_of_work = extracted_data.get("work_description") or extracted_data.get("name_of_work", "")
        conn = self._get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                
                # Dynamically determine column names in works_sanctioned
                cursor.execute("PRAGMA table_info(works_sanctioned)")
                table_cols = [row[1].lower() for row in cursor.fetchall()]
                
                # Column name resolution heuristics
                work_col = next((c for c in table_cols if any(k in c for k in ["work", "desc", "project", "title"])), None)
                amount_col = next((c for c in table_cols if any(k in c for k in ["sanction", "amount", "cost", "estimate"])), None)
                status_col = next((c for c in table_cols if "status" in c), None)

                if not work_col:
                    raise ValueError(f"Could not find a project name column in works_sanctioned. Columns found: {table_cols}")

                select_cols = [f'"{work_col}"']
                if amount_col:
                    select_cols.append(f'"{amount_col}"')
                if status_col:
                    select_cols.append(f'"{status_col}"')

                query = f"SELECT {', '.join(select_cols)} FROM works_sanctioned LIMIT 500"
                cursor.execute(query)
                rows = cursor.fetchall()
                
                max_ratio = 0.0
                matched_record = None
                for row in rows:
                    ratio = self._fuzzy_similarity(name_of_work, str(row[work_col]))
                    if ratio > max_ratio:
                        max_ratio = ratio
                        matched_record = row
                
                if max_ratio < 0.65:
                    proj_score -= 60.0
                    evidences.append(EvidenceItem(
                        issue="Unlinked Public Work", 
                        severity="CRITICAL", 
                        evidence=f"Work title does not match e-Sakshi records (Match confidence: {max_ratio:.0%}).", 
                        source="works_sanctioned.csv"
                    ))
                else:
                    if amount_col and matched_record[amount_col]:
                        official_budget = self._clean_number(matched_record[amount_col])
                        if official_budget > 0 and total > official_budget:
                            proj_score -= 50.0
                            overrun = total - official_budget
                            evidences.append(EvidenceItem(
                                issue="Budget Cap Exceeded", 
                                severity="CRITICAL", 
                                evidence=f"Claimed expenditure exceeds official government sanctioned budget by ₹{overrun:,.2f}.", 
                                source="works_sanctioned.csv"
                            ))
                    
                    if status_col and matched_record[status_col] and str(matched_record[status_col]).lower() == "completed":
                        proj_score -= 50.0
                        evidences.append(EvidenceItem(
                            issue="Duplicate Claim / Project Completed", 
                            severity="HIGH", 
                            evidence="Work is already marked as completed and disbursed in e-Sakshi records.", 
                            source="works_completed.csv"
                        ))

            except Exception as e:
                logger.error(f"SQLite DB Query Error: {e}")
                proj_score -= 30.0
                evidences.append(EvidenceItem(
                    issue="Database Audit Failure",
                    severity="HIGH",
                    evidence=f"Failed to query e-Sakshi database: {str(e)}",
                    source="mplads_guardian.db"
                ))
            finally:
                conn.close()

        return max(0.0, auth_score), max(0.0, proj_score), max(0.0, fin_score), evidences

rule_engine = GFRComplianceEngine()