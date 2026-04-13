"""
Audit report generator.
Converts raw findings into risk_score, summary, and a structured full report.
"""
from typing import List, Dict, Any

SEVERITY_WEIGHT = {"HIGH": 30, "MEDIUM": 15, "LOW": 5}


def generate_report(findings: List[Dict], contract_identifier: str, functions_analyzed: int) -> Dict[str, Any]:
    """
    Generate a complete audit report from findings.

    Returns:
        risk_score   — integer 0-100, stored on-chain
        summary      — short string, stored on-chain
        full_report  — complete JSON object, uploaded to IPFS
    """
    risk_score = _calculate_risk_score(findings)
    summary = _generate_summary(findings, risk_score)

    full_report = {
        "contract_identifier": contract_identifier,
        "risk_score": risk_score,
        "summary": summary,
        "functions_analyzed": functions_analyzed,
        "total_findings": len(findings),
        "findings_by_severity": {
            "HIGH":   [f for f in findings if f.get("severity") == "HIGH"],
            "MEDIUM": [f for f in findings if f.get("severity") == "MEDIUM"],
            "LOW":    [f for f in findings if f.get("severity") == "LOW"],
        },
        "findings": findings,
    }

    return {
        "risk_score": risk_score,
        "summary": summary,
        "full_report": full_report,
    }


def _calculate_risk_score(findings: List[Dict]) -> int:
    if not findings:
        return 0
    score = sum(SEVERITY_WEIGHT.get(f.get("severity", "LOW").upper(), 5) for f in findings)
    return min(score, 100)


def _generate_summary(findings: List[Dict], risk_score: int) -> str:
    if not findings:
        return f"No vulnerabilities found. Risk score: {risk_score}/100."

    high   = sum(1 for f in findings if f.get("severity") == "HIGH")
    medium = sum(1 for f in findings if f.get("severity") == "MEDIUM")
    low    = sum(1 for f in findings if f.get("severity") == "LOW")

    types = list({f.get("type", "Unknown") for f in findings})[:3]
    types_str = ", ".join(types)

    parts = []
    if high:   parts.append(f"{high} HIGH")
    if medium: parts.append(f"{medium} MEDIUM")
    if low:    parts.append(f"{low} LOW")

    return (
        f"Risk score: {risk_score}/100. "
        f"Found {len(findings)} vulnerabilities ({', '.join(parts)}). "
        f"Issues include: {types_str}."
    )
