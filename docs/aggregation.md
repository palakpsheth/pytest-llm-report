# Report Aggregation

pytest-llm-report allows you to aggregate multiple test reports into a single, unified report. This is particularly useful for:

- **Parallel Test Execution**: Combining results from multiple CI jobs or sharded runs.
- **Multi-Environment Testing**: Merging results from different Python versions or platforms.
- **Flaky Test Analysis**: Combining multiple runs to spot inconsistent failures.

## Usage

To aggregate reports, you use the plugin in a special aggregation mode using `--llm-aggregate-dir`:

```bash
pytest --collect-only \
  --llm-aggregate-dir=path/to/reports \
  --llm-report=aggregated.html
```

> [!NOTE]
> We use `--collect-only` to avoid running tests during aggregation. The plugin intercepts the session finish hook to perform aggregation instead.

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--llm-aggregate-dir DIR` | Directory containing JSON reports (`.json`) to aggregate | None |
| `--llm-aggregate-policy POLICY` | Aggregation policy (`latest`, `merge`, `all`) | `latest` |
| `--llm-aggregate-run-id ID` | Unique ID for the new aggregated run | Auto-generated |

### Aggregation Policies

- **latest** (default): Groups results by test ID and keeps only the one with the latest start time. Useful for combining sharded runs or retries.
- **merge**: Groups results by test ID but keeps strictly distinct outcomes (not fully implemented yet, falls back to latest).
- **all**: Keeps all results as separate entries. Useful for analyzing history.

## CI Example (GitHub Actions)

Here's how to aggregate reports from a matrix strategy in GitHub Actions:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          pytest --llm-report-json=report.json \
                 --llm-aggregate-run-id=${{ github.run_id }}-${{ matrix.python }}
      - uses: actions/upload-artifact@v4
        with:
          name: report-${{ matrix.python }}
          path: report.json

  report:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          pattern: report-*
          path: all-reports
          merge-multiple: true

      - name: Aggregate Reports
        run: |
          pytest --collect-only \
            --llm-aggregate-dir=all-reports \
            --llm-report=aggregated.html
```
