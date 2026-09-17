#!/usr/bin/env python3
"""
Setup producao do Multica — replica toda a configuracao do local pro prod.

Cria: workspace, agents, skills, squads, quick actions, properties, timesheet config.
Marca items como globais no banco.

Uso:
  1. Acessar o Multica em prod e fazer login (pegar o token dos logs)
  2. Rodar:
     python3 scripts/setup-prod.py --url https://api.oduscommerce.com.br --token <TOKEN>

  Ou se ja tiver config local:
     python3 scripts/setup-prod.py --from-local
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills" / "stack-templates"


def api(base_url, token, method, path, data=None, ws_id=""):
    sep = "&" if "?" in path else "?"
    url = f"{base_url}{path}{sep}workspace_id={ws_id}" if ws_id else f"{base_url}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if ws_id:
        req.add_header("X-Workspace-ID", ws_id)
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return {"error": f"{e.code}: {body}"}


def db_exec(sql):
    """Executa SQL no Supabase."""
    r = subprocess.run(
        ["psql", "-h", "db.nyvawhtunekgdpmeopvn.supabase.co", "-U", "postgres", "-d", "postgres",
         "-t", "-A", "-c", sql],
        capture_output=True, text=True, timeout=15,
        env={**__import__("os").environ, "PGPASSWORD": "FdbYVIHIp3TUBNs2"},
    )
    return r.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Setup producao Multica")
    parser.add_argument("--url", default="https://api.oduscommerce.com.br", help="URL do backend")
    parser.add_argument("--token", default="", help="Auth token (do login)")
    parser.add_argument("--from-local", action="store_true", help="Copiar token do config local")
    args = parser.parse_args()

    base_url = args.url
    token = args.token

    if args.from_local:
        config = json.loads(Path.home().joinpath(".multica/config.json").read_text())
        token = config["token"]
        base_url = config.get("server_url", base_url)

    if not token:
        print("Erro: --token obrigatorio ou use --from-local")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Setup Producao Multica")
    print(f"URL: {base_url}")
    print(f"{'='*60}\n")

    # ── 1. Verificar conexao ──
    print("1. Verificando conexao...")
    # O primeiro request pode ser criar workspace se nao existir
    # Vamos listar workspaces
    ws_list = api(base_url, token, "GET", "/api/workspaces")
    if isinstance(ws_list, list):
        print(f"   OK — {len(ws_list)} workspaces")
    else:
        print(f"   Pode ser primeiro acesso. Continuando...")

    # ── 2. Workspace master "odus" ──
    print("\n2. Workspace master...")
    ws = None
    if isinstance(ws_list, list):
        ws = next((w for w in ws_list if w.get("slug") == "odus"), None)

    if not ws:
        ws = api(base_url, token, "POST", "/api/workspaces", {"name": "Odus", "slug": "odus"})
        if "id" in ws:
            print(f"   Criado: odus ({ws['id'][:8]})")
        else:
            print(f"   {ws}")
            # Pode ser que ja existe, listar de novo
            ws_list = api(base_url, token, "GET", "/api/workspaces")
            if isinstance(ws_list, list):
                ws = next((w for w in ws_list if w.get("slug") == "odus"), ws_list[0] if ws_list else None)
    else:
        print(f"   Existe: odus ({ws['id'][:8]})")

    if not ws or "id" not in ws:
        print("   ERRO: nao conseguiu workspace")
        sys.exit(1)

    ws_id = ws["id"]

    # ── 3. Contracted hours no workspace ──
    print("\n3. Contracted hours...")
    db_exec(f"UPDATE workspace SET settings = settings || '{{\"contracted_hours_monthly\": 40}}'::jsonb WHERE id = '{ws_id}'")
    print("   40h/mes configurado")

    # ── 4. Skills ──
    print("\n4. Skills...")
    SKILLS = [
        ("vtex-io/css-handles", "vtex-io", "css-handles", "Use when styling VTEX IO components."),
        ("vtex-io/custom-client", "vtex-io", "custom-client", "Use when creating VTEX IO custom backend clients."),
        ("vtex-io/deploy", "vtex-io", "deploy", "Use when deploying VTEX IO apps."),
        ("vtex-io/fix-bug", "vtex-io", "fix-bug", "Use when fixing bugs in VTEX IO Store Framework."),
        ("vtex-io/graphql-resolver", "vtex-io", "graphql-resolver", "Use when creating GraphQL resolvers in VTEX IO."),
        ("vtex-io/new-component", "vtex-io", "new-component", "Use when creating new React components for VTEX IO."),
        ("vtex-io/performance", "vtex-io", "performance", "Use when optimizing VTEX IO store performance."),
        ("vtex-io/review", "vtex-io", "review", "Use when reviewing VTEX IO code changes."),
        ("deco/figma-to-deco", "deco", "figma-to-deco", "Use when implementing Figma designs in deco.cx."),
        ("deco/new-section", "deco", "new-section", "Use when creating new deco.cx sections."),
        ("deco/fix-bug", "deco", "fix-bug", "Use when fixing bugs in deco.cx."),
        ("deco/review", "deco", "review", "Use when reviewing deco.cx code."),
        ("deco/images", "deco", "images", "Use when working with images in deco.cx."),
        ("deco/cache", "deco", "cache", "Use when implementing caching in deco.cx."),
        ("deco/seo-sections", "deco", "seo-sections", "Use when implementing SEO in deco.cx."),
        ("deco/ecommerce-qa", "deco", "ecommerce-qa", "Use for QA on deco.cx e-commerce."),
        ("deco/cms-friendly-props", "deco", "cms-friendly-props", "Use when making deco.cx sections CMS-friendly."),
        ("deco/performance", "deco", "pagespeed-score-model", "Use when optimizing deco.cx performance."),
        ("odus/design-intake", None, None, "Use when implementing a design from Figma."),
        ("odus/verify-geometry", None, None, "Use after implementing a layout to verify it matches Figma."),
        ("odus/memory", None, None, "Use to recall learnings from previous executions."),
    ]

    ODUS_SKILL_CONTENT = {
        "odus/design-intake": "Extract ALL design tokens from Figma before coding. Use MCP Figma (get_design_context + get_screenshot). Each CSS property must trace back to a Figma token.",
        "odus/verify-geometry": "After implementing, measure computed styles in the browser and compare with Figma values. Colors: exact. Fonts: exact. Spacing: +/-2px. Any mismatch is a bug.",
        "odus/memory": "Search for relevant memories before starting. Store learnings only when something went wrong (human correction, review rejected, verify failed).",
    }

    STACK_TEMPLATES = {"vtex-io": "CLAUDE.vtex-io.md", "deco": "CLAUDE.deco.md"}

    skill_ids = {}
    for skill_name, stack, filename, description in SKILLS:
        # Content
        if stack and filename:
            skill_file = SKILLS_DIR / stack / f"{filename}.md"
            content = skill_file.read_text() if skill_file.exists() else description
        else:
            content = ODUS_SKILL_CONTENT.get(skill_name, description)

        # Supporting files
        files = []
        if stack:
            tpl = STACK_TEMPLATES.get(stack)
            if tpl:
                tpl_file = SKILLS_DIR / tpl
                if tpl_file.exists():
                    files.append({"path": f"references/{tpl}", "content": tpl_file.read_text()})

        result = api(base_url, token, "POST", "/api/skills", {
            "name": skill_name,
            "description": description,
            "content": content,
            "files": files,
        }, ws_id=ws_id)

        if "id" in result:
            skill_ids[skill_name] = result["id"]
            print(f"   {skill_name}: OK")
        else:
            print(f"   {skill_name}: {result.get('error', '?')[:60]}")

    # Mark skills global
    for sid in skill_ids.values():
        db_exec(f"UPDATE skill SET is_global = true WHERE id = '{sid}'")
    print(f"   {len(skill_ids)} skills marcadas como globais")

    # ── 5. Agents ──
    print("\n5. Agents...")
    # Precisamos do runtime_id — vem do daemon quando conectar
    # Por enquanto, criar sem runtime (placeholder)
    # O daemon vai registrar os runtimes quando conectar

    # Checar se daemon ja registrou runtimes
    # Por enquanto, nao criar agents sem runtime — o daemon faz isso
    print("   Agents serao criados quando o daemon conectar.")
    print("   Rode: multica daemon start (apontando pro prod)")
    print("   Depois rode: python3 scripts/setup-prod.py --phase agents")

    # ── 6. Custom Properties ──
    print("\n6. Custom Properties...")
    props = [
        {"name": "Tempo realizado", "type": "number", "description": "Tempo real gasto na task (minutos)"},
        {"name": "Quality Score", "type": "number", "description": "Score de qualidade 0-100"},
        {"name": "Tipo", "type": "select", "config": {"options": [
            {"name": "bug", "color": "#ef4444"}, {"name": "feature", "color": "#3b82f6"},
            {"name": "layout", "color": "#8b5cf6"}, {"name": "performance", "color": "#eab308"},
            {"name": "content", "color": "#22c55e"}, {"name": "seo", "color": "#14b8a6"},
            {"name": "infra", "color": "#6b7280"}, {"name": "integration", "color": "#f97316"},
        ]}},
        {"name": "Stack", "type": "select", "config": {"options": [
            {"name": "VTEX IO", "color": "#ec4899"}, {"name": "deco.cx", "color": "#22c55e"},
            {"name": "Shopify", "color": "#84cc16"}, {"name": "FastStore", "color": "#3b82f6"},
            {"name": "Nuvemshop", "color": "#8b5cf6"}, {"name": "Tray", "color": "#f97316"},
        ]}},
        {"name": "Risco", "type": "select", "config": {"options": [
            {"name": "low", "color": "#22c55e"}, {"name": "medium", "color": "#eab308"},
            {"name": "high", "color": "#f97316"}, {"name": "critical", "color": "#ef4444"},
        ]}},
    ]
    for p in props:
        result = api(base_url, token, "POST", "/api/properties", p, ws_id=ws_id)
        status = "OK" if "id" in result else result.get("error", "?")[:50]
        print(f"   {p['name']}: {status}")

    # ── 7. Projetos de clientes ──
    print("\n7. Projetos...")
    projects = [
        "COOK ELETRORARO", "Eletrotrafo B2C", "ESSENZA",
        "Biasá", "YAMAMURA", "BUSON",
    ]
    for name in projects:
        result = api(base_url, token, "POST", "/api/projects", {"title": name}, ws_id=ws_id)
        status = "OK" if "id" in result else result.get("error", "?")[:50]
        print(f"   {name}: {status}")

    # ── 8. Quick Actions (placeholder — precisa agent_id) ──
    print("\n8. Quick Actions...")
    print("   Serao criadas quando os agents existirem (apos daemon conectar)")

    # ── Resumo ──
    print(f"\n{'='*60}")
    print("Setup concluido!")
    print(f"  Skills: {len(skill_ids)}")
    print(f"  Properties: {len(props)}")
    print(f"  Projects: {len(projects)}")
    print(f"\nProximos passos:")
    print(f"  1. Configurar daemon: multica config set server_url {base_url}")
    print(f"  2. multica config set app_url https://task.oduscommerce.com.br")
    print(f"  3. multica login")
    print(f"  4. multica daemon start")
    print(f"  5. Rodar de novo com --phase agents pra criar agents e squads")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
