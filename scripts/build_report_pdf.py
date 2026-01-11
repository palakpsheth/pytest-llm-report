#!/usr/bin/env python3
"""Generate PDF from HTML report using Playwright."""

import sys
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: build_report_pdf.py <input.html> <output.pdf>")
        sys.exit(1)

    input_html = Path(sys.argv[1])
    output_pdf = Path(sys.argv[2])

    if not input_html.exists():
        print(f"Error: {input_html} not found")
        sys.exit(1)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright")
        print("Then: python -m playwright install chromium")
        sys.exit(1)

    print(f"Converting {input_html} to PDF...")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Load HTML file
        page.goto(f"file://{input_html.absolute()}")

        # Wait for content to load
        page.wait_for_load_state("networkidle")

        # Generate PDF
        page.pdf(path=str(output_pdf), format="A4", print_background=True)

        browser.close()

    print(f"PDF saved to {output_pdf}")


if __name__ == "__main__":
    main()
