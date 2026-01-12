# SPDX-License-Identifier: MIT
"""Contract tests for LLM provider interface.

Tests validate schema normalization and noop behavior.
"""

from pytest_llm_report.llm.base import LlmProvider, get_provider
from pytest_llm_report.llm.noop import NoopProvider
from pytest_llm_report.llm.schemas import ANNOTATION_JSON_SCHEMA, AnnotationSchema
from pytest_llm_report.options import Config


class TestAnnotationSchema:
    """Tests for LLM annotation schema."""

    def test_schema_has_required_fields(self):
        """Schema defines required fields."""
        assert "scenario" in ANNOTATION_JSON_SCHEMA["properties"]
        assert "why_needed" in ANNOTATION_JSON_SCHEMA["properties"]
        assert "key_assertions" in ANNOTATION_JSON_SCHEMA["properties"]

    def test_required_fields(self):
        """Schema requires scenario and why_needed."""
        required = ANNOTATION_JSON_SCHEMA.get("required", [])
        assert "scenario" in required
        assert "why_needed" in required

    def test_schema_from_dict(self):
        """AnnotationSchema parses from dict."""
        data = {
            "scenario": "Tests user login",
            "why_needed": "Prevents auth bypass",
            "key_assertions": ["checks password", "checks username"],
            "confidence": 0.95,
        }
        schema = AnnotationSchema.from_dict(data)

        assert schema.scenario == "Tests user login"
        assert schema.why_needed == "Prevents auth bypass"
        assert len(schema.key_assertions) == 2
        assert schema.confidence == 0.95

    def test_schema_to_dict(self):
        """AnnotationSchema serializes to dict."""
        schema = AnnotationSchema(
            scenario="Tests feature X",
            why_needed="Prevents bug Y",
            key_assertions=["assertion 1"],
        )
        data = schema.to_dict()

        assert data["scenario"] == "Tests feature X"
        assert data["why_needed"] == "Prevents bug Y"
        assert "key_assertions" in data

    def test_schema_handles_empty(self):
        """AnnotationSchema handles empty input."""
        schema = AnnotationSchema.from_dict({})
        assert schema.scenario == ""
        assert schema.why_needed == ""

    def test_schema_handles_partial(self):
        """AnnotationSchema handles partial input."""
        schema = AnnotationSchema.from_dict({"scenario": "Partial only"})
        assert schema.scenario == "Partial only"
        assert schema.why_needed == ""


class TestNoopProvider:
    """Tests for NoopProvider behavior."""

    def test_noop_returns_empty_annotation(self):
        """NoopProvider returns empty annotation."""
        from pytest_llm_report.models import TestCaseResult

        config = Config()
        provider = NoopProvider(config)
        test = TestCaseResult(nodeid="test_nodeid", outcome="passed")
        result = provider.annotate(test, "def test(): pass", {})

        assert result.scenario == ""
        assert result.why_needed == ""
        assert result.key_assertions == []

    def test_noop_is_llm_provider(self):
        """NoopProvider implements LlmProvider."""
        config = Config()
        provider = NoopProvider(config)
        assert isinstance(provider, LlmProvider)

    def test_noop_from_factory(self):
        """Factory returns NoopProvider for provider='none'."""
        config = Config(provider="none")
        provider = get_provider(config)
        assert isinstance(provider, NoopProvider)


class TestProviderContract:
    """Contract tests for provider interface."""

    def test_provider_has_annotate_method(self):
        """All providers have annotate method."""
        for provider_name in ["none", "ollama", "litellm", "gemini"]:
            config = Config(provider=provider_name, model="test")
            provider = get_provider(config)
            assert hasattr(provider, "annotate")
            assert callable(provider.annotate)

    def test_annotate_returns_annotation(self):
        """Annotate returns LlmAnnotation-like object."""
        from pytest_llm_report.models import TestCaseResult

        config = Config()
        provider = NoopProvider(config)
        test = TestCaseResult(nodeid="test::nodeid", outcome="passed")
        result = provider.annotate(test, "code", {})

        # Check it has expected attributes
        assert hasattr(result, "scenario")
        assert hasattr(result, "why_needed")
        assert hasattr(result, "key_assertions")

    def test_provider_handles_empty_code(self):
        """Provider handles empty code gracefully."""
        from pytest_llm_report.models import TestCaseResult

        config = Config()
        provider = NoopProvider(config)
        test = TestCaseResult(nodeid="test::nodeid", outcome="passed")
        result = provider.annotate(test, "", {})
        assert result is not None

    def test_provider_handles_none_context(self):
        """Provider handles None context gracefully."""
        from pytest_llm_report.models import TestCaseResult

        config = Config()
        provider = NoopProvider(config)
        test = TestCaseResult(nodeid="test::nodeid", outcome="passed")
        result = provider.annotate(test, "code", None)
        assert result is not None
