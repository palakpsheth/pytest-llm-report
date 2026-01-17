# SPDX-License-Identifier: MIT
"""Token refresh utilities for dynamic authentication.

Provides thread-safe, cached token refresh via subprocess execution.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass, field


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""

    pass


@dataclass
class TokenRefresher:
    """Executes a CLI command to obtain a fresh bearer token.

    Tokens are cached and refreshed before expiration. Thread-safe.

    Attributes:
        command: Shell command to run to get token.
        refresh_interval: Seconds before token expires (default: 3300 = 55 min).
        output_format: How to parse output - "text" or "json".
        json_key: Key to extract token from JSON output (default: "token").
    """

    command: str
    refresh_interval: int = 3300  # 55 minutes (refresh before 60 min expiry)
    output_format: str = "text"  # "text" or "json"
    json_key: str = "token"

    _cached_token: str | None = field(default=None, init=False, repr=False)
    _cached_at: float | None = field(default=None, init=False, repr=False)
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def get_token(self, force: bool = False) -> str:
        """Get a valid token, refreshing if necessary.

        Args:
            force: If True, bypass cache and refresh immediately.

        Returns:
            The bearer token string.

        Raises:
            TokenRefreshError: If the command fails or returns no token.
        """
        with self._lock:
            now = time.time()

            # Check if we have a valid cached token
            if not force and self._cached_token and self._cached_at:
                age = now - self._cached_at
                if age < self.refresh_interval:
                    return self._cached_token

            # Refresh token
            token = self._execute_command()
            self._cached_token = token
            self._cached_at = now
            return token

    def _execute_command(self) -> str:
        """Run the command and parse token from output.

        Returns:
            The extracted token string.

        Raises:
            TokenRefreshError: If command fails, parsing fails, or command is invalid.
        """
        try:
            # Security: Use shell=False to prevent injection. Use shlex to parse args.
            try:
                args = shlex.split(self.command)
            except ValueError as e:
                raise TokenRefreshError(f"Invalid command string: {e}") from e

            if not args:
                raise TokenRefreshError("Command string is empty")

            result = subprocess.run(
                args,
                shell=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip() if result.stderr else "No error output"
                raise TokenRefreshError(
                    f"Token refresh command failed (exit {result.returncode}): {stderr}"
                )

            stdout = result.stdout.strip()
            if not stdout:
                raise TokenRefreshError("Token refresh command returned empty output")

            return self._parse_output(stdout)

        except subprocess.TimeoutExpired as e:
            raise TokenRefreshError(f"Token refresh command timed out: {e}") from e
        except OSError as e:
            raise TokenRefreshError(
                f"Failed to execute token refresh command: {e}"
            ) from e

    def _parse_output(self, stdout: str) -> str:
        """Parse the token from command output.

        Args:
            stdout: The stdout content from the command.

        Returns:
            The extracted token.

        Raises:
            TokenRefreshError: If parsing fails.
        """
        if self.output_format == "json":
            try:
                data = json.loads(stdout)
                if not isinstance(data, dict):
                    raise TokenRefreshError(
                        f"Expected JSON object, got {type(data).__name__}"
                    )
                if self.json_key not in data:
                    raise TokenRefreshError(
                        f"JSON key '{self.json_key}' not found in response"
                    )
                token = data[self.json_key]
                if not isinstance(token, str) or not token.strip():
                    raise TokenRefreshError(
                        f"Token value for key '{self.json_key}' is empty or not a string"
                    )
                return token.strip()
            except json.JSONDecodeError as e:
                raise TokenRefreshError(f"Failed to parse JSON output: {e}") from e
        else:
            # Text mode: last non-empty line
            lines = [line.strip() for line in stdout.splitlines() if line.strip()]
            if not lines:
                raise TokenRefreshError("No non-empty lines in command output")
            return lines[-1]

    def invalidate(self) -> None:
        """Invalidate the cached token, forcing refresh on next get_token()."""
        with self._lock:
            self._cached_token = None
            self._cached_at = None
