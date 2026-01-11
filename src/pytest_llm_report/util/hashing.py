# SPDX-License-Identifier: MIT
"""Hashing and provenance utilities.

Provides cryptographic hashing for tamper evidence and
provenance tracking.

Component Contract:
    Input: file content, config
    Output: hashes, signatures
"""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pytest_llm_report.options import Config


def compute_sha256(content: bytes) -> str:
    """Compute SHA256 hash of content.

    Args:
        content: Bytes to hash.

    Returns:
        Hex digest string.
    """
    return hashlib.sha256(content).hexdigest()


def compute_file_sha256(path: Path | str) -> str:
    """Compute SHA256 hash of a file.

    Args:
        path: Path to file.

    Returns:
        Hex digest string.
    """
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_hmac(content: bytes, key: bytes) -> str:
    """Compute HMAC-SHA256 of content.

    Args:
        content: Content to sign.
        key: HMAC key.

    Returns:
        Hex digest string.
    """
    return hmac.new(key, content, hashlib.sha256).hexdigest()


def load_hmac_key(config: Config) -> bytes | None:
    """Load HMAC key from config.

    Args:
        config: Plugin configuration.

    Returns:
        Key bytes or None if not configured.
    """
    if not config.hmac_key_file:
        return None

    key_path = Path(config.hmac_key_file)
    if not key_path.exists():
        return None

    try:
        return key_path.read_bytes().strip()
    except Exception:
        return None


def compute_config_hash(config: Config) -> str:
    """Compute a hash of the config for reproducibility.

    Args:
        config: Plugin configuration.

    Returns:
        Short hash string.
    """
    # Hash relevant config values
    values = [
        config.provider,
        config.model,
        config.llm_context_mode,
        str(config.llm_context_bytes),
        str(config.llm_max_tests),
    ]
    content = ":".join(values).encode()
    return hashlib.sha256(content).hexdigest()[:16]


def get_dependency_snapshot() -> dict[str, str]:
    """Get installed package versions.

    Returns:
        Dict of package names to versions.
    """
    try:
        from importlib.metadata import distributions

        packages = {}
        for dist in distributions():
            name = dist.metadata["Name"]
            version = dist.metadata["Version"]
            packages[name] = version
        return dict(sorted(packages.items()))
    except Exception:
        return {}
