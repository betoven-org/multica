---
name: uappi-platform
description: Uappi/wapstore platform overview - Nuxt 2 + Vue 2 SSR storefront architecture.
---

# Uappi / wapstore Platform

## Stack

- **Nuxt 2 + Vue 2** com SSR (`ssr: true`).
- Pacotes `@wapstore/*` auto-importados e transpilados (`build.transpile: ['@wapstore']`).
- `srcDir: 'src/'` — todo codigo-fonte em `src/`.
- `.env` fica em `src/.env` (nao na raiz).
- API: `https://www.<loja>.uappi.dev.br/api` com header `App-Token: wapstore`.

## Como reconhecer um projeto Uappi

- `package.json` com `@wapstore/*` e `name: "loja-modelo-front"`.
- `nuxt: ^2.x`, `vue: ^2.6.x`.
- Arquivo `src/.env` com `SITE_URL`, `SUB_DOMAIN_URL`, `WAP_API_URL`.

## Comandos

```bash
npm install        # instalar dependencias
npm run dev        # dev com hot reload localhost:3000
npm run build      # build de producao
npm run start      # servidor de producao
npm run lint       # checa lint
npm run lintfix    # corrige lint
```

## Estrutura de diretorios

```
src/
  components/       # auto-registrados com prefixo camelCase do subdir
  layouts/          # default.vue (scroll lazy, GTM, dados estruturados)
  middleware/       # user-agent.js, loader.js
  pages/            # _produto.vue (catch-all), index.vue, etc
  plugins/          # axios.js, listagem.js, config.server.js, etc
  static/css/       # variaveis-globais.css, geral.css, reset.css
  store/            # Vuex modules (index, home, categoria, listagem, etc)
  .env              # variaveis de ambiente
nuxt.config.js      # config async (busca /v2/front/settings antes de montar)
```

## Fluxo de inicializacao

1. `nuxt.config.js` (async) faz `GET /v2/front/settings` e injeta `window.config` no head.
2. Plugin `config.server.js` busca settings no SSR e faz `setConfig`.
3. Middlewares globais: `user-agent` define `screenWidth`/`tipoImg`; `loader` controla loading.
4. `pages/_produto.vue` resolve a pagina via `/v2/front/url/verify?url=<path>`.
5. `layouts/default.vue` mounted: `dispatch('init')`, scroll lazy (`liberaSegundaDobra`), busca usuario/carrinho/favoritos.

## Convencoes de codigo

- Ponto e virgula obrigatorio.
- Aspas simples.
- Indentacao 2 espacos.
- `const`/`let` — nunca `var`.
- Sem `console.log` em producao.
- Brace style Stroustrup (else/catch em nova linha).
- Self-closing obrigatorio: `<Comp />`.
- SVGs nunca inline — criar em `components/icons/`.
- Tamanho minimo de icone: 20px.
- Refatorar nomes para ingles (camelCase funcoes/variaveis, PascalCase componentes).
- Codigo em ingles; mensagens ao usuario em portugues.

## Cuidados com template herdado

Todo projeto nasce do `loja-modelo-front`. Sempre verificar:

- URLs absolutas hardcoded de outra loja (ex.: `desincha.com.br` em `plugins/listagem.js`).
- Slugs de vitrine/categoria de outro nicho em `store/home.js`.
- Nome/endereco placeholder em `layouts/default.vue` e `store/index.js`.
