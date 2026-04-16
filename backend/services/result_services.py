from __future__ import annotations
from pathlib import Path
from typing import Optional, Any
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

from playwright.sync_api import sync_playwright

#Load plugin registry
def load_plugin_registry(directory: Path) -> dict:
    path = directory / "plugin_registry.json"
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))

#Final Score computation
def clamp_score(score: float) -> float:
    return min(10.0, max(0.0, score))

def compute_total_score(metric_value: Any, user_weight: Any) -> Optional[float]:
    try:
        metric = float(metric_value)
        weight = float(user_weight)

        weighted_score = metric * (weight / 5.0)

        return round(clamp_score(weighted_score), 3)

    except (TypeError, ValueError):
        return None

#generate PDF
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

    out_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{frontend_base_url.rstrip('/')}/report/{run_id}?print=1"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1240, "height": 1754},
                device_scale_factor=1,
            )
            page = context.new_page()

            page.goto(url, wait_until="networkidle", timeout=timeout_ms)

            page.wait_for_function(
                "window.__REPORT_READY__ === true",
                timeout=timeout_ms
            )

            page.wait_for_timeout(300)

            page.pdf(
                path=str(out_path),
                format="A4",
                print_background=True,
                margin={
                    "top": "0mm",
                    "right": "0mm",
                    "bottom": "0mm",
                    "left": "0mm",
                },
                prefer_css_page_size=True,
            )

            context.close()
            browser.close()

        return out_path

    except Exception as e:
        raise RuntimeError(f"Failed while rendering report at {url}: {e}") from e