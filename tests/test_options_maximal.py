# SPDX-License-Identifier: MIT
from pytest_llm_report.options import Config


def test_config_validation_invalid_provider():
    config = Config(provider="unknown")
    errors = config.validate()
    assert any("Invalid provider" in e for e in errors)


def test_config_validation_invalid_context_mode():
    config = Config(llm_context_mode="crazy")
    errors = config.validate()
    assert any("Invalid llm_context_mode" in e for e in errors)


def test_config_validation_invalid_aggregate_policy():
    config = Config(aggregate_policy="none")
    errors = config.validate()
    assert any("Invalid aggregate_policy" in e for e in errors)


def test_config_validation_invalid_include_phase():
    config = Config(include_phase="invalid")
    errors = config.validate()
    assert any("Invalid include_phase" in e for e in errors)


def test_config_validation_numeric_bounds():
    # llm_context_bytes too small
    assert any(
        "bytes must be at least 1000" in e
        for e in Config(llm_context_bytes=500).validate()
    )

    # llm_max_tests negative
    assert any("max_tests must be 0" in e for e in Config(llm_max_tests=-1).validate())

    # llm_requests_per_minute < 1
    assert any(
        "requests_per_minute must be at least 1" in e
        for e in Config(llm_requests_per_minute=0).validate()
    )

    # llm_timeout_seconds < 1
    assert any(
        "timeout_seconds must be at least 1" in e
        for e in Config(llm_timeout_seconds=0).validate()
    )


def test_config_is_llm_enabled():
    assert Config(provider="ollama").is_llm_enabled() is True
    assert Config(provider="none").is_llm_enabled() is False


def test_get_default_config():
    from pytest_llm_report.options import get_default_config

    config = get_default_config()
    assert isinstance(config, Config)
    assert config.provider == "none"


def test_config_all_fields_accessible():
    import dataclasses

    config = Config()
    for f in dataclasses.fields(Config):
        _ = getattr(config, f.name)
    assert True
