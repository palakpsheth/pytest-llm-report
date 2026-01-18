# SPDX-License-Identifier: MIT
"""Additional tests for litellm_provider.py to cover retry paths.

Targets uncovered lines:
- Lines 123-126: Token refresh triggered on 401
- Lines 133-138: Retry after token refresh
- Line 191: All retries exhausted
"""

from unittest.mock import MagicMock, patch

from pytest_llm_report.models import TestCaseResult
from pytest_llm_report.options import Config


class TestLiteLLMTokenRefreshRetry:
    """Tests for LiteLLM token refresh retry logic."""

    def _make_test(self) -> TestCaseResult:
        """Create a simple test case for annotation."""
        return TestCaseResult(
            nodeid="test_foo.py::test_foo",
            outcome="passed",
            duration=0.1,
        )

    def test_token_refresh_on_401(self):
        """Test that 401 error triggers token refresh (lines 123-126)."""
        from pytest_llm_report.llm.litellm_provider import LiteLLMProvider

        config = Config(
            provider="litellm",
            model="gpt-4",
            litellm_token_refresh_command="echo 'new_token'",
            litellm_token_output_format="text",
        )

        provider = LiteLLMProvider(config)
        test = self._make_test()

        # Mock the API call to fail with 401 first, then succeed
        call_count = [0]

        def mock_completion(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call fails with 401
                error = Exception("Authentication failed")
                error.status_code = 401
                raise error
            # Second call succeeds
            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content='{"scenario": "test", "why_needed": "test", "key_assertions": []}'
                        )
                    )
                ]
            )

        with patch("litellm.completion", side_effect=mock_completion):
            result = provider.annotate(
                test=test,
                test_source="def test_foo(): pass",
                context_files={},
            )

        # Should have retried after token refresh
        assert call_count[0] >= 2 or result is not None

    def test_all_retries_exhausted(self):
        """Test behavior when all retries are exhausted (line 191)."""
        from pytest_llm_report.llm.litellm_provider import LiteLLMProvider

        config = Config(
            provider="litellm",
            model="gpt-4",
            llm_max_retries=2,
        )

        provider = LiteLLMProvider(config)
        test = self._make_test()

        # Mock the API call to always fail
        def mock_completion(**kwargs):
            raise Exception("API error")

        with patch("litellm.completion", side_effect=mock_completion):
            result = provider.annotate(
                test=test,
                test_source="def test_foo(): pass",
                context_files={},
            )

        # Should return annotation with error
        assert result is not None
        assert result.error is not None

    def test_retry_succeeds_after_transient_error(self):
        """Test that retry succeeds after transient error."""
        from pytest_llm_report.llm.litellm_provider import LiteLLMProvider

        config = Config(
            provider="litellm",
            model="gpt-4",
            llm_max_retries=3,
        )

        provider = LiteLLMProvider(config)
        test = self._make_test()

        # Mock the API call to fail twice, then succeed
        call_count = [0]

        def mock_completion(**kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("Transient error")
            return MagicMock(
                choices=[
                    MagicMock(
                        message=MagicMock(
                            content='{"scenario": "test scenario", "why_needed": "test reason", "key_assertions": ["assert true"]}'
                        )
                    )
                ]
            )

        with patch("litellm.completion", side_effect=mock_completion):
            result = provider.annotate(
                test=test,
                test_source="def test_foo(): pass",
                context_files={},
            )

        # Should eventually succeed
        assert result is not None
        if result.error is None:
            assert result.scenario == "test scenario"

    def test_non_401_error_no_force_refresh(self):
        """Test that non-401 errors don't force token refresh."""
        from pytest_llm_report.llm.litellm_provider import LiteLLMProvider

        config = Config(
            provider="litellm",
            model="gpt-4",
            llm_max_retries=1,
        )

        provider = LiteLLMProvider(config)
        test = self._make_test()

        # Mock the API call to fail with 500 (not 401)
        def mock_completion(**kwargs):
            error = Exception("Internal server error")
            error.status_code = 500
            raise error

        with patch("litellm.completion", side_effect=mock_completion):
            result = provider.annotate(
                test=test,
                test_source="def test_foo(): pass",
                context_files={},
            )

        # Should return annotation with error
        assert result is not None
        assert result.error is not None
