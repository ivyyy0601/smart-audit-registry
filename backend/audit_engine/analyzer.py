"""
Multi-agent vulnerability analyzer for Solidity smart contracts.

Agents:
  Agent 1 — RAG Auditor    : analyzes using ConsenSys knowledge base (FAISS)
  Agent 2 — Logic Auditor  : specializes in access control & business logic
  Agent 3 — LowLevel Auditor: specializes in arithmetic, external calls, low-level patterns
  Agent 4 — Debate Agent   : synthesizes all findings, removes duplicates, adds confidence
  Agent 5 — Validator      : validates findings + scores in one call

Agents 1-3 run in parallel per function.
Debate Agent sees all findings from all agents and synthesizes.
Critic validates each finding from Debate Agent output.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from openai import OpenAI
from .parser import parse_functions, SolidityFunction
from services.rag import get_retriever

# ── Shared checklist ──────────────────────────────────────────────────────────

VULNERABILITY_CHECKLIST = [
    "Reentrancy: external call before state update",
    "Access Control: missing or incorrect modifier (onlyOwner, onlyRole)",
    "Integer Overflow/Underflow: unchecked arithmetic (especially Solidity <0.8)",
    "Unchecked Return Values: low-level call()/send() return not checked",
    "Front-Running: sensitive operations vulnerable to transaction ordering",
    "Flash Loan Attack: price manipulation via flash loans",
    "Selfdestruct: unauthorized selfdestruct call",
    "Delegatecall Injection: untrusted delegatecall target",
    "Timestamp Dependence: block.timestamp used for critical logic",
    "Gas Griefing: unbounded loops or external calls in loops",
    "Signature Replay: missing nonce or chainId in signed messages",
    "tx.origin Authorization: using tx.origin instead of msg.sender",
]

# ── Finding schema (shared across agents) ─────────────────────────────────────

FINDING_SCHEMA = """{
  "vulnerabilities": [
    {
      "type": "vulnerability type",
      "severity": "HIGH | MEDIUM | LOW",
      "description": "clear description ~80 words",
      "location": "function name and line reference"
    }
  ]
}"""

SEVERITY_GUIDE = """Severity guide (use ONLY these three levels, aligned with Code4rena / Immunefi / Trail of Bits standards):

- HIGH   : Direct, immediate loss or theft of user funds — exploitable by ANY attacker with NO special preconditions.
             Examples: reentrancy draining ETH, unprotected selfdestruct/withdraw, integer overflow in <0.8 contract
             allowing theft, anyone can drain the contract.
             NOT HIGH: missing access control on a function that is DESIGNED to be public (e.g. registry submit,
             ERC20 transfer, claim function). Not HIGH if Solidity >=0.8 protects overflow automatically.

- MEDIUM : Fund loss or DoS requires specific conditions (attacker controls parameters, timing window,
             specific contract state, or chaining multiple steps).
             Examples: front-running a large swap, flash loan price manipulation, timestamp dependence in
             time-critical logic, DoS via gas exhaustion, unprotected function that COULD be misused but
             requires specific setup.

- LOW    : Theoretical vulnerability with no clear direct exploit path, or best-practice violation.
             Examples: tx.origin used in a non-critical context, missing events, theoretical reentrancy
             with no real drain path, minor code quality issues."""

# ── Agent 1: RAG Auditor ──────────────────────────────────────────────────────

RAG_AUDITOR_SYSTEM = """You are a smart contract security auditor specializing in
known vulnerability patterns. You have access to the ConsenSys smart contract
security knowledge base and use it to identify real vulnerabilities.
Only report HIGH CONFIDENCE issues backed by the provided knowledge."""

RAG_AUDITOR_PROMPT = """Analyze this Solidity function using the security knowledge below.

=== ConsenSys Security Knowledge Base ===
{rag_context}
=== End Knowledge ===

Function: {func_name}
{code}

Checklist:
{checklist}

{severity_guide}

Output JSON only — use schema:
{schema}"""


def _run_rag_auditor(client: OpenAI, model: str, fn: SolidityFunction,
                     checklist_text: str) -> List[Dict]:
    """Agent 1: RAG-augmented auditor using ConsenSys knowledge base."""
    try:
        rag_context = get_retriever().retrieve(fn.content, k=3)
    except Exception as e:
        print(f"[WARN] RAG retrieval failed for {fn.name}: {e}")
        rag_context = "No additional context available."

    prompt = RAG_AUDITOR_PROMPT.format(
        rag_context=rag_context,
        func_name=fn.name,
        code=fn.content,
        checklist=checklist_text,
        severity_guide=SEVERITY_GUIDE,
        schema=FINDING_SCHEMA,
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": RAG_AUDITOR_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    findings = json.loads(resp.choices[0].message.content).get("vulnerabilities", [])
    for f in findings:
        f["agent"]      = "rag_auditor"
        f["function"]   = fn.name
        f["start_line"] = fn.start_line
        f["end_line"]   = fn.end_line
        f["contract"]   = fn.contract_name
    return findings


# ── Agent 2: Logic Auditor ────────────────────────────────────────────────────

LOGIC_AUDITOR_SYSTEM = """You are a smart contract security auditor specializing in
access control, privilege escalation, and business logic flaws.
Focus on: who can call what, authorization checks, state machine correctness,
role separation, and trust assumptions. Ignore low-level code patterns.

IMPORTANT — avoid false positives:
- Public/external functions that are DESIGNED to be called by anyone are NOT vulnerabilities.
  (e.g. submitAudit in a registry, transfer in ERC20, claimBonus, deposit — these are intentionally open)
- Only flag missing access control as HIGH if ANY caller can directly drain funds or destroy the contract.
- "Anyone can call this" is only a problem if calling it causes direct harm to other users' funds."""

LOGIC_AUDITOR_PROMPT = """Analyze this Solidity function for access control and logic vulnerabilities.

Function: {func_name}
{code}

Focus areas:
- Missing or incorrect access control on PRIVILEGED operations (admin withdraw, mint, pause, upgrade)
- Privilege escalation: can unprivileged users reach privileged state?
- Business logic: are state transitions correct and ordered?
- Trust assumptions: does the function trust untrusted inputs in a harmful way?
- Initialization: can critical ADMIN functions be called before setup?

Do NOT flag:
- Public functions that are DESIGNED to be open (submit, register, claim, deposit, transfer, view functions)
- Missing onlyOwner on non-critical public utility functions

{severity_guide}

Output JSON only — use schema:
{schema}"""


def _run_logic_auditor(client: OpenAI, model: str, fn: SolidityFunction) -> List[Dict]:
    """Agent 2: Logic and access control specialist."""
    prompt = LOGIC_AUDITOR_PROMPT.format(
        func_name=fn.name,
        code=fn.content,
        severity_guide=SEVERITY_GUIDE,
        schema=FINDING_SCHEMA,
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": LOGIC_AUDITOR_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    findings = json.loads(resp.choices[0].message.content).get("vulnerabilities", [])
    for f in findings:
        f["agent"]      = "logic_auditor"
        f["function"]   = fn.name
        f["start_line"] = fn.start_line
        f["end_line"]   = fn.end_line
        f["contract"]   = fn.contract_name
    return findings


# ── Agent 3: LowLevel Auditor ─────────────────────────────────────────────────

LOWLEVEL_AUDITOR_SYSTEM = """You are a smart contract security auditor specializing in
low-level code patterns and arithmetic issues.
Focus on: integer overflow/underflow, unchecked return values from call()/send(),
reentrancy (call before state update), timestamp dependence, inline assembly risks,
gas griefing, and unsafe delegatecall. Ignore access control and business logic."""

LOWLEVEL_AUDITOR_PROMPT = """Analyze this Solidity function for low-level and arithmetic vulnerabilities.

Function: {func_name}
{code}

Focus areas:
- Integer overflow/underflow (critical in Solidity <0.8.0 without SafeMath)
- Reentrancy: external call() before state variable update
- Unchecked return value from send(), call(), delegatecall()
- block.timestamp used for randomness or exact timing
- Inline assembly bypassing safety checks
- Unbounded loops causing gas exhaustion
- tx.origin used for authorization

{severity_guide}

Output JSON only — use schema:
{schema}"""


def _run_lowlevel_auditor(client: OpenAI, model: str, fn: SolidityFunction) -> List[Dict]:
    """Agent 3: Low-level code and arithmetic specialist."""
    prompt = LOWLEVEL_AUDITOR_PROMPT.format(
        func_name=fn.name,
        code=fn.content,
        severity_guide=SEVERITY_GUIDE,
        schema=FINDING_SCHEMA,
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": LOWLEVEL_AUDITOR_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    findings = json.loads(resp.choices[0].message.content).get("vulnerabilities", [])
    for f in findings:
        f["agent"]      = "lowlevel_auditor"
        f["function"]   = fn.name
        f["start_line"] = fn.start_line
        f["end_line"]   = fn.end_line
        f["contract"]   = fn.contract_name
    return findings


# ── Agent 4: Debate Agent ─────────────────────────────────────────────────────

DEBATE_AGENT_SYSTEM = """You are a senior smart contract security lead.
Three specialized auditors have each analyzed the same contract independently.
Your job is to synthesize their findings into a clean, final list:
- Remove duplicate findings (same vulnerability, different descriptions — keep the best one)
- Boost confidence for findings reported by multiple auditors
- Add any clear findings that all three missed
- Remove obvious false positives (see below)
- Do NOT change severity unless you have a strong reason
Output a clean, deduplicated finding list.

FALSE POSITIVES to remove:
- "Missing access control" on functions that are DESIGNED to be public (submit, register, claim, deposit, transfer)
- Overflow/underflow in Solidity ^0.8.x (built-in protection)
- Reentrancy in functions that have nonReentrant modifier
- Standard OpenZeppelin library code (ERC20, Ownable, ReentrancyGuard internals)
- Standard proxy pattern delegatecall in fallback/receive
- "tx.origin" if it's only used for informational logging, not for access control decisions"""

DEBATE_AGENT_PROMPT = """Three auditors analyzed this contract independently. Synthesize their findings.

Contract source (for reference):
{source_code}

=== RAG Auditor findings (knowledge-base driven) ===
{rag_findings}

=== Logic Auditor findings (access control specialist) ===
{logic_findings}

=== LowLevel Auditor findings (arithmetic & calls specialist) ===
{lowlevel_findings}

Instructions:
1. Deduplicate: if multiple auditors found the same issue, merge into one finding
2. Confidence: add "confirmed_by" field — how many auditors independently found this issue (1, 2, or 3)
3. Fill gaps: if you see a clear vulnerability none of them caught, add it
4. Filter: remove clear false positives (standard OZ patterns, 0.8+ overflow protection, proxy delegatecall)

Output JSON only:
{{
  "findings": [
    {{
      "type": "vulnerability type",
      "severity": "HIGH | MEDIUM | LOW",
      "description": "best description from the auditors, ~100 words",
      "location": "function name and line reference",
      "function": "exact function name as it appears in the code (e.g. safeTransferETH, mint, withdraw)",
      "confirmed_by": 1 or 2 or 3
    }}
  ]
}}"""


def _run_debate_agent(client: OpenAI, model: str,
                      source_code: str,
                      rag_findings: List[Dict],
                      logic_findings: List[Dict],
                      lowlevel_findings: List[Dict]) -> List[Dict]:
    """Agent 4: synthesizes all auditor findings — deduplicates, adds confidence."""

    def fmt(findings: List[Dict]) -> str:
        if not findings:
            return "No findings."
        lines = []
        for f in findings:
            lines.append(
                f"- [{f.get('severity','?')}] {f.get('type','?')} "
                f"in {f.get('function','?')}: {f.get('description','')[:120]}"
            )
        return "\n".join(lines)

    prompt = DEBATE_AGENT_PROMPT.format(
        source_code=source_code[:4000],
        rag_findings=fmt(rag_findings),
        logic_findings=fmt(logic_findings),
        lowlevel_findings=fmt(lowlevel_findings),
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": DEBATE_AGENT_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    findings = json.loads(resp.choices[0].message.content).get("findings", [])
    print(f"[Debate Agent] Synthesized → {len(findings)} findings "
          f"(from {len(rag_findings)} RAG + {len(logic_findings)} Logic "
          f"+ {len(lowlevel_findings)} LowLevel)")
    return findings


# ── Agent 5: Validator (Critic + Scorer combined) ────────────────────────────

VALIDATOR_SYSTEM = """You are a senior smart contract security expert.
Review a list of potential vulnerabilities and:
1. Confirm or reject each finding (real vulnerability or false positive?)
2. Assign an overall risk score based on confirmed findings and contract context.

── VALIDATION RULES ──

REENTRANCY:
  CONFIRM if: external call() is BEFORE state update, AND no nonReentrant modifier.
  REJECT if: state updated BEFORE call (CEI pattern), OR nonReentrant modifier present.
  NOTE: require(success) does NOT prevent reentrancy.

UNCHECKED RETURN VALUE:
  CONFIRM if: send()/call() result not checked with require(success).
  REJECT if: require(success, ...) or if (!success) revert is present after the call.

INTEGER OVERFLOW:
  CONFIRM if: Solidity pragma <0.8.0 AND arithmetic without SafeMath.
  REJECT if: Solidity ^0.8.x (built-in overflow protection).

MISSING ACCESS CONTROL:
  CONFIRM if: mint/drain/selfdestruct function has NO onlyOwner/onlyRole modifier.
  REJECT if: function is intentionally public (deposit, submit, register, transfer, view).

TIMESTAMP:
  CONFIRM if: block.timestamp used for randomness or exact parity check (% 2).
  REJECT if: only used for cooldown of many hours or days.

ALWAYS REJECT:
  ^0.8.x overflow, nonReentrant+reentrancy, OZ library internals, proxy fallback, cosmetic issues.

── SCORING RULES ──
  - Formula baseline is pre-calculated from finding count/severity.
  - You may increase UP TO +20 if contract holds user funds and vulnerabilities can drain them.
  - Never go below the baseline — confirmed findings always mean score > 0.
  - No findings → score = 0."""

VALIDATOR_PROMPT = """Review these {count} findings and output validated results + risk score.

Contract source (for context):
{source_code}

Formula baseline score: {baseline} | Allowed range: {min_score} to {max_score}

Findings to review:
{findings_list}

Output JSON only:
{{
  "reviews": [
    {{"index": 0, "confirmed": true, "reasoning": "external call before state update, no nonReentrant"}},
    {{"index": 1, "confirmed": false, "reasoning": "require(success) present, return value is checked"}}
  ],
  "risk_score": <integer between {min_score} and {max_score}>,
  "score_reasoning": "2 sentences explaining the score"
}}"""


def _run_validator(client: OpenAI, model: str,
                   findings: List[Dict], fn_map: Dict,
                   functions: list, source_code: str,
                   baseline: int) -> Dict:
    """Agent 5: validates all findings and scores the contract in one call."""
    if not findings:
        return {"validated": [], "risk_score": 0, "score_reasoning": "No findings."}

    min_score = baseline
    max_score = min(100, baseline + 20)

    lines = []
    for i, f in enumerate(findings):
        fn = _find_function(fn_map, f, functions[0])
        lines.append(
            f"[{i}] [{f.get('severity','?')}] {f.get('type','?')} "
            f"in {f.get('location','?')} (confirmed by {f.get('confirmed_by',1)} agents)\n"
            f"    Description: {f.get('description','')[:120]}\n"
            f"    Function code: {fn.content[:400]}"
        )

    prompt = VALIDATOR_PROMPT.format(
        count=len(findings),
        source_code=source_code[:2000],
        baseline=baseline,
        min_score=min_score,
        max_score=max_score,
        findings_list="\n\n".join(lines),
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": VALIDATOR_SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    result  = json.loads(resp.choices[0].message.content)
    reviews = result.get("reviews", [])
    score   = max(min_score, min(max_score, int(result.get("risk_score", baseline))))
    reason  = result.get("score_reasoning", "")

    validated = []
    for rev in reviews:
        idx       = rev.get("index", -1)
        confirmed = rev.get("confirmed", True)
        reasoning = rev.get("reasoning", "")
        status    = "✅" if confirmed else "❌"
        if 0 <= idx < len(findings):
            f = findings[idx]
            print(f"[Validator] {status} [{f.get('severity')}] {f.get('type')} — {reasoning[:80]}")
            if confirmed:
                clean = {k: v for k, v in f.items() if k not in ("confirmed", "agent")}
                validated.append(clean)

    print(f"[Validator] {len(validated)}/{len(findings)} confirmed | "
          f"score: {baseline} → {score} — {reason[:80]}")
    return {"validated": validated, "risk_score": score, "score_reasoning": reason}


def _find_function(fn_map: Dict[str, Any], finding: Dict, fallback) -> Any:
    """Find the correct SolidityFunction for a finding from the Debate Agent.
    fn_map keys are 'ContractName.functionName', finding['function'] is just 'functionName'.
    """
    func_name = finding.get("function", "")
    if not func_name:
        return fallback
    # exact match first (e.g. "SafeToken.safeTransferETH")
    if func_name in fn_map:
        return fn_map[func_name]
    # partial match: find any key ending with .functionName
    for key, fn in fn_map.items():
        if key.endswith("." + func_name):
            return fn
    return fallback


# ── Proxy Detection ──────────────────────────────────────────────────────────

PROXY_PATTERNS = [
    r"\bdelegatecall\b",                          # delegatecall in fallback
    r"_fallback\(\)",                             # OZ proxy _fallback
    r"_delegate\(",                               # OZ proxy _delegate
    r"_implementation\(\)",                       # implementation slot getter
    r"AdminUpgradeabilityProxy",                  # OpenZeppelin transparent proxy
    r"TransparentUpgradeableProxy",
    r"UUPSUpgradeable",
    r"EIP1967",
    r"0x360894a13ba1a3210667c828492db98dca3e2076",  # EIP-1967 implementation slot
    r"StorageSlot",                               # OZ storage slot pattern
]

import re as _re

def detect_proxy(source_code: str) -> bool:
    """Returns True if source code looks like an upgradeable proxy contract."""
    for pattern in PROXY_PATTERNS:
        if _re.search(pattern, source_code):
            return True
    return False


# ── Main AuditEngine ──────────────────────────────────────────────────────────

class AuditEngine:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini",
                 max_workers: int = 6):
        self.client      = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model       = model
        self.max_workers = max_workers

    def analyze(self, source_code: str) -> Dict[str, Any]:
        """
        5-agent multi-agent analysis:
          Agent 1 (RAG Auditor)     — knowledge-base driven, parallel per function
          Agent 2 (Logic Auditor)   — access control specialist, parallel per function
          Agent 3 (LowLevel Auditor)— arithmetic & calls specialist, parallel per function
          Agent 4 (Debate Agent)    — synthesizes all findings, deduplicates, adds confidence
          Agent 5 (Critic)          — final validation per finding, parallel
        """
        # Early exit: proxy contracts cannot be meaningfully audited —
        # their code is all infrastructure (delegatecall, fallback, Address.sol).
        # The real logic lives in the implementation contract.
        if detect_proxy(source_code):
            print("[Proxy] Proxy contract detected — skipping AI analysis")
            return {
                "findings":           [],
                "functions_analyzed": 0,
                "risk_score":         0,
                "score_reasoning":    "Proxy contract detected. No AI analysis performed.",
                "is_proxy":           True,
            }

        functions = parse_functions(source_code)
        if not functions:
            return {"findings": [], "functions_analyzed": 0, "error": "No functions found"}

        checklist_text = "\n".join(f"- {item}" for item in VULNERABILITY_CHECKLIST)
        fn_map         = {fn.name: fn for fn in functions}

        rag_findings:      List[Dict] = []
        logic_findings:    List[Dict] = []
        lowlevel_findings: List[Dict] = []

        # ── Agents 1, 2, 3: parallel across all functions ─────────────────────
        print(f"[Agents 1-3] Analyzing {len(functions)} functions in parallel "
              f"(RAG + Logic + LowLevel)...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            rag_futures = {
                executor.submit(_run_rag_auditor,
                                self.client, self.model, fn, checklist_text): fn
                for fn in functions
            }
            logic_futures = {
                executor.submit(_run_logic_auditor,
                                self.client, self.model, fn): fn
                for fn in functions
            }
            lowlevel_futures = {
                executor.submit(_run_lowlevel_auditor,
                                self.client, self.model, fn): fn
                for fn in functions
            }

            for future in as_completed(rag_futures):
                fn = rag_futures[future]
                try:
                    rag_findings.extend(future.result())
                except Exception as e:
                    print(f"[WARN] RAG Auditor error on {fn.name}: {e}")

            for future in as_completed(logic_futures):
                fn = logic_futures[future]
                try:
                    logic_findings.extend(future.result())
                except Exception as e:
                    print(f"[WARN] Logic Auditor error on {fn.name}: {e}")

            for future in as_completed(lowlevel_futures):
                fn = lowlevel_futures[future]
                try:
                    lowlevel_findings.extend(future.result())
                except Exception as e:
                    print(f"[WARN] LowLevel Auditor error on {fn.name}: {e}")

        print(f"[Agents 1-3] Done — RAG:{len(rag_findings)} "
              f"Logic:{len(logic_findings)} LowLevel:{len(lowlevel_findings)}")

        # ── Agent 4: Debate Agent ─────────────────────────────────────────────
        print("[Agent 4 / Debate] Synthesizing all findings...")
        try:
            debate_findings = _run_debate_agent(
                self.client, self.model, source_code,
                rag_findings, logic_findings, lowlevel_findings,
            )
        except Exception as e:
            print(f"[WARN] Debate Agent failed: {e}")
            # fallback: merge all raw findings
            debate_findings = rag_findings + logic_findings + lowlevel_findings

        if not debate_findings:
            return {"findings": [], "functions_analyzed": len(functions)}

        # ── Agent 5: Validator (Critic + Scorer combined) ────────────────────
        print(f"[Agent 5 / Validator] Validating {len(debate_findings)} findings + scoring...")
        from audit_engine.report import _calculate_risk_score
        baseline = _calculate_risk_score(debate_findings)
        try:
            val_result = _run_validator(
                self.client, self.model,
                debate_findings, fn_map, functions,
                source_code=source_code,
                baseline=baseline,
            )
        except Exception as e:
            print(f"[WARN] Validator failed: {e}")
            val_result = {"validated": debate_findings, "risk_score": baseline, "score_reasoning": ""}

        validated   = val_result["validated"]
        score_result = {"risk_score": val_result["risk_score"], "reasoning": val_result["score_reasoning"]}
        rejected = len(debate_findings) - len(validated)
        print(f"[Validator] Done — {len(validated)} confirmed, {rejected} rejected")

        is_proxy = detect_proxy(source_code)
        if is_proxy:
            print("[Proxy] Detected proxy contract — findings may contain false positives")

        return {
            "findings":           validated,
            "functions_analyzed": len(functions),
            "risk_score":         score_result["risk_score"],
            "score_reasoning":    score_result["reasoning"],
            "is_proxy":           is_proxy,
        }
