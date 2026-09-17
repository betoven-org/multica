---
name: fix-bug
description: Abordagem de debugging para VTEX IO — vtex link, console, workspace, policies e erros comuns.
---

# Debugging em VTEX IO

Abordagem sistematica para identificar e corrigir bugs em apps VTEX IO.

## Quando usar

- Componente nao renderiza ou renderiza errado.
- Erro 500/400 em GraphQL ou API customizada.
- App nao instala ou nao linka.
- Comportamento inesperado apos deploy.

## Steps

### 1. Verificar o workspace

```bash
# Confirmar workspace atual
vtex whoami

# Listar apps instaladas no workspace
vtex list

# Verificar se a app esta linkada
vtex link --verbose
```

Se o workspace estiver inconsistente, criar um novo:

```bash
vtex use debug-workspace --production false
```

### 2. Inspecionar logs do vtex link

O terminal do `vtex link` mostra erros de build e runtime:

```bash
vtex link 2>&1 | tee link-output.log
```

Erros comuns no link:
- **TypeScript errors** — Corrigir tipos antes de prosseguir.
- **Missing dependency** — Verificar `manifest.json` dependencies.
- **Builder error** — Conferir versao do builder no manifest.

### 3. Console do navegador

Abrir DevTools (F12) e verificar:

- **Console** — Erros React, GraphQL, ou de rede.
- **Network** — Requests falhando (status 4xx/5xx). Filtrar por `graphql` ou `api`.
- **Application > Cookies** — Verificar `VtexIdclientAutCookie` se o problema envolve autenticacao.

### 4. GraphQL debugging

Usar o GraphQL IDE do VTEX:

```
https://{workspace}--{account}.myvtex.com/_v/private/graphql/v1
```

Testar queries isoladamente para confirmar se o problema e no resolver ou no componente React.

### 5. Verificar manifest.json

```bash
# Policies — sem policy de outbound-access, requests externos falham silenciosamente
# Verificar se todas as APIs externas estao listadas
cat manifest.json | grep -A 5 "outbound-access"

# Dependencies — versao errada causa erro de build
cat manifest.json | grep -A 20 "dependencies"

# Builders — builder errado ou ausente causa falha silenciosa
cat manifest.json | grep -A 10 "builders"
```

### 6. Verificar interfaces.json

Se o bloco nao aparece na pagina:

```bash
# O nome do componente deve corresponder ao arquivo em react/
cat store/interfaces.json
ls react/
```

### 7. Logs de backend (node)

```bash
# Ver logs da app em tempo real
vtex logs --app=vendor.app-name --level=error

# Ou todos os níveis
vtex logs --app=vendor.app-name
```

### 8. Comparar com workspace de producao

```bash
# Verificar se o bug existe em producao
vtex use master
# Testar a funcionalidade

# Voltar ao workspace de desenvolvimento
vtex use debug-workspace
```

## Problemas comuns e solucoes

### Componente nao renderiza
- Verificar `interfaces.json` — nome do componente deve corresponder ao arquivo React.
- Verificar se o bloco esta declarado corretamente no tema (blocks.jsonc).
- Verificar console por erros React.

### Erro "Cannot find module"
- Rodar `yarn` na raiz do projeto.
- Verificar `manifest.json` dependencies.
- Limpar cache: `vtex unlink --all && vtex link`.

### GraphQL retorna null
- Verificar se o resolver retorna campos com nomes exatos do schema.
- Verificar logs: `vtex logs --app=vendor.app-name`.
- Testar a query no GraphQL IDE isoladamente.

### Erro 403 em API externa
- Adicionar `outbound-access` policy no `manifest.json`.
- Verificar se o host esta correto (sem protocolo, sem path especifico demais).

### CSS nao aplica
- Verificar se esta usando CSS Handles (nao classes diretas).
- Verificar se o builder `styles` esta no manifest.
- Confirmar que o arquivo CSS esta em `styles/css/vendor.app-name.css`.

### App nao instala
- Verificar compatibilidade de versao no manifest.
- Verificar se todas as peer dependencies estao instaladas.
- Rodar `vtex install vendor.app-name@version --force` para forcar.

## Common mistakes

1. **Debugar em producao** — Sempre usar workspace de desenvolvimento.
2. **Ignorar logs do vtex link** — A maioria dos erros aparece ali primeiro.
3. **Nao testar GraphQL isoladamente** — Misturar debugging de frontend e backend atrasa a resolucao.
4. **Esquecer de rodar yarn** — Dependencias desatualizadas causam erros confusos.
5. **Nao verificar policies** — Requests externos falham silenciosamente sem outbound-access.
