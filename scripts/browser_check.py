"""Run browser acceptance on a temporary dataset; optionally update README screenshots."""
import argparse
import os
from pathlib import Path
from socket import socket
from subprocess import Popen
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def wait_for_server(base, server):
    deadline = monotonic() + 15
    while monotonic() < deadline and server.poll() is None:
        try:
            with urlopen(base + "/health", timeout=1):
                return
        except URLError:
            sleep(0.15)
    raise RuntimeError("The demo server did not start")


def verify(base, screenshots, chromium):
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chromium)
        page = browser.new_page(viewport={"width": 1440, "height": 920}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))

        def snapshot(name):
            if screenshots:
                page.screenshot(path=ROOT / "docs/assets" / name, full_page=True, animations="disabled")

        page.goto(base + "/")
        expect(page.get_by_role("heading", name="Executive overview")).to_be_visible()
        expect(page.get_by_role("button", name="April,", exact=False)).to_be_visible()
        expect(page.get_by_text("One product is behind its freshness target")).to_be_visible()
        snapshot("01-overview.png")

        page.get_by_role("button", name="April,", exact=False).focus()
        page.keyboard.press("Enter")
        expect(page.get_by_text("April 2026", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Metro Belt", exact=False)).to_be_visible()
        page.get_by_role("button", name="Metro Belt", exact=False).click()
        expect(page.get_by_label("Service region")).to_have_value("metro")
        expect(page.get_by_text("April 2026", exact=True)).to_be_visible()
        page.get_by_label("End month").select_option("2026-06")
        expect(page.get_by_text("Recognised revenue · Jan – Jun 2026")).to_be_visible()
        page.get_by_label("Calendar year").select_option("2025")
        expect(page.get_by_text("No comparable period").first).to_be_visible()

        page.get_by_role("link", name="Browse products").click()
        expect(page.get_by_role("heading", name="Product catalog")).to_be_visible()
        expect(page.get_by_text("Late publication", exact=True)).to_be_visible()
        snapshot("02-catalog.png")
        page.get_by_role("link", name="Open dashboard").nth(2).click()
        expect(page.get_by_role("heading", name="Service delivery")).to_be_visible()
        page.get_by_label("Performance metric").select_option("visits")
        expect(page.get_by_text("Completed visits · Jan – Sep 2026")).to_be_visible()
        page.get_by_role("link", name="KPI definition", exact=True).click()
        expect(page.get_by_role("heading", name="Completed visits")).to_be_visible()
        expect(page.get_by_text("mart_operations")).to_be_visible()
        snapshot("03-metric-lineage.png")

        page.get_by_role("link", name="Data health", exact=True).click()
        expect(page.get_by_text("3 / 4", exact=True)).to_be_visible()
        expect(page.get_by_text("20 / 20", exact=True)).to_be_visible()
        snapshot("04-data-health.png")

        page.get_by_role("link", name="Requests", exact=True).click()
        expect(page.get_by_role("heading", name="Reconcile bookings with recognised revenue")).to_be_visible()
        snapshot("05-requests.png")
        page.get_by_role("button", name="New request").click()
        page.get_by_label("Request title").fill("Explain warranty reporting")
        page.get_by_label("Business outcome and acceptance evidence").fill(
            "Show which synthetic servicing costs are covered in the agreed monthly close."
        )
        page.get_by_role("button", name="Submit request").click()
        expect(page.get_by_role("heading", name="Explain warranty reporting")).to_be_visible()
        page.get_by_label("Simulated reviewer").select_option("analyst")
        page.get_by_label("Decision rationale").fill("Commercial and Finance reviewed the evidence and agreed the next action.")
        page.get_by_role("button", name="Save decision").click()
        expect(page.get_by_text("Select the assigned independent simulated reviewer.", exact=False)).to_be_visible()
        for state, actor in (("triaged", "product-owner"), ("accepted", "finance-steward"), ("released", "release-manager")):
            page.get_by_label("Simulated reviewer").select_option(actor)
            page.get_by_label("Decision rationale").fill("Commercial and Finance reviewed the evidence and agreed the next action.")
            page.get_by_role("button", name="Save decision").click()
            expect(page.get_by_text(f"IP-5 is now {state}.")).to_be_visible()
        page.reload()
        page.get_by_role("button", name="Explain warranty reporting", exact=False).click()
        expect(page.locator(".request-detail .timeline li")).to_have_count(4)

        page.get_by_role("link", name="Adoption", exact=True).click()
        expect(page.get_by_role("heading", name="Product adoption")).to_be_visible()
        form = page.get_by_role("form", name="finance demo feedback")
        form.get_by_label("Rating").select_option("5")
        form.get_by_role("button", name="Save rating").click()
        expect(form.get_by_text("5.0/5 · 1 submitted")).to_be_visible()
        page.reload()
        expect(form.get_by_text("5.0/5 · 1 submitted")).to_be_visible()
        snapshot("06-adoption.png")

        page.route("**/api/v1/dashboard?*", lambda route: route.fulfill(status=503, json={"detail": "Simulated outage"}))
        page.get_by_role("link", name="Executive overview").click()
        expect(page.get_by_text("Simulated outage")).to_be_visible()
        expect(page.get_by_role("button", name="April,", exact=False)).to_have_count(0)
        page.unroute("**/api/v1/dashboard?*")
        page.get_by_role("button", name="Retry").click()
        expect(page.get_by_role("button", name="April,", exact=False)).to_be_visible()

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1, is_mobile=True, has_touch=True)
        mobile.on("pageerror", lambda error: errors.append(str(error)))
        mobile.goto(base + "/")
        expect(mobile.get_by_role("button", name="April,", exact=False)).to_be_visible()
        assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
        if screenshots:
            mobile.screenshot(path=ROOT / "docs/assets/07-mobile.png", full_page=True, animations="disabled")
        mobile.get_by_role("button", name="Open navigation").click()
        mobile.get_by_role("link", name="Metric dictionary").click()
        expect(mobile.get_by_role("heading", name="Metric dictionary")).to_be_visible()
        mobile.get_by_role("searchbox", name="Search metrics").fill("absence")
        expect(mobile.get_by_role("link", name="Absence rate", exact=True)).to_be_visible()
        assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert not errors, errors
        browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screenshots", action="store_true")
    parser.add_argument("--chromium", help="launch an existing Chromium executable")
    args = parser.parse_args()
    if not (ROOT / "web/dist/index.html").exists():
        parser.error("build the frontend first with npm run build --prefix web")
    with socket() as temporary_socket:
        temporary_socket.bind(("127.0.0.1", 0))
        port = temporary_socket.getsockname()[1]
    with TemporaryDirectory() as runtime:
        env = {**os.environ, "INSIGHTPORTAL_DATA_DIR": runtime, "WAREHOUSE_MODE": "local"}
        server = Popen(
            [sys.executable, "-m", "uvicorn", "insightportal.main:app", "--port", str(port), "--no-access-log"],
            env=env, cwd=ROOT,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            wait_for_server(base, server)
            verify(base, args.screenshots, args.chromium)
        finally:
            server.terminate()
            server.wait(timeout=10)
    print("Desktop and mobile acceptance passed.")


if __name__ == "__main__":
    main()
