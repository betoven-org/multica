# Migracao Odus Task → Multica

## Fase 1 — Subir Multica local
- [ ] Abrir OrbStack/Docker
- [ ] `docker compose -f docker-compose.selfhost.yml up -d`
- [ ] Acessar http://localhost:3000
- [ ] Criar conta admin
- [ ] Criar workspaces: "Wave Commerce" e "Odus Commerce"

## Fase 2 — Configurar workspaces e agents
- [ ] Criar agents: Claude Code (executor principal)
- [ ] Configurar repos dos clients (COOK, Eletrotrafo)
- [ ] Criar projects por client com repo linkado
- [ ] Instalar CLI: `brew install multica-ai/tap/multica`
- [ ] `multica setup self-host`
- [ ] `multica daemon start`

## Fase 3 — Migrar dados do Odus Task
Dados a migrar do banco Postgres atual:

| Odus Task | Multica |
|-----------|---------|
| Organization → | Workspace |
| Client → | Project |
| Task → | Issue |
| Comment → | Issue comment |
| Label → | Label |
| Board/Column → | Board status |
| TimeEntry → | (custom field ou integracao) |
| Trace → | Execution log (nativo) |
| Skill → | Skill (nativo no Multica) |
| Knowledge → | (migrar pro Mem0 direto) |

Script de migracao:
- [ ] Exportar tasks do Odus Task (API ou banco direto)
- [ ] Criar issues no Multica via API
- [ ] Migrar comentarios
- [ ] Migrar labels

## Fase 4 — Integrar o motor (scripts/pi/)
O motor construido no Odus Task e independente:

| Modulo | Como integra no Multica |
|--------|------------------------|
| intake.py | Skill do agent — roda antes do executor |
| browser.py | Tool do daemon — expoe navigate/screenshot/measure |
| verify_geometry.py | Skill que roda pos-implementacao |
| memory.py | Extension do agent — injeta/grava memorias |
| claude_code_llm.py | Helper interno do memory |

Opcoes de integracao:
1. **Skills Multica**: intake e verify viram skills que o agent recebe
2. **Custom MCP server**: browser.py vira MCP server local que o daemon expoe
3. **Autopilot**: verify roda como autopilot pos-PR

## Fase 5 — Integracoes
- [ ] Configurar Slack (substitui Tarefy?)
- [ ] GitHub integration (repos da Wave Commerce)
- [ ] Configurar review gates (PR precisa aprovacao humana)

## Fase 6 — Deploy em prod
- [ ] Subir no servidor (169.58.29.233) ou Coolify
- [ ] Migrar DNS: task.oduscommerce.com.br → Multica
- [ ] Desligar Odus Task antigo

## O que NAO migrar
- Experience, Policy, Experiment, AutonomyLevel (prematuros)
- Crons de shadow mode
- Pipeline shell (odus-task.sh ja deletado)
- 51 models Prisma → Multica tem schema proprio

## Ordem de prioridade
1. Subir local e testar (hoje)
2. Configurar agents e rodar 1 task (amanha)
3. Migrar tasks da COOK
4. Integrar motor como skills
5. Deploy prod
