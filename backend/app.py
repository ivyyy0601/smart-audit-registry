"""
FastAPI backend service.

Endpoints:
  POST /audit/address  — fetch source from Etherscan by contract address and run audit
  POST /audit/upload   — upload a .sol file and run audit
  GET  /audit/{id}     — query the latest on-chain audit record
  GET  /verify         — verify a report hash against on-chain records
  GET  /health         — health check
"""
import json, os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from audit_engine import AuditEngine
from audit_engine.report import generate_report
from services.etherscan import fetch_source_code
from services.ipfs import upload_report
from blockchain.registry import AuditRegistryClient

app = FastAPI(title="Smart Audit Registry API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
    expose_headers=["*"],
)

engine = AuditEngine()


# ── Request / Response models ─────────────────────────────────────────────────

class AuditByAddressRequest(BaseModel):
    contract_address: str

class AuditResponse(BaseModel):
    contract_identifier: str
    risk_score: int
    summary: str
    report_hash: str
    tx_hash: str
    findings_count: int
    findings: list


# ── Core pipeline ─────────────────────────────────────────────────────────────

def _run_audit_pipeline(source_code: str, identifier: str) -> AuditResponse:
    """Analyze → generate report → upload to IPFS → submit on-chain."""

    # 1. Run AI analysis
    result = engine.analyze(source_code)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    # 2. Generate risk score, summary, and full report
    report_data = generate_report(
        findings=result["findings"],
        contract_identifier=identifier,
        functions_analyzed=result["functions_analyzed"],
    )

    # 3. Upload full report to IPFS
    try:
        report_hash = upload_report(report_data["full_report"], name=f"audit-{identifier[:10]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IPFS upload failed: {e}")

    # 4. Submit audit record on-chain
    try:
        client = AuditRegistryClient()
        tx_hash = client.submit_audit(
            contract_identifier=identifier,
            risk_score=report_data["risk_score"],
            summary=report_data["summary"],
            report_hash=report_hash,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blockchain submission failed: {e}")

    # Save full report locally for retrieval
    os.makedirs("reports", exist_ok=True)
    safe_hash = report_hash.replace(":", "_").replace("/", "_")
    with open(f"reports/{safe_hash}.json", "w") as f:
        json.dump(report_data["full_report"], f, indent=2)

    return AuditResponse(
        contract_identifier=identifier,
        risk_score=report_data["risk_score"],
        summary=report_data["summary"],
        report_hash=report_hash,
        tx_hash=tx_hash,
        findings_count=len(result["findings"]),
        findings=result["findings"],
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/audit/address", response_model=AuditResponse)
async def audit_by_address(req: AuditByAddressRequest):
    """Fetch source code from Etherscan and run audit."""
    try:
        source_code = fetch_source_code(req.contract_address)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _run_audit_pipeline(source_code, req.contract_address)


@app.post("/audit/upload", response_model=AuditResponse)
async def audit_by_upload(file: UploadFile = File(...)):
    """Upload a .sol file and run audit."""
    if not file.filename.endswith(".sol"):
        raise HTTPException(status_code=400, detail="Only .sol files are supported")
    source_code = (await file.read()).decode("utf-8")
    return _run_audit_pipeline(source_code, file.filename)


@app.get("/audit/{contract_identifier}")
async def get_audit(contract_identifier: str):
    """Query all on-chain audit records for a given identifier."""
    try:
        client = AuditRegistryClient()
        count = client.get_audit_count(contract_identifier)
        if count == 0:
            raise HTTPException(status_code=404, detail="No audit record found")
        records = []
        for i in range(count):
            records.append(client.get_audit_at(contract_identifier, i))
        return {
            "contract_identifier": contract_identifier,
            "total": count,
            "records": records,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/verify")
async def verify_report(contract_identifier: str, report_hash: str = ""):
    """Verify whether a report hash matches the on-chain record."""
    try:
        client = AuditRegistryClient()
        return client.verify_report(contract_identifier, report_hash)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/report/{report_hash}")
async def get_report(report_hash: str):
    """Retrieve full audit report — local cache only (reports are saved during audit pipeline)."""
    safe_hash = report_hash.replace(":", "_").replace("/", "_")
    path = f"reports/{safe_hash}.json"
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="Report not cached locally. Re-submit this contract to generate a fresh report."
        )
    with open(path) as f:
        return json.load(f)


@app.get("/health")
async def health():
    return {"status": "ok"}
