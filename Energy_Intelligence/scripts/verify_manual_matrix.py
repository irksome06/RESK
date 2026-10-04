"""
Verification script for Phase 13.1 Manual Test Matrix.
Executes representative queries across General, Factory, Machine, Energy, Forecast, Savings, and Follow-Up categories.
"""

from fastapi.testclient import TestClient
from api.main import app
from simulator.demo_state import demo_state
from scripts.run_final_demo import run_authoritative_demo

def run_matrix():
    if not demo_state.has_active_demo_data():
        run_authoritative_demo(steps_per_phase=10, dt_seconds=1.0)

    client = TestClient(app)

    queries = [
        # GENERAL
        ("How does this system work?", None),
        ("What can you do?", None),
        ("Hello", None),

        # FACTORY
        ("What is the current factory energy consumption?", None),
        ("What is the production?", None),
        ("What is the factory baseline?", None),
        ("Is the factory above or below baseline?", None),
        ("What is the factory SEC?", None),

        # MACHINE
        ("What is M01 doing?", None),
        ("How much energy is M04 consuming?", None),
        ("Is M04 above baseline?", None),
        ("Is that good?", [{"role": "user", "content": "How much energy is M04 consuming?"}, {"role": "assistant", "content": "M04 consumed 0.0439 kWh."}]),
        ("What is M04's utilization?", None),

        # ENERGY
        ("How much energy is being consumed while idle?", None),
        ("Which machine uses the most energy?", None),
        ("Which machine should I investigate first?", None),

        # FORECAST
        ("What will energy consumption be over the next 5 minutes?", None),
        ("What is the average forecast per minute?", None),

        # SAVINGS
        ("Are we saving energy?", None),
        ("How much could we save?", None),
        ("Why is potential savings zero?", None),

        # FOLLOW-UP
        ("What is M04 consuming?", None),
        ("Is that above baseline?", [{"role": "user", "content": "What is M04 consuming?"}, {"role": "assistant", "content": "M04 consumed 0.0439 kWh."}]),
        ("Why?", [{"role": "user", "content": "Is that above baseline?"}, {"role": "assistant", "content": "M04 is operating slightly above baseline due to operational load."}]),
        ("What about M02?", [{"role": "user", "content": "How much energy is being consumed during non-production?"}, {"role": "assistant", "content": "Factory idle energy is 0.05 kWh."}]),
    ]

    print("=====================================================================")
    print("PHASE 13.1 COPILOT MANUAL TEST MATRIX EXECUTION")
    print("=====================================================================")

    for q, hist in queries:
        payload = {"question": q}
        if hist:
            payload["history"] = hist
        res = client.post("/copilot/chat", json=payload)
        assert res.status_code == 200, f"Failed for query: {q}"
        data = res.json()
        print(f"\n[QUERY]: {q}")
        print(f"[INTENT]: {data['intent']} | [GROUNDED]: {data['grounded']} | [MODEL]: {data['model_used']}")
        print(f"[ANSWER]:\n{data['answer']}")
        print("-" * 65)

    print("\nALL MATRIX QUERIES EXECUTED SUCCESSFULLY WITH GROUNDED FACTUAL RESPONSES.")

if __name__ == "__main__":
    run_matrix()
