# SPDX-License-Identifier: MIT
"""Tests for token refresh functionality."""

from __future__ import annotations

import json
import subprocess
import threading
import time

import pytest

from pytest_llm_report.llm.token_refresh import TokenRefresher, TokenRefreshError


class TestTokenRefresher:
    """Tests for the TokenRefresher class."""

    def test_get_token_text_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher extracts token from text output."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="INFO: Processing...\nmy-secret-token\n",
                stderr="Some log output",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="text",
        )

        token = refresher.get_token()
        assert token == "my-secret-token"

    def test_get_token_json_format(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher extracts token from JSON output."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"token": "json-token-value", "expires_in": 3600}),
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

        token = refresher.get_token()
        assert token == "json-token-value"

    def test_get_token_json_custom_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher uses custom JSON key."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"access_token": "custom-key-token"}),
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="json",
            json_key="access_token",
        )

        token = refresher.get_token()
        assert token == "custom-key-token"

    def test_token_caching(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher caches token and doesn't call command again."""
        call_count = 0

        def fake_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=f"token-{call_count}",
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="text",
        )

        token1 = refresher.get_token()
        token2 = refresher.get_token()

        assert token1 == "token-1"
        assert token2 == "token-1"  # Same token, cached
        assert call_count == 1  # Only called once

    def test_force_refresh(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher force=True bypasses cache."""
        call_count = 0

        def fake_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=f"token-{call_count}",
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="text",
        )

        token1 = refresher.get_token()
        token2 = refresher.get_token(force=True)

        assert token1 == "token-1"
        assert token2 == "token-2"  # New token after force refresh
        assert call_count == 2

    def test_invalidate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher.invalidate() clears cache."""
        call_count = 0

        def fake_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=f"token-{call_count}",
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="text",
        )

        token1 = refresher.get_token()
        refresher.invalidate()
        token2 = refresher.get_token()

        assert token1 == "token-1"
        assert token2 == "token-2"
        assert call_count == 2

    def test_command_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher raises error on command failure."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="Authentication failed",
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
        assert "Authentication failed" in str(exc_info.value)

    def test_empty_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher raises error on empty output."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="",
                stderr="",
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

        assert "empty output" in str(exc_info.value).lower()

    def test_invalid_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher raises error on invalid JSON."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout="not valid json",
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="json",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "json" in str(exc_info.value).lower()

    def test_missing_json_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher raises error when JSON key is missing."""

        def fake_run(*args, **kwargs):
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"other_key": "value"}),
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

        assert "token" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()

    def test_thread_safety(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher is thread-safe."""
        call_count = 0
        lock = threading.Lock()

        def fake_run(*args, **kwargs):
            nonlocal call_count
            with lock:
                call_count += 1
                current = call_count
            # Simulate slow command
            time.sleep(0.05)
            result = subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=f"token-{current}",
                stderr="",
            )
            return result

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="text",
        )

        results = []
        threads = []

        def get_token():
            token = refresher.get_token()
            results.append(token)

        # Start multiple threads concurrently
        for _ in range(5):
            t = threading.Thread(target=get_token)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should get the same token (first one to acquire lock)
        assert len(set(results)) == 1
        assert results[0] == "token-1"

    def test_timeout_handling(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """TokenRefresher handles command timeout."""

        def fake_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="get-token", timeout=30)

        monkeypatch.setattr(subprocess, "run", fake_run)

        refresher = TokenRefresher(
            command="get-token",
            refresh_interval=3600,
            output_format="text",
        )

        with pytest.raises(TokenRefreshError) as exc_info:
            refresher.get_token()

        assert "timed out" in str(exc_info.value).lower()
