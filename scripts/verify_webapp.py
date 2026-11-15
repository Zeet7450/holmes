"""Playwright smoke test for Holmes.

Run with a dev server (pnpm dev) or preview server already running:

    /path/to/playwright-python scripts/verify_webapp.py --url http://localhost:5173

The Anthropic webapp-testing skill uses this pattern: launch Chromium headless,
wait for the app to settle, then test real selectors. Screenshots are written to
docs/screenshots/ if --screenshots is passed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs/screenshots"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:5173")
    parser.add_argument("--screenshots", action="store_true")
    args = parser.parse_args()

    if args.screenshots:
        SHOTS.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    failed: list[str] = []
    checks: list[str] = []

    def check(name: str, condition: bool) -> None:
        checks.append(f"{'PASS' if condition else 'FAIL'}  {name}")
        if not condition:
            errors.append(name)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--use-gl=angle",
                "--use-angle=swiftshader",
            ],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
        page.on("requestfailed", lambda request: failed.append(request.url))

        page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(6500)
        check("app shell mounted", page.locator(".app-shell").count() == 1)
        check("globe canvas is full size", page.evaluate("window.__holmesMap ? window.__holmesMap.getCanvas().height >= 700 : false"))
        check("hero question is visible", "Ask the planet a question." in page.inner_text("body"))
        check("starter cases are visible", page.locator(".cases-strip button").count() >= 5)
        if args.screenshots:
            page.screenshot(path=SHOTS / "verify-hero.png")

        page.get_by_role("button", name="Jakarta scan").click()
        page.wait_for_timeout(1500)
        check("brief opens", page.locator(".brief-headline").count() == 1)
        check("brief headline is populated", len(page.locator(".brief-headline").inner_text()) > 8)
        if args.screenshots:
            page.screenshot(path=SHOTS / "verify-brief.png")

        page.locator('[data-testid="tab-file"]').click()
        page.wait_for_timeout(700)
        check("city file opens", page.locator(".city-title").count() == 1)
        check("uPlot chart renders", page.locator(".chart-wrap canvas").count() == 1)
        check("Then & Now images loaded", page.locator(".compare-frame img").count() >= 2)
        if args.screenshots:
            page.screenshot(path=SHOTS / "verify-city-file.png")

        page.locator('[data-testid="tab-fire"]').click()
        page.wait_for_timeout(600)
        check("fire watch opens", page.locator(".cluster-row").count() > 0)
        check("fire wording is a detection, not a confirmed fire", "not a confirmed" in page.inner_text("body"))

        page.get_by_role("button", name="City index").click()
        page.wait_for_timeout(300)
        check("city index opens", page.locator(".modal-card").count() == 1)
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        page.locator('[data-testid="tab-brief"]').click()
        page.wait_for_timeout(400)
        page.locator(".chat-input").fill("Where is rainfall falling?")
        page.keyboard.press("Enter")
        page.wait_for_timeout(2300)
        check("chat answer produces a brief", "strongest" in page.locator(".brief-headline").inner_text().lower())
        check("URL is shareable state", "place=" in page.url and "w=" in page.url)

        if failed:
            errors.append(f"failed requests: {failed[:3]}")
        browser.close()

    print("\n".join(checks))
    if errors:
        print("\nFAILURES:")
        for error in errors:
            print(" -", error)
        return 1
    print(f"\nOK · {len(checks)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
