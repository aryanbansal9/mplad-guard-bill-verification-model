# 🏛️ MPLADS Guardian: Explainable Bill Verification Engine

**Smart India Hackathon 2026** | **Track:** Financial Fraud Detection & Compliance

MPLADS Guardian is an enterprise-grade, edge-AI powered verification engine designed to audit government procurement bills, tax invoices, and completion certificates. It enforces General Financial Rules (GFR) 2017 and deterministically halts fraudulent payouts through explainable AI.

## 🚀 Core Architecture

* **Edge Vision-Language AI (Qwen2-VL):** Performs localized, strict-schema extraction of bilingual (Hindi/English) invoice data natively on edge GPUs, mitigating the risk of LLM hallucinations.
* **Explainable Decision Engine (XAI):** Generates a deterministic composite score (Authenticity, Project Match, Financial) and itemized, severity-ranked forensic evidence instead of a simple "pass/fail".
* **Statutory Verifiers:** Cross-verifies tax mathematics (Base + CGST/SGST/IGST = Total), authenticates GSTIN formats, and flags missing executive signatures.
* **Database Cross-Verification:** Dynamically matches claimed work titles and budgets against official e-Sakshi government records to prevent budget overruns and ghost project claims.

## 📁 Repository Structure
* `src/api/` - FastAPI routing and system endpoints.
* `src/core/extractor/` - VLM orchestration and hardened extraction prompts.
* `src/core/verifiers/` - GFR statutory compliance and e-Sakshi database linkage.
* `src/core/decision/` - Weighted decision matrix generating explainable evidence.
* `src/schemas/` - Pydantic data contracts for frontend dashboard integration.

## ⚙️ Local Setup & Installation

**1. Initialize the Environment:**
```bash
python -m venv venv
# Windows
source venv/Scripts/activate
# macOS/Linux
# source venv/bin/activate
pip install -r requirements.txt
```

**2. Inject Golden Record (Demo Database Prep):**
```bash
python inject_project.py
```

**3. Boot the FastAPI Server:**
```bash
python -m uvicorn src.main:app --reload
```

## 📡 API Reference
POST /api/verify-bill

Uploads a document image and returns a comprehensive audit response.

Request: multipart/form-data (File: .png, .jpg)

Response Snippet:

``` json
{
  "verification_status": "INVALID",
  "overall_confidence": 76.0,
  "evidence": [
    {
      "issue": "Tax Math Mismatch",
      "severity": "HIGH",
      "evidence": "Base + Taxes does not equal Total Billed.",
      "source": "Bill Arithmetic Audit"
    }
  ],
  "review_notes": [
    {
      "rule_id": "RULE-VETO-REJECT",
      "message": "Critical fraud vectors detected.",
      "action_required": "Mark voucher void in PFMS/e-Sakshi."
    }
  ]
}
```


## 💻 Hardware & Edge Acceleration

This model is engineered for high-performance edge deployment, ensuring sensitive financial documents never leave the local government intranet. 
* **Target Hardware:** NVIDIA RTX 4060 (8GB VRAM) or equivalent.
* **Inference Pipeline:** Executes Qwen2-VL locally via CUDA, achieving ~8.8s extraction times.
* **Cloud Fallback:** Seamlessly routes to Gemini Flash API only if local VRAM is exhausted or hardware acceleration is unavailable.

## ⚖️ Statutory Compliance (GFR 2017)

MPLADS Guardian programmatically enforces key provisions of the **General Financial Rules (GFR) 2017**:
* **Rule 144 (Efficiency & Transparency):** Prevents arbitrary procurement by automatically cross-referencing vendor GSTINs against shell-company formats.
* **Rule 154 & 155 (Petty Purchases & Local Committees):** Audits mathematical integrity (Base + Taxes) to ensure split-billing is not used to bypass the ₹2.5 Lakh GeM/Tender thresholds.
* **PFMS/e-Sakshi Alignment:** Rejects duplicate claims by verifying historical `work_status` in real-time.

## 🔐 Environment Configuration

Create a `.env` file in the root directory to configure database paths and fallback APIs:

```env
# Edge AI / Cloud Fallback
GEMINI_API_KEY=your_google_api_key_here
ENABLE_CLOUD_FALLBACK=True

# Database Configuration
SQLITE_DB_PATH=./mplads_guardian.db
```