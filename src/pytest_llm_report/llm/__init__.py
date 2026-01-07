# SPDX-License-Identifier: MIT
"""LLM provider package."""

from pytest_llm_report.llm.base import LlmProvider
from pytest_llm_report.llm.noop import NoopProvider

__all__ = ["LlmProvider", "NoopProvider"]
