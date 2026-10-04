"""
Phase 11 Energy Copilot API Endpoints.
Natural-language interface grounded strictly in deterministic Python analytics.
Endpoints:
- POST /copilot/chat
- GET /copilot/summary
- POST /copilot/machine/{machine_id}
- POST /copilot/query (legacy backwards compatibility)
"""

import time
import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status

from database.schemas import (
    CopilotChatRequest,
    CopilotChatResponse,
    CopilotSummaryResponse,
    CopilotMachineQueryRequest,
)
from simulator.config import settings
from simulator.machine_simulator import DEFAULT_PROFILES
from llm.context_builder import context_builder
from llm.ollama_client import ollama_client
from llm.prompts import build_copilot_prompt, COPILOT_SYSTEM_PROMPT, STRICT_REGENERATION_PROMPT
from llm.validation import validate_copilot_response
from llm.fallback import generate_deterministic_fallback

logger = logging.getLogger("api.copilot")

router = APIRouter(prefix="/copilot", tags=["Energy Copilot"])


def _process_copilot_query(
    question: str,
    machine_id: Optional[str] = None,
    history: Optional[list] = None,
) -> CopilotChatResponse:
    """
    Core pipeline: Context building -> LLM generation / Fallback -> Hallucination validation.
    """
    t0 = time.time()
    # 1. Build authoritative structured context
    context = context_builder.build_context(question=question, machine_id_override=machine_id, history=history)
    intent = context["intent"]
    context_text = context["text_representation"]
    grounded_facts = context["grounded_facts"]
    model_name = settings.OLLAMA_MODEL

    answer_text = ""
    fallback_used = False
    validation_passed = True

    # 2. Check if Ollama is available
    if ollama_client.is_available():
        prompt = build_copilot_prompt(
            question=question,
            context_str=context_text,
            intent=intent,
            conversation_history=history,
        )

        gen_res = ollama_client.generate(prompt=prompt, system_prompt=COPILOT_SYSTEM_PROMPT)

        if gen_res["success"] and gen_res["text"]:
            candidate_text = gen_res["text"]
            # Validate output against grounding constraints
            val_res = validate_copilot_response(
                candidate_text,
                grounded_facts=grounded_facts,
                context_text=context_text,
            )

            if val_res["is_valid"]:
                answer_text = candidate_text
                validation_passed = True
            else:
                logger.warning("Copilot validation failed: %s. Attempting strict regeneration...", val_res["violations"])
                # Attempt strict regeneration once
                strict_prompt = prompt + "\n\n" + STRICT_REGENERATION_PROMPT
                strict_res = ollama_client.generate(prompt=strict_prompt, system_prompt=COPILOT_SYSTEM_PROMPT)

                if strict_res["success"] and strict_res["text"]:
                    strict_val = validate_copilot_response(
                        strict_res["text"],
                        grounded_facts=grounded_facts,
                        context_text=context_text,
                    )
                    if strict_val["is_valid"]:
                        answer_text = strict_res["text"]
                        validation_passed = True
                    else:
                        logger.warning("Strict regeneration also violated grounding: %s. Using deterministic fallback.", strict_val["violations"])
                        answer_text = generate_deterministic_fallback(context, question)
                        fallback_used = True
                        validation_passed = False
                        model_name = "deterministic_analytics_fallback"
                else:
                    answer_text = generate_deterministic_fallback(context, question)
                    fallback_used = True
                    validation_passed = False
                    model_name = "deterministic_analytics_fallback"
        else:
            logger.info("Ollama error (%s). Using deterministic analytics fallback.", gen_res.get("error"))
            answer_text = generate_deterministic_fallback(context, question)
            fallback_used = True
            model_name = "deterministic_analytics_fallback"
    else:
        # Deterministic fallback when Ollama is unavailable
        logger.info("Ollama daemon is offline. Delivering deterministic evidence-grounded response.")
        answer_text = generate_deterministic_fallback(context, question)
        fallback_used = True
        model_name = "deterministic_analytics_fallback"

    latency = round(time.time() - t0, 3)
    logger.info("Copilot query processed in %ss (Intent: %s, Fallback: %s)", latency, intent, fallback_used)

    return CopilotChatResponse(
        answer=answer_text,
        intent=intent,
        grounded=True,
        context_summary=context["context_summary"],
        model_used=model_name,
        fallback_used=fallback_used,
        validation_passed=validation_passed,
    )


@router.post(
    "/chat",
    response_model=CopilotChatResponse,
    status_code=status.HTTP_200_OK,
)
def copilot_chat(request: CopilotChatRequest):
    """
    Submits a natural language energy intelligence query to the Copilot.
    Responses are grounded strictly in deterministic Python analytics.
    """
    clean_q = request.question.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question must not be empty.",
        )

    return _process_copilot_query(
        question=clean_q,
        machine_id=request.machine_id,
        history=request.history,
    )


@router.post(
    "/machine/{machine_id}",
    response_model=CopilotChatResponse,
    status_code=status.HTTP_200_OK,
)
def copilot_machine_chat(machine_id: str, request: CopilotMachineQueryRequest):
    """
    Submits a machine-specific energy intelligence query to the Copilot.
    """
    clean_id = machine_id.strip().upper()
    if clean_id not in DEFAULT_PROFILES and not clean_id.startswith("M"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine '{machine_id}' not found.",
        )

    return _process_copilot_query(
        question=request.question,
        machine_id=clean_id,
        history=request.history,
    )


@router.get(
    "/summary",
    response_model=CopilotSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def get_copilot_executive_summary():
    """
    Generates a concise factory executive energy summary.
    All numerical KPIs are strictly derived from authoritative analytics.
    """
    context = context_builder.build_context(question="How is the factory performing?")
    structured = context.get("structured_data", {})
    fs = structured.get("factory_summary", {})

    opps = structured.get("opportunities", [])
    top_opp = f"{opps[0]['opportunity_id']} on {opps[0]['machine_id']}: {opps[0]['reason']}" if opps else None
    rec_action = opps[0]["suggested_action"] if opps else "Continue baseline monitoring and standard production schedules."

    # Generate summary text
    fallback_text = generate_deterministic_fallback(context, question="Summarize factory energy performance.")
    summary_prose = fallback_text.split("\n\n")[0].replace("Summary:\n", "")

    return CopilotSummaryResponse(
        timestamp=datetime.now(timezone.utc),
        factory_summary=summary_prose,
        energy_kwh=fs.get("actual_energy_kwh", 0.0),
        expected_energy_kwh=fs.get("expected_energy_kwh", 0.0),
        potential_savings_kwh=fs.get("potential_savings_kwh", 0.0),
        potential_savings_inr=fs.get("potential_savings_inr", 0.0),
        actual_sec_kwh_per_unit=fs.get("actual_sec_kwh_per_unit"),
        production_units=fs.get("production_units", 0),
        top_opportunity=top_opp,
        recommended_action=rec_action,
        model_used=settings.OLLAMA_MODEL if ollama_client.is_available() else "deterministic_analytics_fallback",
    )


# ==========================================
# LEGACY ENDPOINT (BACKWARD COMPATIBILITY)
# ==========================================

from pydantic import BaseModel


class CopilotQuery(BaseModel):
    query: str
    machine_id: str = "M01"


@router.post("/query")
def query_copilot_legacy(payload: CopilotQuery):
    """
    Preserved legacy endpoint from Phase 5 for backwards compatibility.
    """
    resp = _process_copilot_query(question=payload.query, machine_id=payload.machine_id)
    return {
        "query": payload.query,
        "machine_id": payload.machine_id,
        "response": resp.answer,
        "grounded": resp.grounded,
        "intent": resp.intent,
    }
