# Threat Model

This document describes the security threat model for pytest-llm-report.

## Assets

1. **Test code** - Source code of tests being analyzed
2. **Coverage data** - Files and lines executed by each test
3. **LLM API keys** - Credentials for cloud LLM providers
4. **Generated reports** - HTML/JSON output files

## Threat Actors

1. **Malicious test code** - Tests could contain sensitive data
2. **Compromised LLM provider** - Cloud provider could log/leak data
3. **Report readers** - Unauthorized access to reports

## Threats and Mitigations

### T1: Sensitive data sent to LLM

**Threat**: Test code containing secrets, PII, or proprietary logic sent to external LLM.

**Mitigations**:
- Default provider is `"none"` (no LLM calls)
- `llm_context_exclude_globs` excludes secret files by default
- Local Ollama option for sensitive codebases
- Opt-out marker `@pytest.mark.llm_opt_out`

### T2: API key exposure

**Threat**: LLM API keys exposed in logs, reports, or version control.

**Mitigations**:
- Keys read from environment variables only
- `invocation_redact_patterns` redacts CLI args
- Keys never included in reports

### T3: Report tampering

**Threat**: Reports modified after generation to hide failures.

**Mitigations**:
- SHA256 hash of report content
- Optional HMAC signature with shared key
- Git SHA in metadata for correlation

### T4: Unauthorized report access

**Threat**: Reports accessed by unauthorized parties.

**Mitigations**:
- Reports are local files (user controls access)
- No built-in upload or sharing functionality
- CI artifacts inherit CI access controls

## Security Recommendations

1. Use `provider = "none"` for CI/public repos
2. Use local Ollama for sensitive codebases
3. Review `llm_context_exclude_globs` for your environment
4. Enable HMAC signing for compliance requirements
5. Store reports in access-controlled locations
