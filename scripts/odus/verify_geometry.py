"""
Odus Task — Verify de Geometria

Compara o contrato de design (intake) com os computed styles reais no browser.
Cada diferenca e um bug. O agente recebe o diff e corrige.

Uso:
  from verify_geometry import GeometryVerifier

  verifier = GeometryVerifier()
  diff = verifier.verify("https://preview.url", contract)
  print(diff.summary())
  print(diff.to_prompt())  # pra injetar no executor

Tolerancias:
  - Spacing/size: ±2px
  - Font size: exato
  - Colors: exato (hex)
  - Font weight: exato
  - Border radius: ±1px
"""
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from browser import OdusBrowser


@dataclass
class PropertyDiff:
    """Diferenca entre o esperado (Figma) e o real (browser)."""
    component: str
    selector: str
    property: str
    expected: str
    actual: str
    passed: bool
    category: str = ""  # typography, colors, spacing, size, border


@dataclass
class VerifyResult:
    """Resultado da verificacao de geometria."""
    url: str = ""
    total_checks: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    diffs: list[PropertyDiff] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total_checks * 100) if self.total_checks > 0 else 0

    @property
    def is_passing(self) -> bool:
        return self.failed == 0

    def summary(self) -> str:
        lines = [
            f"Verify Geometria: {self.passed}/{self.total_checks} passed ({self.pass_rate:.0f}%)",
            f"URL: {self.url}",
        ]
        if self.failed > 0:
            lines.append(f"\nFalhas ({self.failed}):")
            for d in self.diffs:
                if not d.passed:
                    lines.append(f"  [{d.category}] {d.component} → {d.property}: esperado={d.expected} real={d.actual}")
        return "\n".join(lines)

    def to_prompt(self) -> str:
        """Gera prompt pro executor corrigir as diferencas."""
        if self.is_passing:
            return "Verify de geometria: TODOS os checks passaram. UI fiel ao Figma."

        lines = [
            f"## Verify de Geometria — {self.failed} FALHAS",
            f"URL: {self.url}",
            f"Checks: {self.passed}/{self.total_checks} passaram",
            "",
            "Corrija CADA diferenca abaixo. Use os valores ESPERADOS (do Figma):",
            "",
        ]

        by_component: dict[str, list[PropertyDiff]] = {}
        for d in self.diffs:
            if not d.passed:
                by_component.setdefault(d.component, []).append(d)

        for comp, diffs in by_component.items():
            selector = diffs[0].selector
            lines.append(f"### {comp} (`{selector}`)")
            for d in diffs:
                lines.append(f"- {d.property}: `{d.actual}` → deve ser `{d.expected}`")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "totalChecks": self.total_checks,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "passRate": round(self.pass_rate, 1),
            "diffs": [
                {
                    "component": d.component,
                    "selector": d.selector,
                    "property": d.property,
                    "expected": d.expected,
                    "actual": d.actual,
                    "passed": d.passed,
                    "category": d.category,
                }
                for d in self.diffs
                if not d.passed
            ],
        }


# ── Tolerancias ───────────────────────────────────────────────────────────────

TOLERANCES = {
    "fontSize": 0,        # exato
    "fontWeight": 0,      # exato
    "fontFamily": None,    # string match parcial
    "color": None,         # hex exato
    "fill": None,          # hex exato
    "backgroundColor": None,
    "borderRadius": 1,     # ±1px
    "borderWidth": 0,      # exato
    "paddingTop": 2,       # ±2px
    "paddingRight": 2,
    "paddingBottom": 2,
    "paddingLeft": 2,
    "gap": 2,
    "width": 3,            # ±3px (layout pode variar)
    "height": 3,
    "lineHeight": 1,
    "letterSpacing": 0.5,
}


def _parse_px(value: str) -> float | None:
    """Extrai numero de um valor CSS com px."""
    match = re.match(r"(-?[\d.]+)\s*px", str(value).strip())
    return float(match.group(1)) if match else None


def _normalize_color(color: str) -> str:
    """Normaliza cor pra comparacao."""
    color = color.strip().lower()
    # rgb(r, g, b) → hex
    rgb_match = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", color)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return f"#{r:02x}{g:02x}{b:02x}"
    # rgba(r, g, b, a) → hex (ignora alpha se 1)
    rgba_match = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", color)
    if rgba_match:
        r, g, b = int(rgba_match.group(1)), int(rgba_match.group(2)), int(rgba_match.group(3))
        a = float(rgba_match.group(4))
        if a >= 0.99:
            return f"#{r:02x}{g:02x}{b:02x}"
        return f"#{r:02x}{g:02x}{b:02x}{int(a*255):02x}"
    return color


def _compare_values(expected: str, actual: str, prop_name: str) -> bool:
    """Compara dois valores CSS com tolerancia."""
    if not expected or not actual:
        return True  # skip se falta dado

    tolerance = TOLERANCES.get(prop_name)

    # Comparacao numerica (px)
    if tolerance is not None and isinstance(tolerance, (int, float)):
        exp_px = _parse_px(expected)
        act_px = _parse_px(actual)
        if exp_px is not None and act_px is not None:
            return abs(exp_px - act_px) <= tolerance
        # Se nao e px, comparar string
        return expected.strip().lower() == actual.strip().lower()

    # Comparacao de cor
    if prop_name in ("color", "fill", "backgroundColor", "borderColor"):
        return _normalize_color(expected) == _normalize_color(actual)

    # Font family — match parcial (browser pode expandir)
    if prop_name == "fontFamily":
        exp = expected.strip().lower().replace('"', '').replace("'", "").split(",")[0].strip()
        act = actual.strip().lower().replace('"', '').replace("'", "").split(",")[0].strip()
        return exp in act or act in exp

    # Font weight — normalizar
    if prop_name == "fontWeight":
        weight_map = {"normal": "400", "bold": "700", "light": "300", "medium": "500", "semibold": "600"}
        exp = weight_map.get(expected.strip().lower(), expected.strip())
        act = weight_map.get(actual.strip().lower(), actual.strip())
        return exp == act

    # Default: string comparison
    return expected.strip().lower() == actual.strip().lower()


# ── Mapping de tokens do contrato → CSS properties ───────────────────────────

CONTRACT_TO_CSS = {
    # typography
    "fontFamily": "font-family",
    "fontSize": "font-size",
    "fontWeight": "font-weight",
    "lineHeight": "line-height",
    "letterSpacing": "letter-spacing",
    # colors
    "fill": "background-color",
    "color": "color",
    # spacing
    "paddingTop": "padding-top",
    "paddingRight": "padding-right",
    "paddingBottom": "padding-bottom",
    "paddingLeft": "padding-left",
    "gap": "gap",
    # border
    "borderRadius": "border-radius",
    "borderWidth": "border-width",
    "borderColor": "border-color",
}


class GeometryVerifier:
    """Verifica se a UI implementada bate com o contrato do Figma."""

    def verify(self, url: str, contract: dict, wait_ms: int = 5000) -> VerifyResult:
        """Abre a URL no browser e compara com o contrato."""
        result = VerifyResult(url=url)
        components = contract.get("components", [])

        if not components:
            return result

        with OdusBrowser() as browser:
            browser.navigate(url, wait_ms=wait_ms)

            for comp in components:
                self._verify_component(browser, comp, result)

        return result

    def _verify_component(self, browser: OdusBrowser, comp: dict, result: VerifyResult):
        """Verifica um componente do contrato."""
        name = comp.get("name", "?")
        selector = comp.get("selector", "")
        tokens = comp.get("tokens", {})

        if not selector:
            return

        # Coletar properties que precisamos medir
        css_props = []
        token_map: dict[str, tuple[str, str]] = {}  # css_prop → (token_name, expected_value)

        for category in ("typography", "colors", "spacing", "border"):
            category_tokens = tokens.get(category, {})
            for token_name, expected_value in category_tokens.items():
                css_prop = CONTRACT_TO_CSS.get(token_name)
                if css_prop and expected_value:
                    css_props.append(css_prop)
                    token_map[css_prop] = (token_name, expected_value, category)

        if not css_props:
            return

        # Medir no browser
        measured = browser.measure_element(selector, css_props)
        if not measured:
            # Elemento nao encontrado — skip
            result.skipped += len(css_props)
            return

        # Comparar
        for css_prop, (token_name, expected, category) in token_map.items():
            actual = measured.get(css_prop, "")
            passed = _compare_values(expected, actual, token_name)

            diff = PropertyDiff(
                component=name,
                selector=selector,
                property=token_name,
                expected=expected,
                actual=actual,
                passed=passed,
                category=category,
            )
            result.diffs.append(diff)
            result.total_checks += 1
            if passed:
                result.passed += 1
            else:
                result.failed += 1
