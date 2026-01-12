# Test Report

<iframe src="https://palakpsheth.github.io/pytest-llm-report/reports/index.html" style="width: 100%; height: 90vh; border: 1px solid #e2e8f0; border-radius: 0.5rem;" title="Interactive Test Report"></iframe>

!!! info "Direct Links"
    - [Open the latest CI-generated report](https://palakpsheth.github.io/pytest-llm-report/reports/index.html){ target="_blank" }
    - [Open the latest CI-generated PDF report](https://palakpsheth.github.io/pytest-llm-report/reports/latest.pdf){ target="_blank" }
    - [Open the static example report](example-report/index.html){ target="_blank" }

The embedded report above is the latest CI-generated run. The static example showcases a mix of passed, failed, skipped, xfailed, xpassed, and error results.

## About the Test Report

This report is automatically generated during CI/CD runs and includes:

- **Test Results**: Pass/fail status for all tests
- **Coverage Data**: Per-test coverage information showing which files and lines each test exercises
- **Execution Time**: Duration for each test
- **Error Messages**: Full error details for failed tests
- **Source Coverage**: Per-file covered/missed/percentage summary (similar to pytest-cov)

The report uses the same pytest-llm-report plugin that this documentation describes.

## Report Features

### Interactive Filtering

- Search tests by name
- Filter by test status (passed, failed, skipped, etc.)
- Toggle visibility of passed tests

### Coverage Details

For each test, you can expand to see:

- Which source files were executed during the test
- Specific line ranges covered in each file
- Total line count per file

### Report Metadata

The report header shows:

- Total test count and breakdown by status
- Overall test suite duration
- Total coverage percentage (when available)
- Run metadata (timestamp, Python version, etc.)

### Source Coverage Summary

At the bottom of the report you'll find a table of source files with:

- Statements, missed, and covered counts
- Coverage percentage per file
- Covered and missed line ranges for quick inspection

---

[← Back to Documentation](index.md)
