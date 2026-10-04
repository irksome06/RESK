"""
Phase 11 Energy Copilot Interactive Demonstration Script.
Demonstrates natural-language energy intelligence grounded in deterministic Python analytics.
Questions:
1. "How is the factory performing?"
2. "Which machine should we investigate first?"
3. "How much could we potentially save?"
4. "Explain why that machine is an opportunity."
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.context_builder import context_builder
from llm.ollama_client import ollama_client
from llm.fallback import generate_deterministic_fallback
from api.copilot import _process_copilot_query


def run_copilot_demo():
    print("=" * 70)
    print("  PERSON 3: ENERGY & PRODUCTION INTELLIGENCE ENGINE — COPILOT DEMO")
    print("=" * 70)
    print(f"Ollama Service Available: {ollama_client.is_available()}")
    print(f"Configured Model:        {ollama_client.model}")
    print("=" * 70)

    demo_questions = [
        ("How is the factory performing?", None),
        ("Which machine should we investigate first?", None),
        ("How much could we potentially save?", None),
        ("Explain why that machine is an opportunity.", "M01"),
    ]

    for idx, (question, m_override) in enumerate(demo_questions, 1):
        print(f"\n[QUERY {idx}]: {question}")
        print("-" * 70)

        response = _process_copilot_query(question=question, machine_id=m_override)

        print(f"• Classified Intent:    {response.intent}")
        print(f"• Engine / Model Used:  {response.model_used}")
        print(f"• Fallback Employed:    {response.fallback_used}")
        print(f"• Grounding Validated:  {response.grounded} (Passed: {response.validation_passed})")
        print(f"• Evidence Summary:     {response.context_summary}")
        print("\n• COPILOT RESPONSE:\n")
        print(response.answer)
        print("=" * 70)


if __name__ == "__main__":
    run_copilot_demo()
