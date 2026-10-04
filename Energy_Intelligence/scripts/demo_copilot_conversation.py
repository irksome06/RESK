"""
Demonstration Script for Conversational Energy Intelligence Copilot.
Person 3: Energy & Production Intelligence Engine
Schneider Electric 2026 Smart Manufacturing Hackathon

Demonstrates a multi-turn, stateful, natural-language conversation:
1. "What can you do?" -> Natural conversational explanation of capabilities
2. "What is the factory energy consumption?" -> Grounded numerical answer from authoritative Python analytics
3. "How does that compare with baseline?" -> Grounded baseline deviation analysis
4. "Can we calculate SEC?" -> Transparent explanation of production requirements & SEC status
5. "Which machine should I investigate?" -> Prioritized energy opportunities without claiming machine control
6. "What about M01?" -> Machine-specific deep-dive telemetry analysis

Demonstrates Person 1 / Person 2 / Person 3 responsibility boundaries and strict numerical grounding.
"""

import sys
from pathlib import Path

# Add project root to PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from api.main import app
from scripts.run_final_demo import run_authoritative_demo


def run_copilot_demo_conversation():
    print("\n" + "=" * 65)
    print("  PERSON 3: MULTI-TURN CONVERSATIONAL COPILOT DEMONSTRATION")
    print("        Schneider Electric 2026 Smart Manufacturing")
    print("=" * 65 + "\n")

    # Step 1: Initialize authoritative demonstration environment
    print("[1] Initializing authoritative demonstration window...")
    run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)
    print("    -> Authoritative factory analytics snapshot ready.\n")

    client = TestClient(app)

    # Multi-turn conversation queries
    conversation_turns = [
        (
            "User (Turn 1):",
            "What can you do?",
            "Testing general assistant capability query & natural conversational style."
        ),
        (
            "User (Turn 2):",
            "What is the factory energy consumption?",
            "Testing factory-level energy telemetry grounding."
        ),
        (
            "User (Turn 3):",
            "How does that compare with baseline?",
            "Testing retrospective production-aware expected-energy baseline comparison."
        ),
        (
            "User (Turn 4):",
            "Can we calculate SEC right now?",
            "Testing production-normalized Specific Energy Consumption semantics."
        ),
        (
            "User (Turn 5):",
            "Which machine should I investigate?",
            "Testing opportunity analytics without infringing on Person 1 actuator control."
        ),
        (
            "User (Turn 6):",
            "What about M01?",
            "Testing machine-specific deep dive and operational status."
        ),
    ]

    for turn_label, query, note in conversation_turns:
        print("-" * 65)
        print(f"{turn_label} \"{query}\"")
        print(f"Context Note: {note}")
        print("-" * 65)

        res = client.post("/copilot/chat", json={"question": query})
        if res.status_code != 200:
            print(f"ERROR: Received status code {res.status_code}")
            continue

        data = res.json()
        intent = data.get("intent", "UNKNOWN")
        grounded = data.get("grounded", False)
        fallback = data.get("fallback_used", False)
        answer = data.get("answer", "").strip()

        mode_badge = "GENERAL CONVERSATION" if intent == "GENERAL_CHAT" else "GROUNDED FACTORY ANALYTICS"
        print(f"\n[Execution Mode: {mode_badge} | Intent: {intent} | Grounded: {grounded} | Fallback: {fallback}]\n")
        print(f"Assistant:\n{answer}\n")

    print("=" * 65)
    print("  CONVERSATIONAL COPILOT DEMONSTRATION COMPLETE")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_copilot_demo_conversation()
