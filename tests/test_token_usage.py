from unittest.mock import MagicMock

from pytest_llm_report.models import LlmAnnotation, LlmTokenUsage, TestCaseResult
from pytest_llm_report.options import Config
from pytest_llm_report.plugin import (
    _collector_key,
    _config_key,
    _enabled_key,
    pytest_terminal_summary,
)


def test_token_usage_aggregation(tmp_path):
    # Import inside function to avoid early binding issues
    from unittest.mock import patch

    # Mock config
    config = MagicMock(spec=Config)
    config.is_llm_enabled.return_value = True
    config.provider = "mock_provider"
    config.llm_context_mode = "minimal"
    config.report_json = str(tmp_path / "report.json")
    config.report_html = None
    config.report_pdf = None
    config.aggregate_dir = None
    config.repo_root = tmp_path

    # Mock stash
    class MockStash(dict):
        pass

    stash = MockStash(
        {_enabled_key: True, _config_key: config, _collector_key: MagicMock()}
    )
    pytest_config = MagicMock()
    del pytest_config.workerinput  # Prevent being identified as xdist worker
    pytest_config.stash = stash

    # Mock test results with token usage
    test1 = TestCaseResult(nodeid="test1", outcome="passed")
    test1.llm_annotation = LlmAnnotation(
        token_usage=LlmTokenUsage(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )
    )

    test2 = TestCaseResult(nodeid="test2", outcome="failed")
    test2.llm_annotation = LlmAnnotation(
        token_usage=LlmTokenUsage(
            prompt_tokens=20, completion_tokens=10, total_tokens=30
        )
    )

    test3 = TestCaseResult(nodeid="test3", outcome="passed")
    test3.llm_annotation = None  # No annotation

    collector = stash[_collector_key]
    collector.get_results.return_value = [test1, test2, test3]
    collector.get_collection_errors.return_value = []

    # Mock terminal reporter
    terminalreporter = MagicMock()

    # Mock dependencies
    with (
        patch("pytest_llm_report.coverage_map.CoverageMapper"),
        patch("pytest_llm_report.report_writer.ReportWriter") as mock_writer_cls,
        patch("pytest_llm_report.llm.annotator.annotate_tests"),
        patch("pytest_llm_report.llm.base.get_provider") as mock_get_provider,
    ):
        mock_writer = MagicMock()
        mock_writer_cls.return_value = mock_writer

        mock_provider = MagicMock()
        mock_provider.get_model_name.return_value = "mock_model"
        mock_get_provider.return_value = mock_provider

        # Run terminal summary
        pytest_terminal_summary(terminalreporter, 0, pytest_config)

        # Verify
        assert mock_writer_cls.called
        writer_instance = mock_writer_cls.return_value
        call_args = writer_instance.write_report.call_args
        assert call_args is not None
        llm_info = call_args.kwargs["llm_info"]

        assert llm_info["total_input_tokens"] == 30
        assert llm_info["total_output_tokens"] == 15
        assert llm_info["total_tokens"] == 45
        assert llm_info["annotations_count"] == 2
