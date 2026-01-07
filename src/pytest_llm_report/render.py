# SPDX-License-Identifier: MIT
"""HTML report rendering using Jinja2.

This module renders the HTML report from a ReportRoot using
Jinja2 templates. The output is deterministic.

Component Contract:
    Input: ReportRoot
    Output: HTML string
    Dependencies: jinja2, models
"""

from __future__ import annotations

from importlib.resources import files
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader, select_autoescape

if TYPE_CHECKING:
    from pytest_llm_report.models import ReportRoot


def get_template_dir() -> str:
    """Get the path to the templates directory.

    Returns:
        Path to templates directory.
    """
    templates = files("pytest_llm_report") / "templates"
    return str(templates)


def create_jinja_env() -> Environment:
    """Create and configure the Jinja2 environment.

    Returns:
        Configured Jinja2 environment.
    """
    template_dir = get_template_dir()

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Add custom filters
    env.filters["duration"] = format_duration
    env.filters["outcome_class"] = outcome_to_css_class

    return env


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string (e.g., "1.23s", "45ms").
    """
    if seconds >= 1:
        return f"{seconds:.2f}s"
    return f"{seconds * 1000:.0f}ms"


def outcome_to_css_class(outcome: str) -> str:
    """Convert outcome to CSS class.

    Args:
        outcome: Test outcome.

    Returns:
        CSS class name.
    """
    mapping = {
        "passed": "outcome-passed",
        "failed": "outcome-failed",
        "skipped": "outcome-skipped",
        "xfailed": "outcome-xfailed",
        "xpassed": "outcome-xpassed",
        "error": "outcome-error",
    }
    return mapping.get(outcome, "outcome-unknown")


def render_html(report: "ReportRoot") -> str:
    """Render the HTML report.

    Args:
        report: Report data to render.

    Returns:
        Rendered HTML string.
    """
    env = create_jinja_env()

    try:
        template = env.get_template("report.html.j2")
    except Exception:
        # Fallback to inline template if file not found
        return render_fallback_html(report)

    return template.render(report=report)


def render_fallback_html(report: "ReportRoot") -> str:
    """Render a simple fallback HTML report.

    Used when template files are not available.

    Args:
        report: Report data to render.

    Returns:
        Rendered HTML string.
    """
    tests_html = []
    for test in sorted(report.tests, key=lambda t: t.nodeid):
        css_class = outcome_to_css_class(test.outcome)
        duration = format_duration(test.duration)

        coverage_html = ""
        if test.coverage:
            files = [f"{c.file_path} ({c.line_count} lines)" for c in test.coverage]
            coverage_html = f'<div class="coverage">{", ".join(files)}</div>'

        annotation_html = ""
        if test.llm_annotation:
            a = test.llm_annotation
            annotation_html = f"""
            <div class="llm-annotation">
                <strong>Scenario:</strong> {a.scenario}<br>
                <strong>Why needed:</strong> {a.why_needed}
            </div>
            """

        error_html = ""
        if test.error_message:
            error_html = f'<div class="error-message">{test.error_message}</div>'

        tests_html.append(f"""
        <div class="test {css_class}">
            <span class="outcome">{test.outcome.upper()}</span>
            <span class="nodeid">{test.nodeid}</span>
            <span class="duration">{duration}</span>
            {error_html}
            {coverage_html}
            {annotation_html}
        </div>
        """)

    summary = report.summary
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>pytest-llm-report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        .summary {{ display: flex; gap: 20px; margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px; }}
        .summary-item {{ text-align: center; }}
        .summary-item .count {{ font-size: 24px; font-weight: bold; }}
        .test {{ padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 4px solid #ccc; }}
        .outcome-passed {{ border-left-color: #22c55e; background: #f0fdf4; }}
        .outcome-failed {{ border-left-color: #ef4444; background: #fef2f2; }}
        .outcome-skipped {{ border-left-color: #eab308; background: #fefce8; }}
        .outcome-xfailed {{ border-left-color: #f97316; background: #fff7ed; }}
        .outcome-xpassed {{ border-left-color: #a855f7; background: #faf5ff; }}
        .outcome-error {{ border-left-color: #ef4444; background: #fef2f2; }}
        .outcome {{ font-weight: bold; display: inline-block; min-width: 80px; }}
        .nodeid {{ font-family: monospace; }}
        .duration {{ color: #666; margin-left: 10px; }}
        .error-message {{ color: #b91c1c; font-family: monospace; font-size: 0.9em; margin-top: 5px; }}
        .coverage {{ color: #059669; font-size: 0.85em; margin-top: 5px; }}
        .llm-annotation {{ margin-top: 10px; padding: 10px; background: #f0f7ff; border-radius: 4px; font-size: 0.9em; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>Test Report</h1>
    <div class="meta">
        Generated at {report.run_meta.end_time} | Duration: {format_duration(report.run_meta.duration)} |
        Schema v{report.schema_version}
    </div>
    <div class="summary">
        <div class="summary-item"><div class="count">{summary.total}</div>Total</div>
        <div class="summary-item" style="color:#22c55e"><div class="count">{summary.passed}</div>Passed</div>
        <div class="summary-item" style="color:#ef4444"><div class="count">{summary.failed}</div>Failed</div>
        <div class="summary-item" style="color:#eab308"><div class="count">{summary.skipped}</div>Skipped</div>
        <div class="summary-item" style="color:#f97316"><div class="count">{summary.xfailed}</div>XFailed</div>
        <div class="summary-item" style="color:#ef4444"><div class="count">{summary.error}</div>Error</div>
    </div>
    <h2>Tests</h2>
    {"".join(tests_html)}
</body>
</html>
"""
