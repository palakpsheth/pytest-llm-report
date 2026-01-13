# SPDX-License-Identifier: MIT

from pytest_llm_report.llm.gemini import (
    GeminiProvider,
    _GeminiRateLimitConfig,
    _GeminiRateLimiter,
)
from pytest_llm_report.models import LlmAnnotation, RunMeta, SourceCoverageEntry
from pytest_llm_report.options import Config


class TestCoverageBoosters:
    def test_gemini_model_parsing_edge_cases(self):
        config = Config(model="m1, m2")
        provider = GeminiProvider(config)

        # Test basic parsing
        models = provider._parse_preferred_models()
        assert "m1" in models
        assert "m2" in models

        # Test empty models list (None)
        config.model = None
        assert provider._parse_preferred_models() == []

        # Test "all"
        config.model = "All"
        assert provider._parse_preferred_models() == []

    def test_gemini_rate_limiter_edge_math(self):
        limits = _GeminiRateLimitConfig(requests_per_minute=10, tokens_per_minute=100)
        limiter = _GeminiRateLimiter(limits)

        # record tokens but not request
        limiter.record_tokens(50)
        # next_available_in(tokens)
        assert limiter.next_available_in(60) > 0  # Over token limit (50+60 > 100)
        assert limiter.next_available_in(10) == 0  # Under both limits

    def test_models_to_dict_variants(self):
        # SourceCoverageEntry
        sce = SourceCoverageEntry(
            file_path="a.py",
            statements=10,
            covered=5,
            missed=5,
            coverage_percent=50.0,
            covered_ranges="1-5",
            missed_ranges="6-10",
        )
        d = sce.to_dict()
        assert d["coverage_percent"] == 50.0

        # LlmAnnotation with error
        ann = LlmAnnotation(error="timeout")
        assert ann.to_dict()["error"] == "timeout"

        # RunMeta variants
        meta = RunMeta(start_time="now", end_time="later", duration=1.0)
        assert meta.to_dict()["duration"] == 1.0
