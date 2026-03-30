from __future__ import annotations
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright


def render_report_to_pdf(
    run_id: str,
    frontend_base_url: str,
    out_path: Path,
    timeout_ms: int = 60_000,
) -> Path:
    """
    Opens the Vue report page and prints it to PDF.
    """
    run_id = (run_id or "").strip()
    if not run_id:
        raise ValueError("run_id is required")

    # Ensure folder exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{frontend_base_url.rstrip('/')}/report/{run_id}?print=1"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1240, "height": 1754},  # doesn't matter much for PDF, but stable
            device_scale_factor=1,
        )
        page = context.new_page()

        # Navigate
        page.goto(url, wait_until="networkidle", timeout=timeout_ms)

        # Wait for Vue to mark readiness
        page.wait_for_function("window.__REPORT_READY__ === true", timeout=timeout_ms)

        # Print
        page.pdf(
            path=str(out_path),
            format="A4",
            print_background=True,
            margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
            prefer_css_page_size=True,  # respects @page if you add it
        )

        context.close()
        browser.close()

    return out_path