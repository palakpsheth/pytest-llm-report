# Test Report

<iframe src="example-report/index.html" style="width: 100%; height: 90vh; border: 1px solid #e2e8f0; border-radius: 0.5rem;" title="Interactive Test Report"></iframe>

!!! info "Direct Link"
    If the embedded report doesn't display correctly, you can [open it in a new tab](example-report/index.html){ target="_blank" }.

This embedded report is a static example that showcases a mix of passed, failed, skipped, xfailed, xpassed, and error results.

## About the Test Report

This report is automatically generated during CI/CD runs and includes:

- **Test Results**: Pass/fail status for all tests
- **Coverage Data**: Per-test coverage information showing which files and lines each test exercises
- **Execution Time**: Duration for each test
- **Error Messages**: Full error details for failed tests

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

---

[← Back to Documentation](index.md)
