# SPDX-License-Identifier: MIT
"""LLM response caching.

Provides file-based caching for LLM responses to avoid
redundant API calls for unchanged tests.

Component Contract:
    Input: test nodeid, source hash, Config
    Output: cached LlmAnnotation or None
    Dependencies: models
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

from pytest_llm_report.models import LlmAnnotation

if TYPE_CHECKING:
    from pytest_llm_report.options import Config


class LlmCache:
    """File-based cache for LLM responses.

    Cache keys are based on the test nodeid and source hash.
    """

    def __init__(self, config: Config) -> None:
        """Initialize the cache.

        Args:
            config: Plugin configuration.
        """
        self.config = config
        self.cache_dir = Path(config.cache_dir)
        self.ttl_seconds = config.llm_cache_ttl_seconds

    def get(self, nodeid: str, source_hash: str) -> LlmAnnotation | None:
        """Get a cached annotation.

        Args:
            nodeid: Test nodeid.
            source_hash: Hash of the test source code.

        Returns:
            Cached annotation or None if not found/expired.
        """
        cache_path = self._get_cache_path(nodeid, source_hash)

        if not cache_path.exists():
            return None

        try:
            # Check TTL
            mtime = cache_path.stat().st_mtime
            age = time.time() - mtime
            if age > self.ttl_seconds:
                # Expired
                cache_path.unlink(missing_ok=True)
                return None

            # Load cached data
            data = json.loads(cache_path.read_text())
            return LlmAnnotation(
                scenario=data.get("scenario", ""),
                why_needed=data.get("why_needed", ""),
                key_assertions=data.get("key_assertions", []),
                confidence=data.get("confidence"),
            )
        except Exception:
            return None

    def set(self, nodeid: str, source_hash: str, annotation: LlmAnnotation) -> None:
        """Cache an annotation.

        Args:
            nodeid: Test nodeid.
            source_hash: Hash of the test source code.
            annotation: Annotation to cache.
        """
        if annotation.error:
            # Don't cache errors
            return

        cache_path = self._get_cache_path(nodeid, source_hash)

        try:
            # Ensure directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Write cache file
            data = {
                "scenario": annotation.scenario,
                "why_needed": annotation.why_needed,
                "key_assertions": annotation.key_assertions,
                "confidence": annotation.confidence,
            }
            cache_path.write_text(json.dumps(data))
        except Exception:
            pass  # Silently ignore cache write failures

    def _get_cache_path(self, nodeid: str, source_hash: str) -> Path:
        """Get the cache file path for a test.

        Args:
            nodeid: Test nodeid.
            source_hash: Source hash.

        Returns:
            Path to cache file.
        """
        # Create a stable key from nodeid + source hash
        key = f"{nodeid}:{source_hash}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]

        return self.cache_dir / f"{key_hash}.json"

    def clear(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of entries cleared.
        """
        if not self.cache_dir.exists():
            return 0

        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except Exception:
                # Ignore errors when deleting cache files (file may be in use or deleted)
                pass

        return count


def hash_source(source: str) -> str:
    """Hash source code for cache key.

    Args:
        source: Source code string.

    Returns:
        Hex digest of hash.
    """
    return hashlib.sha256(source.encode()).hexdigest()[:16]
