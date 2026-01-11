# Security Baseline

Minimum security requirements for pytest-llm-report.

## Secure Defaults

| Setting | Default | Security Rationale |
|---------|---------|-------------------|
| `provider` | `"none"` | No data leaves machine |
| `llm_context_mode` | `"minimal"` | Limits exposed code |
| `llm_context_exclude_globs` | secrets patterns | Prevents secret exposure |

## Dependency Management

- Dependencies pinned in `uv.lock`
- Dependabot enabled for updates
- `pip-audit` in CI for vulnerability scanning

## Code Security

- Ruff linting with security rules
- No `eval()` or dynamic code execution
- Input validation on all user options
- Atomic file writes prevent corruption

## Report Security

- SHA256 hash for integrity verification
- Optional HMAC signature for tamper evidence
- No executable code in HTML reports (CSP safe)
- Deterministic output for reproducibility

## CI/CD Security

- Python 3.11-3.13 matrix testing
- 90% test coverage requirement
- Automated release on git tags
- Trusted publishing (OIDC) for PyPI

## Incident Response

1. Security issues via private reporting
2. 48-hour acknowledgment SLA
3. CVE assignment for critical issues
4. Coordinated disclosure timeline
