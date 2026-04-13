"""
LLM-based vulnerability analyzer.
Core logic inspired by finite-monkey-engine:
  for each parsed function, send a checklist-based prompt to the LLM
  and receive structured JSON findings.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from openai import OpenAI
from .parser import parse_functions, SolidityFunction

# Vulnerability checklist (condensed from finite-monkey-engine knowledge base)
VULNERABILITY_CHECKLIST = [
    "Reentrancy: external call before state update",
    "Access Control: missing or incorrect modifier (onlyOwner, onlyRole)",
    "Integer Overflow/Underflow: unchecked arithmetic operations",
    "Unchecked Return Values: low-level call() return not checked",
    "Front-Running: sensitive operations vulnerable to transaction ordering",
    "Flash Loan Attack: price manipulation via flash loans",
    "Selfdestruct: unauthorized selfdestruct call",
    "Delegatecall Injection: untrusted delegatecall target",
    "Timestamp Dependence: block.timestamp used for critical logic",
    "Uninitialized Storage Pointer: uninitialized local storage variable",
    "Gas Griefing: unbounded loops or external calls in loops",
    "Signature Replay: missing nonce or chainId in signed messages",
]

AUDIT_PROMPT_TEMPLATE = """
# Role
You are a senior smart contract security auditor.

# Task
Analyze the following Solidity function for security vulnerabilities.
Use the checklist below as a reference. Be neutral — vulnerabilities may or may not exist.

# Vulnerability Checklist
{checklist}

# Hard Requirements
- Only report HIGH CONFIDENCE vulnerabilities that would cause real harm.
- Do NOT report style issues, gas optimizations, or best-practice suggestions.
- Evidence MUST come from the provided code.
- Output MUST be a single JSON object. Output JSON only, no markdown.
- "vulnerabilities" may be an empty array [] if no issues found.

# Output JSON Schema
{{
  "vulnerabilities": [
    {{
      "type": "vulnerability type name",
      "severity": "HIGH | MEDIUM | LOW",
      "description": "clear description of the issue, ~100 words",
      "location": "function name and line reference"
    }}
  ]
}}

# Function to Analyze
Function: {func_name}
{code}
""".strip()


class AuditEngine:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini", max_workers: int = 5):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.max_workers = max_workers

    def analyze(self, source_code: str) -> Dict[str, Any]:
        """
        Analyze a Solidity source string.
        Returns a dict with 'findings' list and 'functions_analyzed' count.
        """
        functions = parse_functions(source_code)
        if not functions:
            return {"findings": [], "functions_analyzed": 0, "error": "No functions found"}

        all_findings = []
        checklist_text = "\n".join(f"- {item}" for item in VULNERABILITY_CHECKLIST)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._analyze_function, fn, checklist_text): fn
                for fn in functions
            }
            for future in as_completed(futures):
                fn = futures[future]
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                except Exception as e:
                    print(f"[WARN] Error analyzing {fn.name}: {e}")

        return {
            "findings": all_findings,
            "functions_analyzed": len(functions),
        }

    def _analyze_function(self, fn: SolidityFunction, checklist_text: str) -> List[Dict]:
        prompt = AUDIT_PROMPT_TEMPLATE.format(
            checklist=checklist_text,
            func_name=fn.name,
            code=fn.content,
        )
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        findings = parsed.get("vulnerabilities", [])

        # Attach source location info to each finding
        for f in findings:
            f["function"] = fn.name
            f["start_line"] = fn.start_line
            f["end_line"] = fn.end_line
            f["contract"] = fn.contract_name

        return findings
