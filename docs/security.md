# Security

Security considerations for pytest-llm-report.

## Reporting Vulnerabilities

Please report security issues via:
1. GitHub Private Vulnerability Reporting
2. Email: security@example.com

**Do not open public issues for security vulnerabilities.**

## Secure Defaults

| Setting | Default | Why |
|---------|---------|-----|
| `provider` | `"none"` | No external data transmission |
| Exclude globs | secrets patterns | Prevents accidental exposure |
| Redact patterns | API keys, tokens | Sanitizes CLI output |

## Report Integrity

Reports include:
- SHA256 content hash
- Git SHA for source correlation
- Optional HMAC signature

Verify report integrity:
```bash
sha256sum report.json
```

## LLM Security

When using LLM providers:

### Local (Ollama)
- Data stays on your machine
- No network exposure
- Full control over model

### Cloud (LiteLLM, Gemini)
- Data sent to external provider
- Review provider's security policies
- Consider data residency requirements

## Best Practices

1. Use `provider = "none"` in public repos
2. Use local Ollama for sensitive code
3. Review excluded patterns for your needs
4. Store reports in access-controlled locations
5. Enable HMAC for compliance requirements

See also:
- [policies/threat-model.md](../policies/threat-model.md)
- [policies/security-baseline.md](../policies/security-baseline.md)
