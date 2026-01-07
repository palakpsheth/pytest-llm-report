# ADR 0003: Report Formats

## Status
Accepted

## Context

Reports need to be useful for both humans and CI systems.

## Decision

Support three output formats:
1. **HTML** - Human-readable, interactive
2. **JSON** - Machine-readable, CI integration
3. **PDF** (optional) - Portable, archival

## Consequences

### Positive
- HTML for daily use (filtering, search)
- JSON for CI/CD pipelines and tooling
- PDF for compliance and sharing
- Deterministic output (sorted by nodeid)

### Negative
- PDF requires Playwright (heavy dependency)
- Three formats to maintain
- HTML templates add complexity

## Format Details

### HTML
- Jinja2 templates
- Embedded CSS/JS (single file)
- Dark mode support
- Client-side filtering

### JSON
- Schema-validated
- SHA256 hash for integrity
- Optional HMAC signature
- Aggregation-ready

### PDF
- HTML-to-PDF via Playwright
- Matches HTML layout
- Optional (extra dependency)
