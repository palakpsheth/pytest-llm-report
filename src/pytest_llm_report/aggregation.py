# SPDX-License-Identifier: MIT
"""Aggregation logic for merging multiple test reports.

This module handles reading multiple JSON reports and combining them
into a single report based on the configured policy.

Policies:
- latest: Keep only the latest result for each test (by start time)
- merge: Merge results, keeping all outcomes (useful for flaky tests)
- all: Keep all results as separate entries
"""

from __future__ import annotations

import copy
import json
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

from pytest_llm_report.models import (
    CoverageEntry,
    LlmAnnotation,
    LlmTokenUsage,
    ReportRoot,
    RunMeta,
    SourceCoverageEntry,
    Summary,
    TestCaseResult,
)

if TYPE_CHECKING:
    from pytest_llm_report.options import Config


class Aggregator:
    """Aggregates multiple test reports."""

    def __init__(self, config: Config) -> None:
        """Initialize aggregator.

        Args:
            config: Plugin configuration.
        """
        self.config = config

    def aggregate(self) -> ReportRoot | None:
        """Perform aggregation.

        Returns:
            Aggregated ReportRoot, or None if no reports found.
        """
        if not self.config.aggregate_dir:
            return None

        reports = self._load_reports()
        if not reports:
            return None

        if self.config.aggregate_policy == "all":
            # For "all", we just concatenate tests
            aggregated_tests = []
            for r in reports:
                aggregated_tests.extend(r.tests)
        elif self.config.aggregate_policy == "merge":
            # For "merge", we group by nodeid and merge results
            aggregated_tests = self._merge_tests(reports)
        else:
            # Default "latest": group by nodeid and pick latest start time
            aggregated_tests = self._latest_tests(reports)

        # Create aggregated report
        # We use the metadata from the latest run, but update counts
        latest_report = max(reports, key=lambda r: r.run_meta.start_time)
        meta = copy.deepcopy(latest_report.run_meta)

        # Update metadata to reflect aggregation
        meta.is_aggregated = True
        meta.run_count = len(reports)
        meta.collected_count = len(aggregated_tests)
        meta.selected_count = len(aggregated_tests)

        # Recalculate summary
        # Recalculate summary
        summary = self._recalculate_summary(aggregated_tests, latest_report.summary)

        # Apply coverage override if configured
        source_coverage = latest_report.source_coverage
        cov_override = self._load_coverage_from_source()
        if cov_override:
            source_coverage, pct = cov_override
            summary.coverage_total_percent = pct

        return ReportRoot(
            run_meta=meta,
            summary=summary,
            tests=aggregated_tests,
            source_coverage=source_coverage,
            collection_errors=[],  # We don't aggregate collection errors for now
            warnings=[],
            artifacts=[],
        )

    def _load_reports(self) -> list[ReportRoot]:
        """Load all JSON reports from aggregate_dir.

        Returns:
            List of ReportRoot objects.
        """
        if not self.config.aggregate_dir:
            return []

        dir_path = Path(self.config.aggregate_dir)
        if not dir_path.exists():
            return []

        reports = []
        for file_path in dir_path.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    # Basic validation - check for required fields
                    if "run_meta" not in data or "tests" not in data:
                        continue

                    # Convert dict to models (simplified)
                    # Note: We're doing a partial reconstruction here
                    # Ideally we'd have a from_dict method on models
                    meta = RunMeta(**data["run_meta"])

                    tests = []
                    for t_data in data["tests"]:
                        # Handle potential field discrepancies
                        if "llm_opt_out" not in t_data:
                            t_data["llm_opt_out"] = False

                        # Convert coverage dicts to CoverageEntry objects
                        if "coverage" in t_data and t_data["coverage"]:
                            t_data["coverage"] = [
                                CoverageEntry(**c) if isinstance(c, dict) else c
                                for c in t_data["coverage"]
                            ]

                        # Convert llm_annotation dict to LlmAnnotation object
                        if "llm_annotation" in t_data and t_data["llm_annotation"]:
                            ann_data = t_data["llm_annotation"]
                            if isinstance(ann_data, dict):
                                # Convert nested token_usage dict to LlmTokenUsage
                                if "token_usage" in ann_data and isinstance(
                                    ann_data["token_usage"], dict
                                ):
                                    ann_data["token_usage"] = LlmTokenUsage(
                                        **ann_data["token_usage"]
                                    )
                                t_data["llm_annotation"] = LlmAnnotation(**ann_data)

                        # Remove computed property 'file_path' - it's derived from nodeid
                        t_data.pop("file_path", None)

                        tests.append(TestCaseResult(**t_data))

                    reports.append(
                        ReportRoot(
                            run_meta=meta,
                            summary=Summary(**data["summary"]),
                            tests=tests,
                            source_coverage=[
                                SourceCoverageEntry(**entry)
                                for entry in data.get("source_coverage", [])
                            ],
                            collection_errors=[],
                            warnings=[],
                            artifacts=[],
                        )
                    )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                # Skip invalid files, but don't silently ignore
                warnings.warn(
                    f"Skipping invalid report file {file_path}: {e}",
                    stacklevel=2,
                )
                continue

        return reports

    def _latest_tests(self, reports: list[ReportRoot]) -> list[TestCaseResult]:
        """Keep only the latest result for each test.

        Args:
            reports: List of reports.

        Returns:
            List of unique latest tests.
        """
        # Map nodeid to (start_time, test)
        latest_map: dict[str, tuple[str, TestCaseResult]] = {}

        for report in reports:
            run_start = report.run_meta.start_time
            for test in report.tests:
                if test.nodeid not in latest_map:
                    latest_map[test.nodeid] = (run_start, test)
                else:
                    curr_start, _ = latest_map[test.nodeid]
                    if run_start > curr_start:
                        latest_map[test.nodeid] = (run_start, test)

        return sorted([t for _, t in latest_map.values()], key=lambda x: x.nodeid)

    def _merge_tests(self, reports: list[ReportRoot]) -> list[TestCaseResult]:
        """Merge results for the same test.

        Note: For now this is similar to latest, but in future could combine histories.
        Currently implementation falls back to latest logic as deep merging
        is complex without a history list in TestCaseResult.
        """
        return self._latest_tests(reports)

    def _recalculate_summary(
        self, tests: list[TestCaseResult], latest_summary: Summary
    ) -> Summary:
        """Recalculate summary stats for aggregated tests.

        Args:
            tests: List of tests.
            latest_summary: Summary from the latest report (for coverage preservation).

        Returns:
            Updated Summary.
        """
        summary = Summary(total=len(tests))
        # Preserve coverage percentage from the latest report
        summary.coverage_total_percent = latest_summary.coverage_total_percent
        for test in tests:
            summary.total_duration += test.duration
            if test.outcome == "passed":
                summary.passed += 1
            elif test.outcome == "failed":
                summary.failed += 1
            elif test.outcome == "skipped":
                summary.skipped += 1
            elif test.outcome == "xfailed":
                summary.xfailed += 1
            elif test.outcome == "xpassed":
                summary.xpassed += 1
            elif test.outcome == "error":
                summary.error += 1

        return summary

    def _load_coverage_from_source(
        self,
    ) -> tuple[list[SourceCoverageEntry], float] | None:
        """Load coverage from configured source file.

        Returns:
            Tuple of (source_entries, total_percent) or None.
        """
        if not self.config.llm_coverage_source:
            return None

        try:
            from coverage import Coverage

            from pytest_llm_report.coverage_map import CoverageMapper

            cov_path = Path(self.config.llm_coverage_source)
            if not cov_path.exists():
                warnings.warn(
                    f"Coverage source not found: {cov_path}",
                    stacklevel=2,
                )
                return None

            # Load coverage data
            cov = Coverage(data_file=str(cov_path))
            cov.load()

            mapper = CoverageMapper(self.config)
            entries = mapper.map_source_coverage(cov)

            # Calculate total using cov.report() for consistency with CLI
            import io

            out = io.StringIO()
            percent = round(cov.report(file=out), 2)

            return entries, percent

        except Exception as e:
            warnings.warn(
                f"Failed to load coverage override: {e}",
                stacklevel=2,
            )
            return None
