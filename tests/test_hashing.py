# SPDX-License-Identifier: MIT
"""Tests for hashing utilities."""

from pytest_llm_report.options import Config
from pytest_llm_report.util.hashing import (
    compute_config_hash,
    compute_file_sha256,
    compute_hmac,
    compute_sha256,
    get_dependency_snapshot,
    load_hmac_key,
)


class TestComputeSha256:
    """Tests for compute_sha256."""

    def test_consistent(self):
        """Same content should produce same hash."""
        h1 = compute_sha256(b"test")
        h2 = compute_sha256(b"test")
        assert h1 == h2

    def test_length(self):
        """Hash should be 64 hex chars."""
        h = compute_sha256(b"test")
        assert len(h) == 64


class TestComputeFileSha256:
    """Tests for compute_file_sha256."""

    def test_hashes_file(self, tmp_path):
        """Should hash file contents."""
        path = tmp_path / "test.txt"
        path.write_bytes(b"hello world")

        h = compute_file_sha256(path)
        assert len(h) == 64

    def test_consistent_with_bytes(self, tmp_path):
        """File hash should match content hash."""
        content = b"test content"
        path = tmp_path / "test.txt"
        path.write_bytes(content)

        file_hash = compute_file_sha256(path)
        content_hash = compute_sha256(content)
        assert file_hash == content_hash


class TestComputeHmac:
    """Tests for compute_hmac."""

    def test_with_key(self):
        """Should produce HMAC with key."""
        sig = compute_hmac(b"content", b"secret-key")
        assert len(sig) == 64

    def test_different_key(self):
        """Different keys should produce different signatures."""
        sig1 = compute_hmac(b"content", b"key1")
        sig2 = compute_hmac(b"content", b"key2")
        assert sig1 != sig2


class TestLoadHmacKey:
    """Tests for load_hmac_key."""

    def test_no_key_file(self):
        """Should return None if no key file configured."""
        config = Config()
        key = load_hmac_key(config)
        assert key is None

    def test_missing_key_file(self, tmp_path):
        """Should return None if key file doesn't exist."""
        config = Config(hmac_key_file=str(tmp_path / "nonexistent.key"))
        key = load_hmac_key(config)
        assert key is None

    def test_loads_key(self, tmp_path):
        """Should load key from file."""
        key_file = tmp_path / "hmac.key"
        key_file.write_bytes(b"my-secret-key\n")

        config = Config(hmac_key_file=str(key_file))
        key = load_hmac_key(config)
        assert key == b"my-secret-key"


class TestComputeConfigHash:
    """Tests for compute_config_hash."""

    def test_returns_short_hash(self):
        """Should return 16-char hash."""
        config = Config()
        h = compute_config_hash(config)
        assert len(h) == 16

    def test_different_config(self):
        """Different configs should produce different hashes."""
        config1 = Config(provider="none")
        config2 = Config(provider="ollama")
        assert compute_config_hash(config1) != compute_config_hash(config2)


class TestGetDependencySnapshot:
    """Tests for get_dependency_snapshot."""

    def test_returns_dict(self):
        """Should return dict of packages."""
        snapshot = get_dependency_snapshot()
        assert isinstance(snapshot, dict)

    def test_includes_pytest(self):
        """Should include pytest package."""
        snapshot = get_dependency_snapshot()
        assert "pytest" in snapshot
