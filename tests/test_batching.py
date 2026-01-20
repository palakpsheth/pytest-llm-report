# SPDX-License-Identifier: MIT
"""Tests for test batching functionality."""

from pytest_llm_report.llm.batching import (
    BatchedRequest,
    _compute_source_hash,
    _get_base_nodeid,
    build_batch_prompt,
    group_tests_for_batching,
)
from pytest_llm_report.models import TestCaseResult
from pytest_llm_report.options import Config


class TestGetBaseNodeid:
    """Tests for base nodeid extraction."""

    def test_simple_nodeid(self):
        """Simple nodeid without params should return unchanged."""
        assert (
            _get_base_nodeid("tests/test_foo.py::test_bar")
            == "tests/test_foo.py::test_bar"
        )

    def test_parametrized_nodeid(self):
        """Parametrized nodeid should strip params."""
        assert (
            _get_base_nodeid("tests/test_foo.py::test_add[1+1=2]")
            == "tests/test_foo.py::test_add"
        )

    def test_nested_params(self):
        """Complex params should be fully stripped."""
        assert _get_base_nodeid("test.py::test[a-b-c]") == "test.py::test"


class TestComputeSourceHash:
    """Tests for source hashing."""

    def test_empty_source(self):
        """Empty source should return empty string."""
        assert _compute_source_hash("") == ""

    def test_consistent_hash(self):
        """Same source should produce same hash."""
        source = "def test_foo(): assert True"
        hash1 = _compute_source_hash(source)
        hash2 = _compute_source_hash(source)
        assert hash1 == hash2
        assert len(hash1) == 32

    def test_different_source_different_hash(self):
        """Different source should produce different hash."""
        hash1 = _compute_source_hash("def test_a(): pass")
        hash2 = _compute_source_hash("def test_b(): pass")
        assert hash1 != hash2


class TestGroupTestsForBatching:
    """Tests for test grouping logic."""

    def _make_test(self, nodeid: str) -> TestCaseResult:
        """Helper to create TestCaseResult."""
        return TestCaseResult(
            nodeid=nodeid,
            outcome="passed",
            duration=0.1,
        )

    def test_single_tests_no_grouping(self):
        """Single tests should each be their own batch."""
        config = Config(provider="none", batch_parametrized_tests=True)
        tests = [
            self._make_test("test.py::test_a"),
            self._make_test("test.py::test_b"),
        ]

        batches = group_tests_for_batching(tests, config, lambda n: "")

        assert len(batches) == 2
        assert len(batches[0].tests) == 1
        assert len(batches[1].tests) == 1

    def test_parametrized_tests_grouped(self):
        """Parametrized tests should be grouped together."""
        config = Config(
            provider="none", batch_parametrized_tests=True, batch_max_tests=10
        )
        tests = [
            self._make_test("test.py::test_add[1+1=2]"),
            self._make_test("test.py::test_add[0+0=0]"),
            self._make_test("test.py::test_add[-1+1=0]"),
        ]

        batches = group_tests_for_batching(
            tests, config, lambda n: "def test_add(): pass"
        )

        assert len(batches) == 1
        assert len(batches[0].tests) == 3
        assert batches[0].is_parametrized
        assert batches[0].base_nodeid == "test.py::test_add"

    def test_batching_disabled(self):
        """With batching disabled, each test should be separate."""
        config = Config(provider="none", batch_parametrized_tests=False)
        tests = [
            self._make_test("test.py::test_add[1]"),
            self._make_test("test.py::test_add[2]"),
        ]

        batches = group_tests_for_batching(tests, config, lambda n: "")

        assert len(batches) == 2

    def test_batch_max_size_respected(self):
        """Large groups should be split by batch_max_tests."""
        config = Config(
            provider="none", batch_parametrized_tests=True, batch_max_tests=2
        )
        tests = [
            self._make_test("test.py::test_add[1]"),
            self._make_test("test.py::test_add[2]"),
            self._make_test("test.py::test_add[3]"),
            self._make_test("test.py::test_add[4]"),
            self._make_test("test.py::test_add[5]"),
        ]

        batches = group_tests_for_batching(tests, config, lambda n: "")

        assert len(batches) == 3  # 2, 2, 1
        assert len(batches[0].tests) == 2
        assert len(batches[1].tests) == 2
        assert len(batches[2].tests) == 1


class TestBuildBatchPrompt:
    """Tests for batch prompt generation."""

    def _make_test(self, nodeid: str) -> TestCaseResult:
        """Helper to create TestCaseResult."""
        return TestCaseResult(
            nodeid=nodeid,
            outcome="passed",
            duration=0.1,
        )

    def test_single_test_prompt(self):
        """Single test should generate normal prompt."""
        batch = BatchedRequest(
            tests=[self._make_test("test.py::test_foo")],
            base_nodeid="test.py::test_foo",
        )
        source = "def test_foo(): assert True"

        prompt = build_batch_prompt(batch, source)

        assert "Test: test.py::test_foo" in prompt
        assert "```python" in prompt
        assert source in prompt
        assert "Parameterizations" not in prompt

    def test_parametrized_batch_prompt(self):
        """Parametrized batch should include all variants."""
        batch = BatchedRequest(
            tests=[
                self._make_test("test.py::test_add[1+1=2]"),
                self._make_test("test.py::test_add[0+0=0]"),
            ],
            base_nodeid="test.py::test_add",
        )
        source = "def test_add(a, b, expected): assert a + b == expected"

        prompt = build_batch_prompt(batch, source)

        assert "Test Group: test.py::test_add[*]" in prompt
        assert "Parameterizations (2 variants)" in prompt
        assert "[1+1=2]" in prompt
        assert "[0+0=0]" in prompt
        assert "ONE annotation" in prompt

    def test_context_files_included(self):
        """Context files should be added to prompt."""
        batch = BatchedRequest(
            tests=[self._make_test("test.py::test_foo")],
            base_nodeid="test.py::test_foo",
        )
        context = {"src/module.py": "def helper(): pass"}

        prompt = build_batch_prompt(batch, "def test_foo(): pass", context)

        assert "src/module.py" in prompt
        assert "def helper()" in prompt


class TestConfigValidation:
    """Test configuration validation for Phase 2 options."""

    def test_valid_context_compression(self):
        """Valid compression modes should pass."""
        for mode in ["none", "lines"]:
            config = Config(provider="none", context_compression=mode)
            errors = config.validate()
            assert not any("context_compression" in e for e in errors)

    def test_invalid_context_compression(self):
        """Invalid compression mode should fail."""
        config = Config(provider="none", context_compression="invalid")
        errors = config.validate()
        assert any("context_compression" in e for e in errors)

    def test_batch_max_tests_minimum(self):
        """batch_max_tests must be at least 1."""
        config = Config(provider="none", batch_max_tests=0)
        errors = config.validate()
        assert any("batch_max_tests" in e for e in errors)

    def test_context_line_padding_non_negative(self):
        """context_line_padding must be non-negative."""
        config = Config(provider="none", context_line_padding=-1)
        errors = config.validate()
        assert any("context_line_padding" in e for e in errors)
