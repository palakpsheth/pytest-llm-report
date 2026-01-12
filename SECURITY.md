# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in pytest-llm-report, please report it by:

1. **GitHub Security Advisories**: Use [GitHub's private vulnerability reporting](https://github.com/palakpsheth/pytest-llm-report/security/advisories/new)
2. **Private disclosure**: Open a draft security advisory for confidential discussion

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix timeline**: Depends on severity

### Security considerations

This plugin handles test code and may send it to LLM providers:

- **Default behavior**: Provider is `"none"` - no data leaves your machine
- **When LLM is enabled**: Test code is sent to the configured provider
- **Secrets**: We exclude common secret file patterns from context
- **Redaction**: Command-line arguments matching sensitive patterns are redacted

### Best practices

1. Never enable LLM features in production CI without review
2. Review `llm_context_exclude_globs` for your environment
3. Use local LLM (Ollama) for sensitive codebases
4. Rotate any API keys that may have been exposed
