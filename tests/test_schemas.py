# SPDX-License-Identifier: MIT
"""Tests for LLM schemas."""

from pytest_llm_report.llm.schemas import AnnotationSchema


class TestAnnotationSchema:
    def test_from_dict_full(self):
        """Should create from dictionary with all fields."""
        data = {
            "scenario": "Verify login",
            "why_needed": "Catch auth bugs",
            "key_assertions": ["assert 200", "assert token"],
            "confidence": 0.95,
        }
        schema = AnnotationSchema.from_dict(data)
        assert schema.scenario == "Verify login"
        assert schema.why_needed == "Catch auth bugs"
        assert schema.key_assertions == ["assert 200", "assert token"]
        assert schema.confidence == 0.95

    def test_to_dict_full(self):
        """Should convert to dictionary with all fields."""
        schema = AnnotationSchema(
            scenario="Verify login",
            why_needed="Catch auth bugs",
            key_assertions=["assert 200", "assert token"],
            confidence=0.95,
        )
        data = schema.to_dict()
        assert data["scenario"] == "Verify login"
        assert data["why_needed"] == "Catch auth bugs"
        assert data["key_assertions"] == ["assert 200", "assert token"]
        assert data["confidence"] == 0.95
