"""
Phase 11 Hallucination Defense & Post-Generation Grounding Validator.
Validates LLM-generated output against strict industrial intelligence rules:
1. Flags unsupported numerical figures not present in authoritative context.
2. Rejects machine-failure diagnosis/claims (Person 2 boundary).
3. Rejects direct machine-control commands (Person 1 boundary).
4. Rejects certainty about unverified causal claims.
"""

import re
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger("llm.validation")

# Prohibited failure prediction terms (Person 2 boundary)
FORBIDDEN_FAILURE_PATTERNS = [
    r"\bwill\s+fail\b",
    r"\bmotor\s+will\s+fail\b",
    r"\bbearing\s+failure\b",
    r"\bfailure\s+probability\b",
    r"\bfail\s+in\s+\d+\s+days\b",
    r"\bcatastrophic\s+failure\b",
    r"\bmachine\s+breakdown\s+imminent\b",
]

# Prohibited direct machine control commands (Person 1 boundary)
FORBIDDEN_CONTROL_PATTERNS = [
    r"\bshut\s+down\s+the\s+machine\b",
    r"\bturn\s+off\s+power\b",
    r"\bkill\s+the\s+motor\b",
    r"\bstop\s+the\s+machine\s+immediately\b",
    r"\bset\s+motor\s+speed\s+to\b",
    r"\bexecute\s+plc\s+command\b",
    r"\bactuate\s+sleep\s+mode\s+now\b",
]

# Prohibited claims of certainty about causation
FORBIDDEN_CAUSAL_PATTERNS = [
    r"\bis\s+definitely\s+caused\s+by\b",
    r"\bthe\s+root\s+cause\s+is\b",
    r"\bconclusively\s+proves\s+that\b",
    r"\bis\s+guaranteed\s+to\s+cause\b",
]


def extract_numbers_from_text(text: str) -> List[float]:
    """
    Extracts numerical candidate values from text, ignoring section numbers and basic formatting.
    """
    # Match numbers like 100, 100.24, -5.5
    matches = re.findall(r"(?<![a-zA-Z_])[-+]?\d*\.?\d+(?![a-zA-Z_])", text)
    numbers = []
    for m in matches:
        try:
            val = float(m)
            # Filter trivial 0, 1, 2 integers often used in markdown lists
            if val.is_integer() and 1 <= val <= 4:
                continue
            numbers.append(val)
        except ValueError:
            continue
    return numbers


def validate_copilot_response(
    response_text: str,
    grounded_facts: List[Dict[str, Any]],
    context_text: str,
) -> Dict[str, Any]:
    """
    Validates generated response against grounding constraints.
    Returns:
        Dict with:
            - is_valid: bool
            - violations: List[str]
            - unsupported_numbers: List[float]
    """
    violations: List[str] = []
    resp_lower = response_text.lower()

    # 1. Check for Forbidden Machine Failure Claims (Person 2 boundary)
    for pat in FORBIDDEN_FAILURE_PATTERNS:
        if re.search(pat, resp_lower):
            violations.append(f"Forbidden failure prediction pattern detected: '{pat}'")

    # 2. Check for Forbidden Machine Control Commands (Person 1 boundary)
    for pat in FORBIDDEN_CONTROL_PATTERNS:
        if re.search(pat, resp_lower):
            violations.append(f"Forbidden machine control command detected: '{pat}'")

    # 3. Check for Forbidden Causation Claims
    for pat in FORBIDDEN_CAUSAL_PATTERNS:
        if re.search(pat, resp_lower):
            violations.append(f"Unsupported certainty about causation detected: '{pat}'")

    # 4. Numeric Grounding Verification
    # Collect known authoritative numbers from grounded_facts and context_text
    known_numbers: Set[float] = set()
    for f in grounded_facts:
        val = f.get("value")
        if isinstance(val, (int, float)):
            known_numbers.add(round(float(val), 2))
            known_numbers.add(round(float(val), 4))

    for m in extract_numbers_from_text(context_text):
        known_numbers.add(round(m, 2))

    # Also allow standard constants: 100 (for percentages), 60 (minutes/seconds), 24 (hours), 30 (days), 365 (days)
    known_numbers.update([100.0, 60.0, 24.0, 30.0, 365.0, 12.0, 5.0, 10.0, 1.0, 2.0])

    response_numbers = extract_numbers_from_text(response_text)
    unsupported_numbers = []

    for num in response_numbers:
        rounded_2 = round(num, 2)
        # Check if number matches any known value within a tolerance of 0.05
        matched = any(abs(rounded_2 - k) < 0.05 or abs(num - k) / (abs(k) + 1e-6) < 0.02 for k in known_numbers)
        if not matched and abs(num) >= 0.01:
            unsupported_numbers.append(num)

    # Flag unsupported numbers if significant
    if len(unsupported_numbers) > 2:
        violations.append(f"Unsupported numerical values detected: {unsupported_numbers}")

    is_valid = len(violations) == 0

    return {
        "is_valid": is_valid,
        "violations": violations,
        "unsupported_numbers": unsupported_numbers,
    }
