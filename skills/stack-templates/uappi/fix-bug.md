---
name: uappi-fix-bug
description: Debugging Uappi storefronts - common issues, session handling, API errors and template leftovers.
---

# Debugging Uappi

## Checklist rapido

1. **PHPSESSID** — o cookie esta sendo enviado? Verificar `plugins/axios.js` (header `Session`).
2. **Endpoint correto** — usar caminho relativo `/v2/front/...`, nunca URL absoluta hardcoded.
3. **`?debug`** — adicionar na URL para ver detalhes do erro da API no front.
4. **`nuxt.config.js`** — a `baseUrl` do axios e o `siteUrl` de settings estao apontando para a loja correta?
5. **`App-Token: wapstore`** — header presente em toda chamada?

## Problemas comuns

### URLs hardcoded de outra loja

O template `loja-modelo-front` pode conter URLs absolutas de outra loja. Locais frequentes:

- `src/plugins/listagem.js` — no `switch`, o `case 'lista'` pode usar URL hardcoded (ex.: `https://www.desincha.com.br/api/...`). Corrigir para caminho relativo.
- `src/store/home.js` — slugs de vitrines de outro nicho.
- `nuxt.config.js` — URL hardcoded alem das envs.

```bash
# Buscar URLs hardcoded no projeto
grep -r "uappi.dev.br" src/ --include="*.js" --include="*.vue" -l
grep -r "desincha\|isaclin\|loja-modelo" src/ --include="*.js" --include="*.vue" -l
```

### Perda de sessao (carrinho sumindo)

- O `PHPSESSID` nao esta sendo propagado entre requests.
- Verificar `plugins/axios.js`: o interceptor de request deve ler o cookie e injetar o header `Session`.
- Verificar se `cookie-universal-nuxt` esta nos modules do `nuxt.config.js`.

### Componente @wapstore nao renderiza

- `build.transpile: ['@wapstore']` esta no `nuxt.config.js`?
- O pacote esta instalado? Verificar `package.json` e `node_modules/@wapstore/`.
- O `.npmrc` tem o token de auth para o registry privado?

### Slug de vitrine/banner retorna vazio

- Slugs sao **por loja** — configurados no painel Uappi.
- O componente faz `.catch` silencioso; se o slug nao existir, nada renderiza.
- Confirmar no painel se o slug esta ativo e com conteudo.

### Erro no SSR (500)

- Verificar `plugins/config.server.js` — falha na `GET /v2/front/settings` quebra o boot.
- Verificar se a API esta acessivel do servidor (DNS, firewall, `extra_hosts` no Docker).
- Verificar `asyncData` da pagina — erros nao tratados geram 500.

### Vuex state undefined

- O modulo esta registrado? Verificar `store/index.js` (modulos @wapstore) e a existencia do arquivo no `store/`.
- Namespace correto? Ex.: `cabecalho/menu` vs `menu` (varia por loja).

### Imagens quebradas

- Middleware `user-agent` define `tipoImg` (WebP vs originais para Mac). Se `tipoImg` esta errado, as URLs de imagem podem nao funcionar.
- Verificar se o `screenWidth` esta sendo setado corretamente (360 mobile / 1366 desktop).

### Lint falhando

```bash
npm run lint       # ver erros
npm run lintfix    # correcao automatica
```

Regras principais: ponto e virgula obrigatorio, aspas simples, self-closing, brace-style Stroustrup.

## Debug da API

```bash
# Verificar tipo de pagina
curl -s "https://www.<loja>.uappi.dev.br/api/v2/front/url/verify?url=/produto-teste" \
  -H "App-Token: wapstore" | jq '.data.nivel'

# Testar settings
curl -s "https://www.<loja>.uappi.dev.br/api/v2/front/settings" \
  -H "App-Token: wapstore" | jq '.data'

# Colecao completa de endpoints
curl -s "https://www.<loja>.uappi.dev.br/api/v2/collection/front" \
  -H "App-Token: wapstore"
```
