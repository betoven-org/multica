---
name: deploy
description: Workflow de deploy em VTEX IO — link, publish, deploy, A/B testing e versionamento.
---

# Deploy Workflow em VTEX IO

Fluxo completo de desenvolvimento ate producao, incluindo testes em workspace e A/B testing.

## Quando usar

- Para publicar uma nova versao de app VTEX IO.
- Para promover mudancas de workspace para producao.
- Para configurar A/B testing antes de deploy definitivo.

## Steps

### 1. Desenvolvimento — vtex link

```bash
# Criar workspace de desenvolvimento
vtex use dev-feature-x --production false

# Linkar a app para desenvolvimento
vtex link

# A app roda em hot-reload no workspace
# Acessar: https://dev-feature-x--{account}.myvtex.com
```

### 2. Teste no workspace

Verificar no workspace antes de publicar:

- [ ] Funcionalidade completa (happy path + edge cases).
- [ ] Mobile e desktop.
- [ ] Performance (Lighthouse no workspace).
- [ ] Console sem erros.
- [ ] GraphQL retornando dados corretos.

### 3. Bump de versao

Atualizar versao no `manifest.json` seguindo semver:

```
patch (0.1.0 → 0.1.1): bug fix, ajuste pequeno
minor (0.1.0 → 0.2.0): nova feature, compatível com versao anterior
major (0.1.0 → 1.0.0): breaking change
```

### 4. Publicar — vtex publish

```bash
# Deslinkar antes de publicar
vtex unlink

# Publicar a nova versao (cria release candidate)
vtex publish

# A versao fica disponível como RC (release candidate)
# Nao esta em producao ainda
```

### 5. Instalar no workspace de teste

```bash
# Criar workspace de producao para testes
vtex use qa-feature-x --production true

# Instalar a versao publicada
vtex install vendor.app-name@0.2.0

# Testar no workspace de producao
# Acessar: https://qa-feature-x--{account}.myvtex.com
```

### 6. A/B Testing (opcional mas recomendado)

```bash
# Iniciar A/B test entre master e o workspace
vtex workspace abtest start qa-feature-x

# Monitorar resultados
vtex workspace abtest status

# Finalizar teste quando tiver dados suficientes
vtex workspace abtest finish
```

O A/B test distribui trafego entre o workspace atual (master) e o novo. VTEX calcula automaticamente qual versao performa melhor.

### 7. Deploy — vtex deploy

```bash
# Deploy da versao (marca como stable, nao mais RC)
vtex deploy vendor.app-name@0.2.0
```

O deploy:
- Marca a versao como stable.
- Atualiza automaticamente em todas as contas que usam major range (`0.x`).
- E irreversível — nao da para "undeployar". Correcao requer nova versao.

### 8. Promover workspace (para store-themes)

Se a mudanca e no store-theme (nao numa app), o fluxo e diferente:

```bash
# Criar workspace de producao
vtex use release-v2 --production true

# Instalar/configurar tudo no workspace

# Promover para master (substitui producao)
vtex workspace promote
```

**CUIDADO:** `vtex workspace promote` substitui o master. E irreversível.

### Rollback

Se algo deu errado apos deploy:

```bash
# Para apps: publicar versao anterior corrigida
vtex publish  # com versao patch incrementada
vtex deploy vendor.app-name@0.2.1

# Para store-theme: criar novo workspace e promover
vtex use hotfix --production true
# Reverter mudancas
vtex workspace promote
```

## Fluxo resumido

```
vtex link (dev) → testar → vtex publish → vtex install (qa workspace)
→ testar em producao → A/B test (opcional) → vtex deploy → monitorar
```

## Common mistakes

1. **Publicar sem deslinkar** — `vtex publish` pode falhar se a app esta linkada. Sempre `vtex unlink` antes.
2. **Deploy sem testar em workspace de producao** — Workspace de dev nao e identico a producao. Sempre testar em `--production true`.
3. **Bump de versao errado** — Breaking change com bump de patch causa problemas em quem depende da app.
4. **Promover workspace sem validacao** — `vtex workspace promote` e irreversível. Validar tudo antes.
5. **Esquecer de monitorar pos-deploy** — Verificar logs e metricas por pelo menos 30 minutos apos deploy.
6. **Nao usar A/B test para mudancas grandes** — Mudancas que afetam conversao devem passar por A/B test.
7. **Deploy na sexta-feira** — Evitar deploys antes de finais de semana ou feriados.
