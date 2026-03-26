"""Structured JSON output helper for GeminiClient.

Provides a reliable alternative to with_structured_output(): invoke the LLM
(configured with json_mode=True for native JSON enforcement) and parse manually.
"""
import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def _strip_markdown(text: str) -> str:
    """Remove ```json ... ``` code fences if the model wraps its output."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    return text


def invoke_structured(llm, prompt: str, model_class: Type[T]) -> T:
    """Invoke an LLM and validate its JSON response into model_class.

    Args:
        llm: A GeminiClient instance (ideally created with json_mode=True).
        prompt: The full prompt string (should describe the expected JSON keys).
        model_class: Pydantic model to validate the parsed JSON against.

    Returns:
        A validated instance of model_class.
    """
    from langchain_core.messages import HumanMessage

    response = llm.invoke([HumanMessage(content=prompt)])
    raw = _strip_markdown(response.content)
    data = json.loads(raw)
    return model_class.model_validate(data)
