"""
Ollama Client for Local Qwen Model Inference.
Provides fault-tolerant HTTP transport to the local Ollama daemon.
Handles timeouts, model errors, and connection failures gracefully without crashing FastAPI.
"""

import logging
from typing import Optional, Dict, Any
import requests

from simulator.config import settings
from llm.prompts import COPILOT_SYSTEM_PROMPT

logger = logging.getLogger("llm.ollama")


class OllamaClient:
    """
    HTTP client for local Ollama LLM execution.
    """

    def __init__(
        self,
        base_url: str = settings.OLLAMA_BASE_URL,
        model: str = settings.OLLAMA_MODEL,
        timeout_seconds: int = settings.LLM_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        """Checks if the local Ollama server is responsive."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            return resp.status_code == 200
        except Exception:
            return False

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submits prompt to Ollama and returns structured generation response.

        Returns:
            Dict containing:
                - success: bool
                - text: str (generated text if success else "")
                - error: Optional[str] ("LLM_SERVICE_UNAVAILABLE", "TIMEOUT", "HTTP_ERROR", "MALFORMED_RESPONSE")
                - model: str
        """
        target_model = model_override or self.model
        sys_prompt = system_prompt or COPILOT_SYSTEM_PROMPT

        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": sys_prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for factual grounding
                "top_p": 0.9,
            },
        }

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout_seconds,
            )

            if resp.status_code != 200:
                logger.warning("Ollama returned non-200 status code: %s (%s)", resp.status_code, resp.text)
                return {
                    "success": False,
                    "text": "",
                    "error": f"HTTP_{resp.status_code}",
                    "model": target_model,
                }

            data = resp.json()
            if not isinstance(data, dict) or "response" not in data:
                return {
                    "success": False,
                    "text": "",
                    "error": "MALFORMED_RESPONSE",
                    "model": target_model,
                }

            return {
                "success": True,
                "text": str(data["response"]).strip(),
                "error": None,
                "model": target_model,
            }

        except requests.exceptions.Timeout:
            logger.warning("Ollama inference timed out after %s seconds", self.timeout_seconds)
            return {
                "success": False,
                "text": "",
                "error": "TIMEOUT",
                "model": target_model,
            }
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to Ollama daemon at %s", self.base_url)
            return {
                "success": False,
                "text": "",
                "error": "LLM_SERVICE_UNAVAILABLE",
                "model": target_model,
            }
        except Exception as e:
            logger.error("Unexpected error during Ollama generation: %s", e)
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "model": target_model,
            }


# Singleton client instance
ollama_client = OllamaClient()
