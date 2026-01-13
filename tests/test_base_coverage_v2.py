# SPDX-License-Identifier: MIT
import json

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.options import Config


class MockProvider(LlmProvider):
    def _annotate_internal(self, test, test_source, context_files=None):
        return None

    def _check_availability(self):
        return True


def test_base_parse_response_non_string_fields():
    """Cover lines 204, 206: non-string scenario/why_needed."""
    provider = MockProvider(Config())
    response_data = {
        "scenario": 123,  # int
        "why_needed": ["list"],  # list
        "key_assertions": ["a"],
    }

    annotation = provider._parse_response(json.dumps(response_data))
    assert annotation.scenario == "123"
    assert annotation.why_needed == "['list']"
    assert annotation.key_assertions == ["a"]


def test_base_parse_response_malformed_json_after_extract():
    """Cover lines 220-221: JSONDecodeError."""
    provider = MockProvider(Config())
    # extract_json_from_response will find braces, but contents are invalid
    response = "{ invalid json }"

    annotation = provider._parse_response(response)
    assert annotation.error == "Failed to parse LLM response as JSON"
