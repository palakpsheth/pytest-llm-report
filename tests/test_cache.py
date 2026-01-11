# SPDX-License-Identifier: MIT
"""Tests for pytest_llm_report.cache module."""

from pytest_llm_report.cache import LlmCache, hash_source
from pytest_llm_report.models import LlmAnnotation
from pytest_llm_report.options import Config


class TestHashSource:
    """Tests for hash_source function."""

    def test_consistent_hash(self):
        """Same source should produce same hash."""
        source = "def test_foo(): pass"
        assert hash_source(source) == hash_source(source)

    def test_different_source_different_hash(self):
        """Different source should produce different hash."""
        assert hash_source("def test_a(): pass") != hash_source("def test_b(): pass")

    def test_hash_length(self):
        """Hash should be 16 characters."""
        h = hash_source("test")
        assert len(h) == 16


class TestLlmCache:
    """Tests for LlmCache class."""

    def test_get_missing(self, tmp_path):
        """Should return None for missing entries."""
        config = Config(cache_dir=str(tmp_path / "cache"))
        cache = LlmCache(config)

        result = cache.get("test::foo", "abc123")
        assert result is None

    def test_set_and_get(self, tmp_path):
        """Should store and retrieve annotations."""
        config = Config(cache_dir=str(tmp_path / "cache"))
        cache = LlmCache(config)

        annotation = LlmAnnotation(
            scenario="Tests login",
            why_needed="Prevents bypass",
            key_assertions=["Check status"],
            confidence=0.9,
        )

        cache.set("test::foo", "abc123", annotation)
        result = cache.get("test::foo", "abc123")

        assert result is not None
        assert result.scenario == "Tests login"
        assert result.confidence == 0.9

    def test_does_not_cache_errors(self, tmp_path):
        """Should not cache annotations with errors."""
        config = Config(cache_dir=str(tmp_path / "cache"))
        cache = LlmCache(config)

        annotation = LlmAnnotation(error="API timeout")

        cache.set("test::foo", "abc123", annotation)
        result = cache.get("test::foo", "abc123")

        assert result is None

    def test_clear(self, tmp_path):
        """Should clear all cache entries."""
        config = Config(cache_dir=str(tmp_path / "cache"))
        cache = LlmCache(config)

        # Add some entries
        cache.set("test::a", "hash1", LlmAnnotation(scenario="A"))
        cache.set("test::b", "hash2", LlmAnnotation(scenario="B"))

        # Clear
        count = cache.clear()

        assert count == 2
        assert cache.get("test::a", "hash1") is None
        assert cache.get("test::b", "hash2") is None
