# SPDX-License-Identifier: MIT
"""LLM response schemas.

Defines the expected JSON structure for LLM responses and utilities
for extracting JSON from LLM outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Regex to match markdown code fences with optional language identifier
# Matches ```json, ```JSON, or just ``` followed by content and closing ```
_CODE_FENCE_PATTERN = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)


def extract_json_from_response(response: str) -> str | None:
    """Extract JSON from an LLM response, handling markdown code fences.

    LLMs often wrap JSON responses in markdown code fences like:
        ```json
        {"key": "value"}
        ```

    This function handles that case and falls back to finding raw JSON braces.

    Args:
        response: Raw LLM response text.

    Returns:
        Extracted JSON string, or None if no JSON found.
    """
    if not response:
        return None

    # Try to find JSON inside code fences first
    match = _CODE_FENCE_PATTERN.search(response)
    if match:
        content = match.group(1).strip()
        # Validate it looks like JSON (starts with { or [)
        if content.startswith("{") or content.startswith("["):
            return content

    # Fallback: find raw JSON braces
    start = response.find("{")
    end = response.rfind("}") + 1
    if start >= 0 and end > start:
        return response[start:end]

    return None


@dataclass
class AnnotationSchema:
    """Schema for LLM annotation response."""

    scenario: str = ""
    why_needed: str = ""
    key_assertions: list[str] | None = None
    confidence: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnnotationSchema:
        """Create from dictionary.

        Args:
            data: Response dictionary.

        Returns:
            AnnotationSchema instance.
        """
        return cls(
            scenario=data.get("scenario", ""),
            why_needed=data.get("why_needed", ""),
            key_assertions=data.get("key_assertions"),
            confidence=data.get("confidence"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        result: dict[str, Any] = {
            "scenario": self.scenario,
            "why_needed": self.why_needed,
        }
        if self.key_assertions:
            result["key_assertions"] = self.key_assertions
        if self.confidence is not None:
            result["confidence"] = self.confidence
        return result


# JSON Schema for validation
ANNOTATION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "scenario": {
            "type": "string",
            "description": "What this test verifies in plain English",
        },
        "why_needed": {
            "type": "string",
            "description": "What bug or regression this test prevents",
        },
        "key_assertions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "The critical checks performed",
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence in the annotation (0-1)",
        },
    },
    "required": ["scenario", "why_needed"],
}


# System prompt for LLM
SYSTEM_PROMPT = """You are a test documentation assistant. Analyze the provided test code and generate a JSON annotation with:

1. scenario: A one-sentence description of what this test verifies
2. why_needed: What bug or regression this test prevents
3. key_assertions: A list of the critical checks performed (optional)
4. confidence: Your confidence in this annotation from 0.0 to 1.0 (optional)

Respond ONLY with valid JSON matching this schema:
{
  "scenario": "string",
  "why_needed": "string",
  "key_assertions": ["string"],
  "confidence": 0.95
}
"""
