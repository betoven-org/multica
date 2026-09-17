---
name: uappi-review
description: Review checklist for Uappi storefronts - code quality, API usage, design tokens and common mistakes.
---

# Review Checklist Uappi

## API e sessao

- [ ] Nenhuma URL absoluta de API hardcoded — usar caminho relativo (`/v2/front/...`).
- [ ] Header `App-Token: wapstore` presente (via config global do axios).
- [ ] `PHPSESSID` tratado corretamente no `plugins/axios.js`.
- [ ] Parametro de busca e `busca` (nao `url`) para `/v2/front/url/product/listing/search`.
- [ ] Erros de API tratados com `try/catch` no `asyncData` (evitar 500 no SSR).

## Template herdado

- [ ] Sem URLs hardcoded de outra loja (desincha, isaclin, loja-modelo, etc).
- [ ] `nomeSite` no `store/index.js` atualizado para a loja atual.
- [ ] Dados estruturados em `layouts/default.vue` com nome/endereco corretos.
- [ ] Slugs de vitrines em `store/home.js` correspondem ao painel da loja.
- [ ] `src/.env` aponta para o dominio correto.
- [ ] `nuxt.config.js` baseUrl alinhado com as envs.

## Codigo

- [ ] Ponto e virgula em toda instrucao.
- [ ] Aspas simples.
- [ ] Indentacao 2 espacos.
- [ ] `const`/`let` — sem `var`.
- [ ] Sem `console.log`.
- [ ] Brace style Stroustrup (else/catch em nova linha).
- [ ] Self-closing: `<Comp />` (com espaco antes de `/>`)
- [ ] Ordem das opcoes do componente: name, components, props, data, computed, watch, hooks, methods.
- [ ] SVGs em `components/icons/` — nunca inline no template.
- [ ] Tamanho minimo de icone: 20px.
- [ ] Sem comentarios desnecessarios — codigo autoexplicativo.
- [ ] Nomes em ingles (camelCase variaveis/funcoes, PascalCase componentes).

## Design system

- [ ] Cores via `var(--token)` — nunca literais (`#E5A923`, etc).
- [ ] Font-sizes via tokens (`--fonteBody1`, `--fonteBody2`, etc) — minimo 12px (Body 3).
- [ ] Spacing na escala 4px (`--space-1` a `--space-24`) — nunca valores avulsos.
- [ ] Border-radius via tokens (`--radius-sm`, `--radius`, `--radius-lg`).
- [ ] Sem `box-shadow` (elevacao = `border: 2px solid var(--cinza)`).
- [ ] Sem `text-transform: uppercase`.
- [ ] Estilos `scoped` nos componentes; globais so em `geral.css`.

## Componentes @wapstore

- [ ] Verificar se ja existe helper `$` equivalente antes de criar um novo.
- [ ] `build.transpile: ['@wapstore']` presente no `nuxt.config.js`.
- [ ] Preferir componentes @wapstore quando disponiveis.

## Performance

- [ ] Conteudo abaixo da dobra usa lazy loading (flag `loadSegundaDobra`).
- [ ] Imagens com dimensoes explicitas (evitar CLS).
- [ ] Sem @2x — usar tamanho 1x.

## Seguranca

- [ ] `.npmrc` com token privado — nunca expor.
- [ ] `npm_token_deploy` no compose — tratar como segredo.
- [ ] `src/.env` nao commitado com valores sensiveis.

## Lint

```bash
npm run lint       # verificar
npm run lintfix    # corrigir automaticamente
```
