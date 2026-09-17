# Odus Commerce — Plataforma de AI Agents para E-commerce

## O que é

Plataforma de gestão de projetos onde **agentes AI e desenvolvedores humanos colaboram** em tarefas de e-commerce. Baseada no [Multica](https://github.com/multica-ai/multica) (open source), customizada pra agências de e-commerce com ferramentas de design (Figma), verificação visual e memória persistente.

**URL Produção:** https://task.oduscommerce.com.br
**API:** https://api.oduscommerce.com.br
**Banco:** Supabase (PostgreSQL 17 + pgvector, região São Paulo)
**Servidor:** 169.58.29.233 (Coolify, Docker Compose)

---

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                   Coolify (servidor)                 │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   Backend    │  │   Frontend   │  │   Tools    │ │
│  │   (Go)       │  │  (Next.js)   │  │ (FastAPI)  │ │
│  │  porta 8080  │  │  porta 3000  │  │ porta 8090 │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                 │                │        │
│         └─────────┬───────┘                │        │
│                   │                        │        │
│              ┌────┴────┐             ┌─────┴──────┐ │
│              │ Caddy   │             │ Playwright │ │
│              │ (proxy) │             │ Chromium   │ │
│              └────┬────┘             └────────────┘ │
└───────────────────┼─────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
   ┌────┴────┐ ┌────┴────┐ ┌───┴────┐
   │Supabase │ │ Resend  │ │ Figma  │
   │(Postgres)│ │ (email) │ │ (MCP)  │
   └─────────┘ └─────────┘ └────────┘

   ┌─────────────────┐
   │   Seu Mac       │
   │  multica daemon │
   │  (Claude Code)  │
   └─────────────────┘
```

---

## O que entrega

### Para o cliente (member)
- **Board Kanban** pra criar e acompanhar tasks
- **Comentários** em tempo real nas issues
- **Status tracking**: backlog → in progress → review → done
- **Sem acesso** a AI Team, agents, skills, configurações
- **Português brasileiro** como idioma

### Para a agência (owner/admin)
- **6 agentes AI especializados** que executam tasks automaticamente
- **3 squads** com líder que coordena e delega
- **25 skills** de VTEX IO e deco.cx
- **5 quick actions** pra disparar agents com um clique
- **Timesheet automático** com horas contratadas vs realizado
- **Ferramentas de design**: intake do Figma, verificação visual pixel-perfect
- **Memória persistente** entre execuções (Mem0)

---

## Agentes AI

Todos globais — disponíveis em qualquer workspace sem configuração.

| Agente | Modelo | Especialidade | Skills |
|--------|--------|---------------|--------|
| **Dev Assistant** | claude-sonnet-4-6 | Executor principal | 8 VTEX IO |
| **VTEX IO Dev** | claude-sonnet-4-6 | VTEX IO Store Framework | 8 VTEX IO |
| **deco.cx Dev** | claude-sonnet-4-6 | deco.cx (Fresh/Preact) | 10 deco |
| **Layout Agent** | claude-sonnet-4-6 | Figma → código pixel-perfect | 5 cross-stack + intake + verify |
| **Code Reviewer** | claude-sonnet-4-6 | Review de código | 4 review + performance |
| **Pi** | — | Agent minimalista (extensões) | — |

### Squads

| Squad | Líder | Membros | Uso |
|-------|-------|---------|-----|
| **VTEX IO Squad** | Code Reviewer | VTEX IO Dev + Layout Agent | Tasks de lojas VTEX IO |
| **deco.cx Squad** | Code Reviewer | deco.cx Dev + Layout Agent | Tasks de lojas deco.cx |
| **Full Team** | Code Reviewer | Todos os agents | Tasks complexas ou cross-stack |

**Como squads funcionam:**
1. Issue atribuída ao squad → líder (Code Reviewer) é ativado
2. Líder analisa a issue, decide qual agent é melhor
3. Delega via @mention pro agent escolhido
4. Agent executa, faz commit
5. Líder avalia o resultado

---

## Ferramentas (Odus Tools)

Serviço Python (FastAPI) com Playwright headless. Disponível como **MCP tools** que os agents chamam automaticamente.

### Browser
| Tool | Endpoint | O que faz |
|------|----------|-----------|
| `browser_navigate` | POST /browser/navigate | Navega + captura console/network errors |
| `browser_screenshot` | POST /browser/screenshot | Screenshot full-page |
| `browser_measure` | POST /browser/measure | Computed styles de 1 elemento |
| `browser_measure_all` | POST /browser/measure-all | Computed styles de todos que batem |

### Design
| Tool | Endpoint | O que faz |
|------|----------|-----------|
| `intake_extract` | POST /intake/extract | Figma → contrato JSON de tokens |
| `verify_geometry` | POST /verify/geometry | Compara contrato com browser real |

### Memória
| Tool | Endpoint | O que faz |
|------|----------|-----------|
| `memory_search` | POST /memory/search | Busca memórias de execuções anteriores |
| `memory_add` | POST /memory/add | Grava aprendizado (só com evidência) |

### Fluxo do Layout Agent
```
Issue com Figma URL
  → intake_extract (extrai tokens do Figma)
  → Implementa código
  → verify_geometry (compara com contrato)
  → Se diff > 0: corrige e verifica de novo
  → memory_add (se algo deu errado)
  → Commit
```

### Tolerâncias do Verify
- **Cores**: match exato (hex)
- **Font size/weight**: match exato
- **Font family**: match parcial (browser expande)
- **Spacing**: ±2px
- **Size**: ±3px
- **Border radius**: ±1px

---

## Skills

18 skills globais organizadas por stack.

### VTEX IO (8)
| Skill | Quando usar |
|-------|-------------|
| `vtex-io/css-handles` | Estilização de componentes |
| `vtex-io/custom-client` | Clients backend (REST/GraphQL) |
| `vtex-io/deploy` | Deploy, workspace, release |
| `vtex-io/fix-bug` | Investigar e corrigir bugs |
| `vtex-io/graphql-resolver` | Resolvers GraphQL |
| `vtex-io/new-component` | Novo componente React |
| `vtex-io/performance` | Otimização de performance |
| `vtex-io/review` | Code review |

### deco.cx (10)
| Skill | Quando usar |
|-------|-------------|
| `deco/figma-to-deco` | Implementar design do Figma |
| `deco/new-section` | Criar nova section |
| `deco/fix-bug` | Corrigir bugs Fresh/Preact |
| `deco/review` | Code review |
| `deco/images` | Otimização de imagens |
| `deco/cache` | Caching e stale-while-revalidate |
| `deco/seo-sections` | SEO sections e meta tags |
| `deco/ecommerce-qa` | QA de e-commerce |
| `deco/cms-friendly-props` | Props CMS-friendly |
| `deco/performance` | PageSpeed, JS budget, Core Web Vitals |

Cada skill tem:
- **Description**: quando o agent deve usar
- **Main file** (SKILL.md): instrução completa
- **Supporting files**: template da stack como referência

---

## Quick Actions

5 ações rápidas pra disparar agents. Visíveis só pra owner/admin.

| Action | O que faz |
|--------|-----------|
| **Implementar** | Agent implementa a issue completa |
| **Implementar (Figma)** | DE-PARA Figma → código, pixel-perfect |
| **Review** | Revisa diff criticamente |
| **Fix QA** | Roda tsc + eslint e corrige erros |
| **Bug Fix** | Investiga e corrige bug descrito na issue |

---

## Custom Properties

5 propriedades em cada issue, visíveis no board.

| Property | Tipo | Descrição |
|----------|------|-----------|
| **Tempo realizado** | number | Minutos gastos na task |
| **Quality Score** | number | Score 0-100 |
| **Tipo** | select | bug, feature, layout, performance, content, seo, infra, integration |
| **Stack** | select | VTEX IO, deco.cx, Shopify, FastStore, Nuvemshop, Tray |
| **Risco** | select | low, medium, high, critical |

---

## Timesheet

### API
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/timesheet` | POST | Registra tempo numa issue |
| `/api/timesheet` | GET | Lista entries do mês |
| `/api/timesheet/summary` | GET | Realizado vs contratado |

### Horas contratadas
- Configuradas por workspace em Settings > General
- Campo "Contracted hours (monthly)" na UI
- Summary retorna: `total_hours`, `contracted_hours`, `usage_percent`

### Formato
- Duração em `duration_seconds`, exibido como `hh:mm:ss`
- Breakdown por tipo de task

---

## Workspaces e Isolamento

### Modelo
- **1 workspace por cliente** (ex: "cook", "odus")
- **Workspace master "odus"**: onde items globais são definidos
- **Items globais**: agents, skills, squads, quick actions — aparecem em todos os workspaces automaticamente

### Roles
| Role | Permissões |
|------|-----------|
| **owner** | Tudo: settings, members, agents, billing |
| **admin** | Quase tudo (exceto gerenciar owners) |
| **member** | Criar issues, comentar, ver board. Sem AI Team, sem settings |

### Provisionamento
```bash
# Novo workspace já herda tudo do master automaticamente (is_global)
# Só precisa: criar workspace → convidar cliente como member
```

---

## MCP Servers

| MCP | Tools | Vinculado a |
|-----|-------|-------------|
| **figma** | get_design_context, get_screenshot, etc | Dev Assistant, VTEX IO Dev, deco.cx Dev, Layout Agent |
| **odus-tools** | browser_*, intake_*, verify_*, memory_* | Todos os 5 agents |

---

## Deploy

### Stack
| Componente | Tecnologia | Onde |
|-----------|-----------|------|
| Backend | Go (single binary) | Docker, Coolify |
| Frontend | Next.js 16 | Docker, Coolify |
| Tools | Python 3.12, FastAPI, Playwright | Docker, Coolify |
| Banco | PostgreSQL 17 + pgvector | Supabase (São Paulo) |
| Email | Resend | Cloud |
| Daemon | CLI local | Seu Mac |

### Domínios
- `task.oduscommerce.com.br` → frontend (porta 3000)
- `api.oduscommerce.com.br` → backend (porta 8080)

### Deploy automático
- Push na `main` → Coolify auto-deploy via webhook
- Compose file: `compose.yaml`

### Variáveis de ambiente
```
DATABASE_URL=postgres://...@db.nyvawhtunekgdpmeopvn.supabase.co:5432/postgres
JWT_SECRET=<gerado>
RESEND_API_KEY=<resend>
RESEND_FROM_EMAIL=noreply@oduscommerce.com.br
REMOTE_API_URL=http://backend:8080
DO_NOT_TRACK=true
```

---

## Customizações sobre o Multica upstream

| Feature | O que mudou |
|---------|-------------|
| **is_global** | Coluna em agent, skill, quick_action, squad. Queries SQL patched pra incluir `OR is_global = true` |
| **Timesheet** | Tabela time_entry + endpoints + UI (contracted hours em Settings) |
| **pt-BR** | 25 JSONs traduzidos + locale registrado |
| **AI Team escondido** | Sidebar oculta pra role=member |
| **Discord removido** | Sidebar e help menu |
| **Agents renomeados** | "Claude Code" → "Dev Assistant", "Reviewer" → "Code Reviewer" |
| **Odus Tools** | Service Python com MCP server (browser, intake, verify, memory) |
| **Permission private** | Agents e quick actions invisíveis pra members |

---

## Projetos/Clientes

| Cliente | Stack | Workspace |
|---------|-------|-----------|
| COOK ELETRORARO | VTEX IO | cook (20h/mês) |
| Eletrotrafo B2C | deco.cx | odus |
| ESSENZA | VTEX IO | odus |
| Biasá | — | odus |
| YAMAMURA | — | odus |
| BUSON | — | odus |

---

## Daemon (sua máquina)

```bash
# Configurar
multica config set server_url https://api.oduscommerce.com.br
multica config set app_url https://task.oduscommerce.com.br

# Login
multica login

# Iniciar
multica daemon start

# Status
multica daemon status

# Agents detectados: claude, pi
# Workspaces: odus, cook
```

O daemon roda no seu Mac e executa os agents localmente usando Claude Code CLI. Os agents têm acesso ao filesystem, git, e tools via MCP.

---

## Fluxo completo de uma task

```
1. Cliente cria issue no board (task.oduscommerce.com.br/cook)
   └── "Relayout PDP: Primeira dobra"
   └── Cola link do Figma na descrição

2. Owner vê a issue no workspace odus (visão global)
   └── Atribui ao VTEX IO Squad

3. Code Reviewer (líder) é ativado
   └── Lê a issue, analisa o escopo
   └── Delega: @Layout Agent "implementar layout pixel-perfect"

4. Layout Agent é ativado
   └── Chama intake_extract → extrai tokens do Figma
   └── Lê o código atual do repo
   └── Implementa as mudanças
   └── Chama verify_geometry → compara com contrato
   └── Se diff > 0: corrige e verifica de novo
   └── Commit + push

5. Code Reviewer é re-ativado
   └── Revisa o diff
   └── Se OK: marca como done
   └── Se não: delega correção

6. Owner faz merge do PR
   └── Timesheet registrado automaticamente
   └── Quality score calculado
```
