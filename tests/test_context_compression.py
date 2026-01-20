# SPDX-License-Identifier: MIT
"""Tests for context compression functionality."""

from pytest_llm_report.options import Config
from pytest_llm_report.prompts import ContextAssembler


class TestExtractCoveredLines:
    """Tests for the _extract_covered_lines method."""

    def test_extract_single_line(self):
        """Single covered line should be extracted with padding."""
        config = Config(provider="none")
        assembler = ContextAssembler(config)

        lines = ["line 0", "line 1", "line 2", "line 3", "line 4", "line 5"]
        covered = {3}  # Line 3 (1-indexed)

        result = assembler._extract_covered_lines(lines, covered, padding=1)

        # Should include lines 2, 3, 4 (with 1 line padding)
        assert "# L2:" in result
        assert "# L3:" in result
        assert "# L4:" in result

    def test_extract_multiple_ranges(self):
        """Multiple covered ranges should be extracted with gap indicators."""
        config = Config(provider="none")
        assembler = ContextAssembler(config)

        lines = [f"line {i}" for i in range(20)]
        covered = {3, 15}  # Two separate covered lines

        result = assembler._extract_covered_lines(lines, covered, padding=1)

        # Should have gap indicator between ranges
        assert "# ..." in result
        assert "# L3:" in result
        assert "# L15:" in result

    def test_empty_coverage(self):
        """Empty coverage should return empty string."""
        config = Config(provider="none")
        assembler = ContextAssembler(config)

        result = assembler._extract_covered_lines(["line1", "line2"], set(), padding=2)

        assert result == ""

    def test_padding_boundary(self):
        """Padding should not go beyond file boundaries."""
        config = Config(provider="none")
        assembler = ContextAssembler(config)

        lines = ["line 1", "line 2", "line 3"]
        covered = {1}  # First line

        result = assembler._extract_covered_lines(lines, covered, padding=5)

        # Should not have negative line numbers
        assert "# L1:" in result
        assert "# L2:" in result
        assert "# L3:" in result
        assert "# L0:" not in result
        assert "# L4:" not in result

    def test_contiguous_lines_no_gap(self):
        """Contiguous covered lines should not have gap indicators."""
        config = Config(provider="none")
        assembler = ContextAssembler(config)

        lines = [f"line {i}" for i in range(10)]
        covered = {3, 4, 5}  # Contiguous lines

        result = assembler._extract_covered_lines(lines, covered, padding=0)

        # No gap indicator for contiguous lines
        assert result.count("# ...") == 0
        assert "# L3:" in result
        assert "# L4:" in result
        assert "# L5:" in result


class TestContextCompression:
    """Tests for context compression in ContextAssembler."""

    def test_compression_enabled_by_default(self):
        """Context compression should be enabled by default ("lines")."""
        config = Config(provider="none")
        # Compression mode check
        assert config.context_compression == "lines"

    def test_compression_mode_lines(self):
        """Lines compression mode should be available."""
        config = Config(provider="none", context_compression="lines")
        assert config.context_compression == "lines"

    def test_line_padding_default(self):
        """Line padding should default to 2."""
        config = Config(provider="none")
        assert config.context_line_padding == 2


class TestConfigValidation:
    """Tests for compression configuration validation."""

    def test_valid_compression_modes(self):
        """Valid compression modes should pass validation."""
        for mode in ["none", "lines"]:
            config = Config(provider="none", context_compression=mode)
            errors = config.validate()
            assert not any("context_compression" in e for e in errors)

    def test_invalid_compression_mode(self):
        """Invalid compression mode should fail validation."""
        config = Config(provider="none", context_compression="invalid")
        errors = config.validate()
        assert any("context_compression" in e for e in errors)

    def test_negative_padding_invalid(self):
        """Negative padding should fail validation."""
        config = Config(provider="none", context_line_padding=-1)
        errors = config.validate()
        assert any("context_line_padding" in e for e in errors)

    def test_zero_padding_valid(self):
        """Zero padding should be valid."""
        config = Config(provider="none", context_line_padding=0)
        errors = config.validate()
        assert not any("context_line_padding" in e for e in errors)
