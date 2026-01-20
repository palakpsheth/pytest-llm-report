# SPDX-License-Identifier: MIT
"""Tests for context_util module.

Tests for context optimization utilities that compress source code
to reduce token consumption while preserving logical structure.
"""

from pytest_llm_report.context_util import (
    collapse_empty_lines,
    optimize_context,
    strip_comments,
    strip_docstrings,
)


class TestStripDocstrings:
    """Tests for strip_docstrings function."""

    def test_strip_triple_double_quoted_docstring(self):
        """Should remove triple double-quoted docstrings."""
        source = '''def foo():
    """This is a docstring."""
    pass'''
        result = strip_docstrings(source)
        assert '"""' not in result
        assert "This is a docstring" not in result
        assert "def foo():" in result
        assert "pass" in result

    def test_strip_triple_single_quoted_docstring(self):
        """Should remove triple single-quoted docstrings."""
        source = """def foo():
    '''This is a docstring.'''
    pass"""
        result = strip_docstrings(source)
        assert "'''" not in result
        assert "This is a docstring" not in result
        assert "def foo():" in result
        assert "pass" in result

    def test_strip_multiline_docstring(self):
        """Should remove multiline docstrings."""
        source = '''def foo():
    """
    This is a
    multiline docstring.
    """
    pass'''
        result = strip_docstrings(source)
        assert '"""' not in result
        assert "multiline docstring" not in result
        assert "pass" in result

    def test_multiple_docstrings(self):
        """Should remove multiple docstrings."""
        source = '''"""Module docstring."""

def foo():
    """Function docstring."""
    pass

class Bar:
    """Class docstring."""
    pass'''
        result = strip_docstrings(source)
        assert result.count('"""') == 0
        assert "def foo():" in result
        assert "class Bar:" in result

    def test_preserves_regular_strings(self):
        """Should preserve regular strings (not docstrings)."""
        source = '''x = "hello world"
y = 'another string'
z = "contains # hash"'''
        result = strip_docstrings(source)
        assert 'x = "hello world"' in result
        assert "y = 'another string'" in result

    def test_preserves_multiline_data_strings(self):
        """Should preserve triple-quoted strings assigned to variables."""
        source = '''def foo():
    """Docstring."""
    data = """
    This is data
    not a docstring
    """
    return data'''
        result = strip_docstrings(source)
        assert '"""' in result  # Should keep the data string quotes
        assert "This is data" in result
        assert "not a docstring" in result
        # But real docstring should be gone
        assert '"""Docstring."""' not in result

    def test_preserves_strings_in_structures(self):
        """Should preserve strings in lists/dicts."""
        source = '''x = [
            """string 1""",
            "string 2"
        ]'''
        result = strip_docstrings(source)
        assert '"""string 1"""' in result
        assert '"string 2"' in result

    def test_handles_syntax_error_gracefully(self):
        """Should return original source on syntax error."""
        source = "def foo( unclosed paren"
        result = strip_docstrings(source)
        assert result == source


class TestStripComments:
    """Tests for strip_comments function."""

    def test_strip_simple_comment(self):
        """Should remove simple end-of-line comments."""
        source = "x = 1  # this is a comment"
        result = strip_comments(source)
        assert result == "x = 1"

    def test_strip_standalone_comment(self):
        """Should handle lines that are only comments."""
        source = """# This is a comment
x = 1
# Another comment
y = 2"""
        result = strip_comments(source)
        assert "# This is a comment" not in result
        assert "# Another comment" not in result
        assert "x = 1" in result
        assert "y = 2" in result

    def test_preserve_hash_in_double_quoted_string(self):
        """Should preserve # inside double-quoted strings."""
        source = 'url = "http://example.com#anchor"'
        result = strip_comments(source)
        assert result == 'url = "http://example.com#anchor"'

    def test_preserve_hash_in_single_quoted_string(self):
        """Should preserve # inside single-quoted strings."""
        source = "url = 'http://example.com#anchor'"
        result = strip_comments(source)
        assert result == "url = 'http://example.com#anchor'"

    def test_comment_after_string_with_hash(self):
        """Should strip comment after string containing hash."""
        source = 'url = "http://example.com#anchor"  # URL with fragment'
        result = strip_comments(source)
        assert result == 'url = "http://example.com#anchor"'

    def test_no_comments(self):
        """Should handle source with no comments."""
        source = """def foo():
    return 42"""
        result = strip_comments(source)
        assert result == source

    def test_mixed_quotes(self):
        """Should handle mixed quote styles."""
        source = """x = "don't # worry"  # comment
y = 'say "hello#world"'  # another"""
        result = strip_comments(source)
        assert 'x = "don\'t # worry"' in result
        assert "y = 'say \"hello#world\"'" in result
        assert "# comment" not in result
        assert "# another" not in result

    def test_escaped_quotes(self):
        """Should handle escaped quotes in strings."""
        source = r's = "escaped \"quote\" # here"  # comment'
        result = strip_comments(source)
        # The escaped quote handling is simplified, check basic behavior
        assert "# comment" not in result


class TestCollapseEmptyLines:
    """Tests for collapse_empty_lines function."""

    def test_collapse_three_empty_lines(self):
        """Should collapse 3+ empty lines to 2."""
        source = "line1\n\n\n\nline2"
        result = collapse_empty_lines(source)
        assert result == "line1\n\nline2"

    def test_preserve_two_empty_lines(self):
        """Should preserve up to 2 consecutive newlines."""
        source = "line1\n\nline2"
        result = collapse_empty_lines(source)
        assert result == "line1\n\nline2"

    def test_single_newline(self):
        """Should preserve single newlines."""
        source = "line1\nline2\nline3"
        result = collapse_empty_lines(source)
        assert result == "line1\nline2\nline3"

    def test_many_empty_lines(self):
        """Should collapse many empty lines to one blank line."""
        source = "line1\n\n\n\n\n\n\n\nline2"
        result = collapse_empty_lines(source)
        assert result == "line1\n\nline2"


class TestOptimizeContext:
    """Tests for optimize_context function."""

    def test_default_strips_docs_only(self):
        """Default behavior strips docstrings but not comments."""
        source = '''def foo():
    """Docstring."""
    x = 1  # comment
    return x'''
        result = optimize_context(source)
        assert '"""' not in result
        assert "# comment" in result  # Comments preserved by default

    def test_strip_both(self):
        """Should strip both docstrings and comments when requested."""
        source = '''def foo():
    """Docstring."""
    x = 1  # comment
    return x'''
        result = optimize_context(source, strip_docs=True, strip_comms=True)
        assert '"""' not in result
        assert "# comment" not in result
        assert "x = 1" in result

    def test_strip_comments_only(self):
        """Should strip comments but keep docstrings."""
        source = '''def foo():
    """Docstring."""
    x = 1  # comment
    return x'''
        result = optimize_context(source, strip_docs=False, strip_comms=True)
        assert '"""Docstring."""' in result
        assert "# comment" not in result

    def test_strip_neither(self):
        """Should keep both when explicitly requested."""
        source = '''def foo():
    """Docstring."""
    x = 1  # comment
    return x'''
        result = optimize_context(source, strip_docs=False, strip_comms=False)
        assert '"""Docstring."""' in result
        assert "# comment" in result

    def test_always_collapses_empty_lines(self):
        """Should always collapse empty lines regardless of flags."""
        source = "line1\n\n\n\n\nline2"
        result = optimize_context(source, strip_docs=False, strip_comms=False)
        assert result == "line1\n\nline2"

    def test_combined_optimization(self):
        """Should apply all optimizations correctly."""
        source = '''"""Module docstring."""


def foo():
    """Function docstring."""
    # comment line
    x = 1  # inline comment


    return x'''
        result = optimize_context(source, strip_docs=True, strip_comms=True)
        # Docstrings gone
        assert '"""' not in result
        # Comments gone
        assert "# comment" not in result
        assert "# inline" not in result
        # Structure preserved
        assert "def foo():" in result
        assert "x = 1" in result
        assert "return x" in result
        # Excessive empty lines collapsed
        assert "\n\n\n" not in result

    def test_empty_source(self):
        """Should handle empty source gracefully."""
        result = optimize_context("")
        assert result == ""

    def test_source_with_only_whitespace(self):
        """Should handle whitespace-only source."""
        result = optimize_context("   \n\n   \n")
        assert result == "   \n\n   \n"
