"""
Audit report generator.
Converts raw findings into risk_score, summary, and a structured full report.

Severity levels (3-tier):
  HIGH   — exploitable, significant impact
  MEDIUM — exploitable under specific conditions
  LOW    — minor risk, limited impact
"""
import re
from typing import List, Dict, Any

# Risk label thresholds
RISK_LABELS = [
    (0,   0,  "Safe"),
    (1,  20,  "Low Risk"),
    (21, 50,  "Medium Risk"),
    (51, 75,  "High Risk"),
    (76, 100, "Critical Risk"),
]

# ── Heuristic pre-checks (fast regex rules, no AI needed) ────────────────────

HEURISTIC_RULES = [
    {
        "pattern": r"\btx\.origin\b",
        "type": "tx.origin Authorization",
        "severity": "HIGH",
        "description": (
            "tx.origin is used, likely for authorization. This is unsafe because "
            "a malicious contract in the call chain can impersonate the original "
            "sender. Always use msg.sender for access control."
        ),
    },
    {
        "pattern": r"pragma solidity\s*\^?(0\.[4567])\.",
        "type": "Outdated Solidity Version",
        "severity": "MEDIUM",
        "description": (
            "An outdated Solidity version is used (< 0.8.0). Versions before 0.8 "
            "lack built-in overflow/underflow protection and contain known compiler "
            "bugs. Upgrade to ^0.8.0 or higher."
        ),
    },
    {
        "pattern": r"\bselfdestruct\b",
        "type": "Selfdestruct Present",
        "severity": "MEDIUM",
        "description": (
            "selfdestruct is present. If not protected by strict access control, "
            "an attacker could destroy the contract and lock funds. Verify that "
            "only authorized addresses can trigger it."
        ),
    },
    {
        "pattern": r"\bassembly\b",
        "type": "Inline Assembly",
        "severity": "LOW",
        "description": (
            "Inline assembly is used. Assembly bypasses Solidity safety checks "
            "and is harder to audit. Verify all assembly blocks are necessary "
            "and correct."
        ),
    },
]


def run_heuristic_checks(source_code: str) -> List[Dict]:
    """Fast regex-based pre-scan — runs before AI agents."""
    findings = []
    for rule in HEURISTIC_RULES:
        if re.search(rule["pattern"], source_code):
            findings.append({
                "type":        rule["type"],
                "severity":    rule["severity"],
                "description": rule["description"],
                "location":    "contract-wide (heuristic scan)",
                "function":    "N/A",
                "source":      "heuristic",
            })
    return findings


def generate_report(findings: List[Dict], contract_identifier: str,
                    functions_analyzed: int, source_code: str = "",
                    ai_score: int = None, score_reasoning: str = "",
                    is_proxy: bool = False) -> Dict[str, Any]:
    """
    Generate a complete audit report from findings.

    Returns:
        risk_score   — integer 0-100, stored on-chain
        summary      — short string, stored on-chain
        full_report  — complete JSON object, uploaded to IPFS
    """
    # Use Scorer Agent's score if provided, otherwise fall back to formula
    risk_score  = ai_score if ai_score is not None else _calculate_risk_score(findings)
    risk_label  = _risk_label(risk_score)
    if is_proxy:
        summary = (
            "Upgradeable proxy contract detected. AI analysis was skipped — "
            "proxy infrastructure (delegatecall, fallback) cannot be meaningfully audited in isolation. "
            "Submit the implementation contract address for a real audit."
        )
    else:
        summary = _generate_summary(findings, risk_score, risk_label)

    severities = ["HIGH", "MEDIUM", "LOW"]
    full_report = {
        "contract_identifier": contract_identifier,
        "risk_score":          risk_score,
        "risk_label":          risk_label,
        "summary":             summary,
        "functions_analyzed":  functions_analyzed,
        "total_findings":      len(findings),
        "findings_by_severity": {
            sev: [f for f in findings if f.get("severity", "").upper() == sev]
            for sev in severities
        },
        "findings": findings,
    }

    return {
        "risk_score":  risk_score,
        "risk_label":  risk_label,
        "summary":     summary,
        "full_report": full_report,
    }


# Diminishing returns weight per severity
# Each finding takes this fraction of the remaining score
SEVERITY_WEIGHT = {
    "HIGH":   0.20,   # 1st HIGH: +20, 2nd: +16, 3rd: +13 ...
    "MEDIUM": 0.08,   # 1st MEDIUM: +8, 2nd: +7 ...
    "LOW":    0.03,   # minor, slow accumulation
}


def _calculate_risk_score(findings: List[Dict]) -> int:
    """
    Diminishing returns scoring — naturally approaches 100, never exceeds it.

    Each finding takes a fraction of the remaining headroom:
      score += (100 - score) × weight

    Example:
      1st HIGH  → (100-0)  × 0.30 = 30   → score = 30
      2nd HIGH  → (100-30) × 0.30 = 21   → score = 51
      3rd HIGH  → (100-51) × 0.30 = 14.7 → score = 66
      1st MEDIUM→ (100-66) × 0.15 = 5.1  → score = 71
    """
    if not findings:
        return 0

    # Sort findings: worst severity first for maximum impact
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    sorted_findings = sorted(
        findings,
        key=lambda f: severity_order.get(f.get("severity", "LOW").upper(), 3)
    )

    score = 0.0
    for f in sorted_findings:
        sev    = f.get("severity", "LOW").upper()
        weight = SEVERITY_WEIGHT.get(sev, 0.0)
        if weight == 0:
            continue
        score += (100 - score) * weight

    return min(round(score), 100)


def _risk_label(score: int) -> str:
    for lo, hi, label in RISK_LABELS:
        if lo <= score <= hi:
            return label
    return "Critical Risk"


def _generate_summary(findings: List[Dict], risk_score: int, risk_label: str) -> str:
    if not findings:
        return f"No vulnerabilities found. Risk score: {risk_score}/100. ({risk_label})"

    counts = {}
    for f in findings:
        sev = f.get("severity", "LOW").upper()
        counts[sev] = counts.get(sev, 0) + 1

    parts = [f"{v} {k}" for k, v in counts.items() if v > 0]
    types = list({f.get("type", "Unknown") for f in findings})[:3]

    return (
        f"Risk score: {risk_score}/100 ({risk_label}). "
        f"Found {len(findings)} issue(s) ({', '.join(parts)}). "
        f"Issues include: {', '.join(types)}."
    )
