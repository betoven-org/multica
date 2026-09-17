"""
Odus Task — Design Intake

Extrai design tokens do Figma e gera um contrato estruturado (JSON).
O contrato define exatamente como cada componente deve ser implementado.

Usa Claude Code CLI com MCP Figma (get_design_context) pra extrair.
Fallback pra Figma REST API se FIGMA_TOKEN disponivel.

Uso:
  from intake import DesignIntake

  intake = DesignIntake()
  contract = intake.extract("ruwo58Uwnsi5B1IPGZRLr2", "2337:4783")
  intake.save(contract, "cook-pdp-desktop.json")

Schema do contrato:
  {
    "fileKey": "...",
    "nodeId": "...",
    "nodeName": "...",
    "extractedAt": "...",
    "components": [
      {
        "name": "ProductName",
        "selector": "h1, .productName",
        "tokens": {
          "typography": {"fontFamily": "...", "fontSize": "24px", ...},
          "colors": {"color": "#222", "background": "transparent"},
          "spacing": {"paddingTop": "0px", "marginBottom": "16px", ...},
          "size": {"width": "auto", "height": "auto"},
          "border": {"borderRadius": "0px", ...}
        }
      }
    ],
    "globals": {
      "colors": ["#222", "#666", "#fff", ...],
      "fonts": ["Roboto", "Arial"],
      "breakpoints": {"desktop": 1440, "mobile": 375}
    }
  }
"""
import json
import os
import re
import subprocess
import time
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional


class DesignIntake:
    """Extrai design tokens do Figma e gera contrato."""

    def __init__(self):
        self._figma_token = self._find_figma_token()

    def extract(self, file_key: str, node_id: str) -> dict:
        """Extrai tokens do Figma. Tenta REST API, fallback pra MCP."""
        # Tentar REST API primeiro (mais rapido, sem LLM)
        if self._figma_token:
            result = self._extract_via_rest(file_key, node_id)
            if result and result.get("components"):
                return result

        # Fallback: Claude Code CLI com MCP Figma
        return self._extract_via_mcp(file_key, node_id)

    def save(self, contract: dict, path: str):
        """Salva contrato como JSON."""
        Path(path).write_text(json.dumps(contract, indent=2, ensure_ascii=False))

    # ── REST API extraction ───────────────────────────────────────────────

    def _extract_via_rest(self, file_key: str, node_id: str) -> dict | None:
        """Extrai via Figma REST API direto."""
        try:
            params = f"?ids={urllib.parse.quote(node_id)}&geometry=paths"
            req = urllib.request.Request(
                f"https://api.figma.com/v1/files/{file_key}/nodes{params}",
                headers={"X-FIGMA-TOKEN": self._figma_token},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read())

            nodes = data.get("nodes", {})
            if not nodes:
                return None

            node_data = list(nodes.values())[0]
            doc = node_data.get("document", {})

            return self._process_figma_node(file_key, node_id, doc)

        except Exception:
            return None

    def _process_figma_node(self, file_key: str, node_id: str, doc: dict) -> dict:
        """Processa arvore de nodes do Figma e extrai tokens."""
        contract = {
            "fileKey": file_key,
            "nodeId": node_id,
            "nodeName": doc.get("name", ""),
            "nodeType": doc.get("type", ""),
            "extractedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "components": [],
            "globals": {
                "colors": [],
                "fonts": set(),
            },
        }

        self._walk_node(doc, contract, depth=0)

        # Deduplicate colors
        contract["globals"]["colors"] = list(set(contract["globals"]["colors"]))
        contract["globals"]["fonts"] = list(contract["globals"]["fonts"])

        return contract

    def _walk_node(self, node: dict, contract: dict, depth: int):
        """Recursivamente extrai tokens de cada node."""
        name = node.get("name", "")
        node_type = node.get("type", "")

        # Extrair componente se tem conteudo visual
        if node_type in ("FRAME", "COMPONENT", "INSTANCE", "GROUP", "TEXT", "RECTANGLE", "VECTOR"):
            component = self._extract_component(node)
            if component:
                contract["components"].append(component)

                # Agregar globals
                for color in component["tokens"].get("colors", {}).values():
                    if color and color != "transparent" and color.startswith("#"):
                        contract["globals"]["colors"].append(color)
                font = component["tokens"].get("typography", {}).get("fontFamily")
                if font:
                    contract["globals"]["fonts"].add(font)

        # Recurse children
        for child in node.get("children", []):
            self._walk_node(child, contract, depth + 1)

    def _extract_component(self, node: dict) -> dict | None:
        """Extrai tokens de um node individual."""
        name = node.get("name", "")
        node_type = node.get("type", "")

        tokens: dict = {
            "typography": {},
            "colors": {},
            "spacing": {},
            "size": {},
            "border": {},
            "layout": {},
        }

        # Bounding box → size
        bb = node.get("absoluteBoundingBox", {})
        if bb:
            tokens["size"] = {
                "width": f"{bb.get('width', 0):.0f}px",
                "height": f"{bb.get('height', 0):.0f}px",
            }

        # Typography (TEXT nodes)
        style = node.get("style", {})
        if style:
            tokens["typography"] = {
                "fontFamily": style.get("fontFamily", ""),
                "fontSize": f"{style.get('fontSize', 0)}px",
                "fontWeight": str(style.get("fontWeight", 400)),
                "lineHeight": f"{style.get('lineHeightPx', 0):.1f}px" if style.get("lineHeightPx") else "normal",
                "letterSpacing": f"{style.get('letterSpacing', 0):.2f}px" if style.get("letterSpacing") else "normal",
                "textAlign": style.get("textAlignHorizontal", "LEFT").lower(),
            }

        # Fills → colors
        for fill in node.get("fills", []):
            if fill.get("type") == "SOLID" and "color" in fill:
                c = fill["color"]
                hex_color = f"#{int(c.get('r',0)*255):02x}{int(c.get('g',0)*255):02x}{int(c.get('b',0)*255):02x}"
                opacity = fill.get("opacity", c.get("a", 1))
                if opacity < 1:
                    hex_color += f"{int(opacity*255):02x}"
                tokens["colors"]["fill"] = hex_color

        # Strokes → border color
        for stroke in node.get("strokes", []):
            if stroke.get("type") == "SOLID" and "color" in stroke:
                c = stroke["color"]
                tokens["border"]["borderColor"] = f"#{int(c.get('r',0)*255):02x}{int(c.get('g',0)*255):02x}{int(c.get('b',0)*255):02x}"

        # Stroke weight → border width
        if node.get("strokeWeight"):
            tokens["border"]["borderWidth"] = f"{node['strokeWeight']}px"

        # Corner radius
        if node.get("cornerRadius"):
            tokens["border"]["borderRadius"] = f"{node['cornerRadius']}px"
        elif node.get("rectangleCornerRadii"):
            radii = node["rectangleCornerRadii"]
            tokens["border"]["borderRadius"] = " ".join(f"{r}px" for r in radii)

        # Padding/spacing (auto-layout)
        if "paddingLeft" in node:
            tokens["spacing"] = {
                "paddingTop": f"{node.get('paddingTop', 0)}px",
                "paddingRight": f"{node.get('paddingRight', 0)}px",
                "paddingBottom": f"{node.get('paddingBottom', 0)}px",
                "paddingLeft": f"{node.get('paddingLeft', 0)}px",
            }
        if "itemSpacing" in node:
            tokens["spacing"]["gap"] = f"{node['itemSpacing']}px"

        # Layout mode
        if "layoutMode" in node:
            tokens["layout"] = {
                "display": "flex",
                "flexDirection": "column" if node["layoutMode"] == "VERTICAL" else "row",
                "alignItems": self._map_align(node.get("counterAxisAlignItems", "")),
                "justifyContent": self._map_justify(node.get("primaryAxisAlignItems", "")),
            }

        # Efeitos (shadows)
        for effect in node.get("effects", []):
            if effect.get("type") == "DROP_SHADOW" and effect.get("visible", True):
                c = effect.get("color", {})
                tokens["border"]["boxShadow"] = (
                    f"{effect.get('offset', {}).get('x', 0)}px "
                    f"{effect.get('offset', {}).get('y', 0)}px "
                    f"{effect.get('radius', 0)}px "
                    f"rgba({int(c.get('r',0)*255)},{int(c.get('g',0)*255)},{int(c.get('b',0)*255)},{c.get('a',1):.2f})"
                )

        # Limpar tokens vazios
        tokens = {k: v for k, v in tokens.items() if v}

        if not tokens:
            return None

        # Text content
        characters = node.get("characters", "")

        return {
            "name": name,
            "type": node_type,
            "characters": characters[:100] if characters else "",
            "selector": self._suggest_selector(name, node_type),
            "tokens": tokens,
        }

    @staticmethod
    def _suggest_selector(name: str, node_type: str) -> str:
        """Sugere um CSS selector baseado no nome do node."""
        # Converter CamelCase/PascalCase pra kebab-case
        slug = re.sub(r"([A-Z])", r"-\1", name).lower().strip("-")
        slug = re.sub(r"[^a-z0-9-]", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")

        if node_type == "TEXT":
            return f".{slug}, [class*='{slug}']"
        return f".{slug}"

    @staticmethod
    def _map_align(value: str) -> str:
        return {"MIN": "flex-start", "CENTER": "center", "MAX": "flex-end", "BASELINE": "baseline"}.get(value, "stretch")

    @staticmethod
    def _map_justify(value: str) -> str:
        return {"MIN": "flex-start", "CENTER": "center", "MAX": "flex-end", "SPACE_BETWEEN": "space-between"}.get(value, "flex-start")

    # ── MCP extraction (fallback) ─────────────────────────────────────────

    def _extract_via_mcp(self, file_key: str, node_id: str) -> dict:
        """Fallback: retorna contrato vazio com instrucoes pro executor.
        O executor (interativo, com MCP) faz a extracao de verdade."""
        return {
            "fileKey": file_key,
            "nodeId": node_id,
            "nodeName": "",
            "extractedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "components": [],
            "globals": {"colors": [], "fonts": []},
            "pendingExtraction": True,
        }

    @staticmethod
    def build_intake_prompt(file_key: str, node_id: str) -> str:
        """Gera prompt pra o executor extrair tokens via MCP Figma."""
        return f"""ANTES de implementar, extraia os design tokens do Figma.

Use get_design_context e get_screenshot do MCP Figma:
- FileKey: {file_key}
- NodeId: {node_id}

Extraia TODOS os tokens visuais de cada elemento:
1. Typography: fontFamily, fontSize, fontWeight, lineHeight, letterSpacing
2. Colors: fills (hex), strokes, text color
3. Spacing: padding, margin, gap (de auto-layout)
4. Size: width, height
5. Border: borderRadius, borderWidth, borderColor
6. Effects: boxShadow

Liste o DE-PARA completo entre o design e o codigo atual.
Implemente usando APENAS os valores extraidos do Figma.
NAO invente valores — cada propriedade CSS deve vir do Figma."""

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _get_mcp_config_file() -> str:
        """Gera arquivo temporario com mcpServers do settings.json."""
        settings_path = Path.home() / ".claude" / "settings.json"
        if not settings_path.exists():
            return ""
        try:
            settings = json.loads(settings_path.read_text())
            servers = settings.get("mcpServers", {})
            if not servers:
                return ""
            import tempfile
            tmp = tempfile.mktemp(suffix=".json", prefix="odus-mcp-")
            Path(tmp).write_text(json.dumps({"mcpServers": servers}))
            return tmp
        except Exception:
            return ""

    @staticmethod
    def _find_figma_token() -> str:
        """Busca Figma token no env ou settings.json."""
        token = os.environ.get("FIGMA_TOKEN", "")
        if token:
            return token

        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text())
                token = settings.get("env", {}).get("FIGMA_TOKEN", "")
                if token:
                    return token
                # Tentar no mcpServers
                for srv in settings.get("mcpServers", {}).values():
                    if isinstance(srv, dict):
                        token = srv.get("env", {}).get("FIGMA_API_KEY", "") or srv.get("env", {}).get("FIGMA_TOKEN", "")
                        if token:
                            return token
            except Exception:
                pass

        return ""


def parse_figma_url(url: str) -> tuple[str, str]:
    """Extrai fileKey e nodeId de uma URL do Figma."""
    file_match = re.search(r"/design/([^/]+)", url)
    node_match = re.search(r"node-id=([^&]+)", url)
    file_key = file_match.group(1) if file_match else ""
    node_id = node_match.group(1).replace("-", ":") if node_match else ""
    return file_key, node_id
