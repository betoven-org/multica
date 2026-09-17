"""
Odus Task — Browser Module

Primitivas de browser pra verify e debugging.
Usa Playwright (sync) direto, sem agent LLM intermediario.

Uso:
  from browser import OdusBrowser

  with OdusBrowser() as b:
      result = b.navigate("https://example.com")
      b.screenshot("/tmp/screenshot.png")
      errors = b.get_console_errors()
      styles = b.measure_element("h1", ["font-size", "color", "margin-top"])
"""
import json
import time
from pathlib import Path
from typing import Optional


class BrowserResult:
    """Resultado de uma navegacao."""
    def __init__(self):
        self.url: str = ""
        self.status: int = 0
        self.console_errors: list[dict] = []
        self.console_warnings: list[dict] = []
        self.network_errors: list[dict] = []
        self.load_time_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "status": self.status,
            "consoleErrors": self.console_errors,
            "consoleWarnings": self.console_warnings,
            "networkErrors": self.network_errors,
            "loadTimeMs": self.load_time_ms,
        }

    @property
    def has_errors(self) -> bool:
        return len(self.console_errors) > 0

    def summary(self) -> str:
        parts = [f"URL: {self.url} ({self.status})"]
        if self.console_errors:
            parts.append(f"Console errors: {len(self.console_errors)}")
            for e in self.console_errors[:5]:
                parts.append(f"  - {e.get('text', '')[:200]}")
        if self.network_errors:
            parts.append(f"Network errors: {len(self.network_errors)}")
            for e in self.network_errors[:5]:
                parts.append(f"  - {e.get('status', '?')} {e.get('url', '')[:150]}")
        if not self.console_errors and not self.network_errors:
            parts.append("Clean (no errors)")
        parts.append(f"Load time: {self.load_time_ms}ms")
        return "\n".join(parts)


class OdusBrowser:
    """Browser headless com Playwright pra verify e debugging."""

    def __init__(self, headless: bool = True, width: int = 1440, height: int = 900):
        self._headless = headless
        self._width = width
        self._height = height
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._result = BrowserResult()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    def start(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self._headless)
        self._context = self._browser.new_context(
            viewport={"width": self._width, "height": self._height},
        )
        self._page = self._context.new_page()
        self._result = BrowserResult()

        # Listeners
        self._page.on("console", self._on_console)
        self._page.on("pageerror", self._on_pageerror)
        self._page.on("response", self._on_response)
        self._page.on("requestfailed", self._on_requestfailed)

    def stop(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = None
        self._pw = None
        self._page = None

    # ── Navegacao ─────────────────────────────────────────────────────────

    def navigate(self, url: str, wait_ms: int = 3000, timeout: int = 30000) -> BrowserResult:
        """Navega pra URL, espera carregar, retorna resultado com erros."""
        self._result = BrowserResult()
        self._result.url = url

        start = time.time()
        try:
            resp = self._page.goto(url, wait_until="networkidle", timeout=timeout)
            self._result.status = resp.status if resp else 0
        except Exception as e:
            self._result.console_errors.append({"type": "navigation", "text": str(e)[:500]})
            self._result.status = 0

        # Espera extra pra JS async
        if wait_ms > 0:
            self._page.wait_for_timeout(wait_ms)

        self._result.load_time_ms = int((time.time() - start) * 1000)
        return self._result

    # ── Screenshots ───────────────────────────────────────────────────────

    def screenshot(self, path: str, full_page: bool = True) -> str | None:
        """Tira screenshot e salva no path. Retorna path ou None."""
        try:
            self._page.screenshot(path=path, full_page=full_page)
            return path if Path(path).exists() else None
        except Exception:
            return None

    def screenshot_element(self, selector: str, path: str) -> str | None:
        """Screenshot de um elemento especifico."""
        try:
            el = self._page.query_selector(selector)
            if el:
                el.screenshot(path=path)
                return path if Path(path).exists() else None
        except Exception:
            pass
        return None

    # ── Medicao de estilos (pra verify de geometria) ──────────────────────

    def measure_element(self, selector: str, properties: list[str]) -> dict | None:
        """Mede computed styles de um elemento.

        Args:
            selector: CSS selector do elemento
            properties: Lista de CSS properties (ex: ["font-size", "color", "padding-top"])

        Returns:
            Dict com {property: valor} ou None se nao encontrou.
        """
        try:
            result = self._page.evaluate(
                """([selector, properties]) => {
                    const el = document.querySelector(selector);
                    if (!el) return null;
                    const styles = window.getComputedStyle(el);
                    const result = {};
                    for (const prop of properties) {
                        result[prop] = styles.getPropertyValue(prop);
                    }
                    // Adicionar bounding box
                    const rect = el.getBoundingClientRect();
                    result['__bbox'] = {
                        x: Math.round(rect.x),
                        y: Math.round(rect.y),
                        width: Math.round(rect.width),
                        height: Math.round(rect.height),
                    };
                    return result;
                }""",
                [selector, properties],
            )
            return result
        except Exception:
            return None

    def measure_all(self, selector: str, properties: list[str]) -> list[dict]:
        """Mede computed styles de TODOS os elementos que batem com o selector."""
        try:
            results = self._page.evaluate(
                """([selector, properties]) => {
                    const els = document.querySelectorAll(selector);
                    return Array.from(els).map(el => {
                        const styles = window.getComputedStyle(el);
                        const result = {};
                        for (const prop of properties) {
                            result[prop] = styles.getPropertyValue(prop);
                        }
                        const rect = el.getBoundingClientRect();
                        result['__bbox'] = {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        };
                        result['__tagName'] = el.tagName.toLowerCase();
                        result['__text'] = el.textContent?.trim()?.substring(0, 100) || '';
                        return result;
                    });
                }""",
                [selector, properties],
            )
            return results or []
        except Exception:
            return []

    def get_page_metrics(self) -> dict:
        """Retorna metricas basicas da pagina (pra debugging)."""
        try:
            return self._page.evaluate("""() => {
                return {
                    title: document.title,
                    url: location.href,
                    bodyHeight: document.body?.scrollHeight || 0,
                    bodyWidth: document.body?.scrollWidth || 0,
                    elementCount: document.querySelectorAll('*').length,
                    imageCount: document.querySelectorAll('img').length,
                    scriptCount: document.querySelectorAll('script').length,
                    hasReactRoot: !!document.querySelector('[data-reactroot], #__next, #root'),
                };
            }""")
        except Exception:
            return {}

    # ── Interacao ─────────────────────────────────────────────────────────

    def click(self, selector: str, timeout: int = 5000) -> bool:
        try:
            self._page.click(selector, timeout=timeout)
            return True
        except Exception:
            return False

    def fill(self, selector: str, value: str, timeout: int = 5000) -> bool:
        try:
            self._page.fill(selector, value, timeout=timeout)
            return True
        except Exception:
            return False

    def get_text(self, selector: str) -> str:
        try:
            el = self._page.query_selector(selector)
            return el.text_content().strip() if el else ""
        except Exception:
            return ""

    def get_html(self, selector: str = "body") -> str:
        try:
            el = self._page.query_selector(selector)
            return el.inner_html() if el else ""
        except Exception:
            return ""

    # ── Getters ───────────────────────────────────────────────────────────

    def get_console_errors(self) -> list[dict]:
        return self._result.console_errors

    def get_network_errors(self) -> list[dict]:
        return self._result.network_errors

    def get_result(self) -> BrowserResult:
        return self._result

    # ── DevTools report (formato compativel com o pipeline) ───────────────

    def devtools_report(self, screenshot_path: str | None = None) -> dict:
        """Gera report no formato que o pipeline espera."""
        report = self._result.to_dict()
        if screenshot_path:
            report["screenshot"] = screenshot_path
        report["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return report

    def save_devtools_report(self, path: str, screenshot_path: str | None = None):
        """Salva report como JSON."""
        report = self.devtools_report(screenshot_path)
        Path(path).write_text(json.dumps(report, indent=2))

    # ── Event handlers ────────────────────────────────────────────────────

    def _on_console(self, msg):
        entry = {"type": msg.type, "text": msg.text[:500]}
        if msg.type == "error":
            self._result.console_errors.append(entry)
        elif msg.type == "warning":
            self._result.console_warnings.append(entry)

    def _on_pageerror(self, error):
        self._result.console_errors.append({"type": "pageerror", "text": str(error)[:500]})

    def _on_response(self, response):
        if response.status >= 400:
            self._result.network_errors.append({
                "url": response.url[:200],
                "status": response.status,
            })

    def _on_requestfailed(self, request):
        self._result.network_errors.append({
            "url": request.url[:200],
            "status": 0,
            "failure": request.failure or "unknown",
        })
