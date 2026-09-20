from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import time


@dataclass
class BrowserFinding:
    kind: str
    detail: str
    severity: str = "error"


@dataclass
class BrowserReport:
    url: str
    final_url: str
    title: str
    findings: list[dict] = field(default_factory=list)
    network: list[dict] = field(default_factory=list)
    visible_text: str = ""
    screenshot: str | None = None
    elapsed_ms: int = 0
    ok: bool = False


class BrowserOperator:
    """Chromium inspector used by KRISHNA to observe real frontend behavior."""

    def __init__(self, headless: bool = True, timeout_ms: int = 15000):
        self.headless = headless
        self.timeout_ms = timeout_ms

    @staticmethod
    def summarize_findings(console_errors=None, page_errors=None,
                           failed_requests=None, bad_responses=None) -> list[dict]:
        findings: list[dict] = []
        for item in console_errors or []:
            findings.append(asdict(BrowserFinding("console_error", str(item))))
        for item in page_errors or []:
            findings.append(asdict(BrowserFinding("page_error", str(item), "critical")))
        for item in failed_requests or []:
            findings.append(asdict(BrowserFinding("request_failed", str(item))))
        for item in bad_responses or []:
            findings.append(asdict(BrowserFinding("http_error", str(item))))
        return findings

    def inspect(self, url: str, actions: list[dict] | None = None,
                screenshot_path: str | None = None) -> dict:
        if not url.startswith(("http://", "https://")):
            raise ValueError("browser inspection requires http:// or https:// URL")
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise RuntimeError(
                "Chromium operator unavailable. Install with: "
                "python -m pip install playwright && python -m playwright install chromium"
            ) from exc

        started = time.perf_counter()
        console_errors: list[str] = []
        page_errors: list[str] = []
        failed_requests: list[str] = []
        bad_responses: list[str] = []
        network: list[dict] = []
        actions = actions or []

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome", headless=self.headless)
            except Exception:
                browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            page.set_default_timeout(self.timeout_ms)
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.on("requestfailed", lambda req: failed_requests.append(
                f"{req.method} {req.url} :: {req.failure}"
            ))
            page.on("response", lambda resp: (
                network.append({"url": resp.url, "status": resp.status, "method": resp.request.method}),
                bad_responses.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None,
            ))
            page.goto(url, wait_until="networkidle")

            for action in actions:
                kind = str(action.get("type", "")).lower()
                selector = str(action.get("selector", ""))
                if kind == "click":
                    page.locator(selector).click()
                elif kind == "fill":
                    page.locator(selector).fill(str(action.get("value", "")))
                elif kind == "press":
                    page.locator(selector).press(str(action.get("key", "Enter")))
                elif kind == "wait":
                    page.wait_for_timeout(int(action.get("ms", 500)))
                elif kind:
                    raise ValueError(f"unsupported browser action: {kind}")

            shot = None
            if screenshot_path:
                target = Path(screenshot_path).resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(target), full_page=True)
                shot = str(target)

            visible_text = page.locator("body").inner_text()[:12000]
            report = BrowserReport(
                url=url,
                final_url=page.url,
                title=page.title(),
                findings=self.summarize_findings(
                    console_errors, page_errors, failed_requests, bad_responses
                ),
                network=network[-200:],
                visible_text=visible_text,
                screenshot=shot,
                elapsed_ms=int((time.perf_counter() - started) * 1000),
            )
            report.ok = not report.findings
            browser.close()
            return asdict(report)
