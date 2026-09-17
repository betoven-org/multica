#!/usr/bin/env python3
"""
Provisiona um workspace de cliente com agents, skills, quick actions e project.

Uso:
  python3 scripts/provision-workspace.py <workspace_slug> --stack "VTEX IO" --client "COOK ELETRORARO"

Copia tudo do workspace base (odus) pra funcionar igual:
- Agents: Claude Code + Pi (mesmos runtimes do daemon)
- Skills: da stack especificada
- Quick Actions: Implementar, Review, Fix QA, Bug Fix, Implementar Figma
- Project: com nome do cliente
- Instructions: template CLAUDE.{stack}.md no agent

O daemon compartilha runtimes entre workspaces automaticamente.
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills" / "stack-templates"
API_BASE = "http://localhost:8080"


def load_config():
    return json.loads(Path.home().joinpath(".multica/config.json").read_text())


def api(method, path, data=None, token="", ws_id=""):
    sep = "&" if "?" in path else "?"
    url = f"{API_BASE}{path}{sep}workspace_id={ws_id}" if ws_id else f"{API_BASE}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if ws_id:
        req.add_header("X-Workspace-ID", ws_id)
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read())
            return {"error": body.get("error", str(e))}
        except Exception:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def get_daemon_runtimes():
    """Le runtime IDs do daemon log."""
    log_path = Path.home() / ".multica" / "daemon.log"
    runtimes = {}
    if log_path.exists():
        for line in log_path.read_text().split("\n"):
            if "registered runtime" in line and "provider=" in line:
                rt_match = re.search(r"runtime_id=(\S+)", line)
                prov_match = re.search(r"provider=(\S+)", line)
                if rt_match and prov_match:
                    runtimes[prov_match.group(1)] = rt_match.group(1)
    return runtimes


def find_workspace(token, slug):
    """Encontra workspace por slug."""
    result = api("GET", "/api/workspaces", token=token)
    workspaces = result if isinstance(result, list) else result.get("workspaces", [])
    return next((w for w in workspaces if w.get("slug") == slug), None)


def stack_slug(stack):
    return stack.lower().replace(" ", "-").replace(".", "-")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Provisiona workspace de cliente")
    parser.add_argument("slug", help="Slug do workspace (ex: cook-eletroraro)")
    parser.add_argument("--stack", default="VTEX IO", help="Stack do cliente (ex: 'VTEX IO', 'deco.cx')")
    parser.add_argument("--client", default="", help="Nome do cliente (ex: 'COOK ELETRORARO')")
    args = parser.parse_args()

    config = load_config()
    token = config["token"]

    # 1. Encontrar workspace
    ws = find_workspace(token, args.slug)
    if not ws:
        print(f"Workspace '{args.slug}' nao encontrado.")
        print("Crie primeiro na UI (http://localhost:3000) e rode este script depois.")
        sys.exit(1)

    ws_id = ws["id"]
    ws_name = ws.get("name", args.slug)
    print(f"\n{'='*50}")
    print(f"Provisionando: {ws_name} ({args.slug})")
    print(f"Stack: {args.stack}")
    print(f"{'='*50}\n")

    # 2. Runtimes do daemon
    runtimes = get_daemon_runtimes()
    claude_rt = runtimes.get("claude", "")
    pi_rt = runtimes.get("pi", "")

    if not claude_rt:
        print("ERRO: daemon nao tem runtime Claude. Rode: multica daemon start")
        sys.exit(1)

    print(f"Runtimes: claude={claude_rt[:12]} pi={pi_rt[:12] if pi_rt else 'N/A'}")

    # 3. Instructions da stack
    ss = stack_slug(args.stack)
    instructions = ""
    template_file = SKILLS_DIR / f"CLAUDE.{ss}.md"
    if template_file.exists():
        instructions = template_file.read_text()

    # 4. Criar agents
    print("\n--- Agents ---")
    claude_agent_id = ""

    result = api("POST", "/api/agents", {
        "name": "Claude Code",
        "runtime_id": claude_rt,
        "model": "claude-sonnet-4-6",
        "description": f"Executor principal — {args.stack}",
        "instructions": instructions,
        "visibility": "workspace",
    }, token=token, ws_id=ws_id)
    if "id" in result:
        claude_agent_id = result["id"]
        print(f"  Claude Code: OK ({claude_agent_id[:8]})")
        if instructions:
            print(f"  Instructions: {template_file.name} ({len(instructions)} chars)")
    else:
        print(f"  Claude Code: {result.get('error', '?')}")

    if pi_rt:
        result = api("POST", "/api/agents", {
            "name": "Pi",
            "runtime_id": pi_rt,
            "description": "Agent com extensoes Odus (intake, verify, memory)",
            "visibility": "workspace",
        }, token=token, ws_id=ws_id)
        if "id" in result:
            print(f"  Pi: OK ({result['id'][:8]})")
        else:
            print(f"  Pi: {result.get('error', '?')}")

    # 5. Skills da stack
    print("\n--- Skills ---")
    skills_path = SKILLS_DIR / ss
    skill_count = 0
    if skills_path.exists():
        for skill_file in sorted(skills_path.glob("*.md")):
            name = f"{ss}/{skill_file.stem}"
            content = skill_file.read_text()
            result = api("POST", "/api/skills", {
                "name": name,
                "content": content,
            }, token=token, ws_id=ws_id)
            if "id" in result:
                skill_count += 1
            else:
                print(f"  {name}: {result.get('error', '?')}")
        print(f"  {skill_count} skills de {args.stack}")
    else:
        print(f"  Nenhuma skill pra '{args.stack}'")

    # 6. Quick Actions
    print("\n--- Quick Actions ---")
    if claude_agent_id:
        actions = [
            {
                "name": "Implementar",
                "description": "Executor implementa a issue completa",
                "prompt": "Implemente a task descrita nesta issue. Leia os arquivos relevantes, implemente, e faca commit quando terminar. NAO faca push.",
                "assignee_type": "agent",
                "assignee_id": claude_agent_id,
                "visibility": "public",
            },
            {
                "name": "Implementar (Figma)",
                "description": "Layout pixel-perfect a partir do Figma",
                "prompt": "ANTES de codar, faca o DE-PARA entre o Figma e o codigo atual. Use o MCP Figma (get_screenshot + get_design_context) pra extrair TODOS os tokens visuais. Implemente usando APENAS valores do Figma. Faca commit.",
                "assignee_type": "agent",
                "assignee_id": claude_agent_id,
                "visibility": "public",
            },
            {
                "name": "Review",
                "description": "Revisar codigo criticamente",
                "prompt": "Revise o diff desta branch criticamente. Checklist: sem console.log, sem any, sem inline styles, sem imports nao usados, sem vulnerabilidades. Liste cada problema.",
                "assignee_type": "agent",
                "assignee_id": claude_agent_id,
                "visibility": "public",
            },
            {
                "name": "Fix QA",
                "description": "Corrigir erros de types/lint/tests",
                "prompt": "Rode tsc --noEmit e eslint. Corrija TODOS os erros. Mantenha a logica original. Faca commit.",
                "assignee_type": "agent",
                "assignee_id": claude_agent_id,
                "visibility": "public",
            },
            {
                "name": "Bug Fix",
                "description": "Investigar e corrigir bug",
                "prompt": "Investigue o bug descrito nesta issue. Encontre a causa raiz, implemente o fix. Faca commit.",
                "assignee_type": "agent",
                "assignee_id": claude_agent_id,
                "visibility": "public",
            },
        ]
        qa_count = 0
        for action in actions:
            result = api("POST", "/api/quick-actions", action, token=token, ws_id=ws_id)
            if "id" in result:
                qa_count += 1
            else:
                print(f"  {action['name']}: {result.get('error', '?')}")
        print(f"  {qa_count} quick actions")
    else:
        print("  Pulado (sem agent Claude Code)")

    # 7. Criar project do cliente
    print("\n--- Project ---")
    client_name = args.client or ws_name
    result = api("POST", "/api/projects", {
        "title": client_name,
        "description": f"Stack: {args.stack}",
    }, token=token, ws_id=ws_id)
    if "id" in result:
        print(f"  {client_name}: OK ({result['id'][:8]})")
    else:
        print(f"  {client_name}: {result.get('error', '?')}")

    # Resumo
    print(f"\n{'='*50}")
    print(f"Workspace '{args.slug}' provisionado!")
    print(f"  Agents: Claude Code + Pi")
    print(f"  Skills: {skill_count} ({args.stack})")
    print(f"  Quick Actions: 5")
    print(f"  Project: {client_name}")
    print(f"  URL: http://localhost:3000/{args.slug}")
    print(f"{'='*50}\n")
    print("Proximo passo: convidar o cliente pro workspace na UI (Settings > Members)")


if __name__ == "__main__":
    main()
