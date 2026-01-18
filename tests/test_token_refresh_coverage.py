# SPDX-License-Identifier: MIT
"""Additional tests for token_refresh.py to increase coverage.

Targets uncovered lines:
- Line 87-88: Invalid command string parsing
- Line 91: Empty command string
- Line 116: OSError when executing command
- Line 136: JSON is not a dict
- Line 145: Empty/non-string token value
- Line 155: No non-empty lines in output
"""

from __future__ import annotations

import json
import subprocess

import pytest

from pytest_llm_report.llm.token_refresh import TokenRefresher, TokenRefreshError


class TestTokenRefresherEdgeCases:
    """Tests for edge cases in TokenRefresher."""

    def test_invalid_command_string(self) -> None:
        """Test handling of invalid command string (shlex parse error)."""
        refresher = TokenRefresher(
            command='echo "unclosed quote',  # Invalid shell syntax
            refresh_interval=3600,
            output_format="text",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "Invalid command string" in str(exc_info.value)

    def test_empty_command_string(self) -> None:
        """Test handling of empty command string."""
        refresher = TokenRefresher(
            command="",
            refresh_interval=3600,
            output_format="text",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_only_command(self) -> None:
        """Test handling of whitespace-only command string."""
        refresher = TokenRefresher(
            command="   ",
            refresh_interval=3600,
            output_format="text",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "empty" in str(exc_info.value).lower()

    def test_oserror_on_execution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of OSError when executing command."""

        def fake_run(*args, **kwargs):
            raise OSError("Command not found")

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="nonexistent-command",
            refresh_interval=3600,
            output_format="text",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "Failed to execute" in str(exc_info.value)

    def test_json_not_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling when JSON output is not a dict."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps(["array", "not", "dict"]),
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="json",
            json_key="token",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "Expected JSON object" in str(exc_info.value)
        assert "list" in str(exc_info.value)

    def test_json_token_not_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling when token value is not a string."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"token": 12345}),  # int, not string
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="json",
            json_key="token",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "empty or not a string" in str(exc_info.value)

    def test_json_token_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling when token value is an empty string."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"token": "   "}),  # whitespace only
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="json",
            json_key="token",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "empty or not a string" in str(exc_info.value)

    def test_text_only_whitespace_lines(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling when text output has only whitespace lines after initial strip."""
        # Note: Since stdout.strip() is called first, we need output that is
        # non-empty after strip() but has only whitespace lines when splitlines() is called.
        # This is actually impossible since strip() would make it empty.
        # Instead, test the _parse_output method directly to cover line 155.

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="text",
        )

        # Directly test the parsing method with text that has only blank lines
        # after the initial strip is done (output that has non-whitespace wrapper
        # but only whitespace content lines)
        with pytest.raises(TokenRefreshError) as exc_info:
            refresher._parse_output("   \n\t\n  ")  # Only whitespace lines

        assert "No non-empty lines" in str(exc_info.value)

    def test_command_failure_no_stderr(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling when command fails with no stderr output."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="",  # No error output
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="text",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "exit 1" in str(exc_info.value)
        assert "No error output" in str(exc_info.value)
