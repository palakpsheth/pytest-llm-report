# SPDX-License-Identifier: MIT
from pytest_llm_report.aggregation import Aggregator
from pytest_llm_report.models import Summary, TestCaseResult
from pytest_llm_report.options import Config


class TestAggregationMaximal:
    def test_recalculate_summary_coverage(self):
        config = Config()
        agg = Aggregator(config)

        tests = [
            TestCaseResult(nodeid="t1", outcome="passed", duration=1.0),
            TestCaseResult(nodeid="t2", outcome="failed", duration=2.0),
        ]
        latest_summary = Summary(coverage_total_percent=88.5)

        summary = agg._recalculate_summary(tests, latest_summary)
        assert summary.total == 2
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.coverage_total_percent == 88.5
        assert summary.total_duration == 3.0
