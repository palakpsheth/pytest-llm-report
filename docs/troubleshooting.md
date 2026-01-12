# Troubleshooting

Common issues and solutions for pytest-llm-report.

## "No coverage contexts found"

**Problem**: Report shows warnings about missing coverage contexts.

**Solution**: Run with `--cov-context=test`:
```bash
pytest --cov=my_pkg --cov-context=test --llm-report=report.html
```

## "No .coverage file found"

**Problem**: Plugin can't find coverage data.

**Solutions**:
1. Ensure pytest-cov is installed: `pip install pytest-cov`
2. Add `--cov=your_package` to pytest options
3. Check you're not running with `--no-cov`

## Empty coverage in reports

**Problem**: Tests show 0 covered files.

**Solutions**:
1. Verify `--cov-context=test` is set
2. Check source path: `--cov=correct/path`
3. Clear old data: `coverage erase`

## LLM annotations not appearing

**Problem**: Tests don't have LLM annotations.

**Solutions**:
1. Check provider is set: `provider = "ollama"`, `"litellm"`, or `"gemini"`
2. Verify Ollama is running: `ollama serve`
3. Check API key is set for cloud providers (LiteLLM or Gemini)
4. Confirm the provider dependency is installed (e.g., `pytest-llm-report[litellm]`)
5. Look for errors in pytest output

## Ollama connection refused

**Problem**: Can't connect to Ollama.

**Solutions**:
1. Start Ollama: `ollama serve`
2. Check host: `ollama_host = "http://127.0.0.1:11434"`
3. Verify model is pulled: `ollama list`

## Report not generated

**Problem**: No HTML/JSON output.

**Solutions**:
1. Check output path: `--llm-report=/path/to/report.html`
2. Ensure directory exists
3. Check for errors at end of pytest output

## Dark mode not working

**Problem**: Report doesn't switch to dark theme.

**Solutions**:
1. Check your OS/browser dark mode setting is enabled
2. Ensure you're using a modern browser (Chrome 76+, Firefox 67+, Safari 12.1+)
3. Some browsers require `about:config` flags for `prefers-color-scheme`

## Still stuck?

[Open an issue on GitHub](https://github.com/palakpsheth/pytest-llm-report/issues/new) with:
- pytest-llm-report version
- Full pytest output (with `-v`)
- Your pyproject.toml configuration
