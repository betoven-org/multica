---
name: uappi-routing
description: Page routing architecture - catch-all pattern, url/verify and nivel-based rendering.
---

# Roteamento Uappi

## Catch-all central: `src/pages/_produto.vue`

Toda URL que nao casa com uma pagina explicita cai no `_produto.vue`. No `asyncData`:

```js
// 1. Descobre o tipo da pagina
const verify = await $axios.$get('/v2/front/url/verify', { params: { url: route.path } });
const nivel = verify.data.nivel; // ex.: 'product/detail', 'category', 'landing-page', 'brand', 'search', 'lista'
```

## Resolucao por `nivel`

| nivel | Endpoint | Componente | Vuex |
|---|---|---|---|
| `product/detail` | `GET /v2/front/url/product/detail?url=...` | `produtoDetalhe` | commits em `detalhe/*` |
| `category` | `$requestDataListagem(route, 'category')` | `listagem` | `categoria/*` |
| `landing-page` (path com `/c/`) | `$requestDataListagem(route, 'landing-page')` | `listagem` | `categoria/*` |
| `brand` | `$requestDataListagem(route, 'brand')` | `listagem` | `categoria/*` |
| `search` | `$requestDataListagem(route, 'search')` | `listagem` | `categoria/*` |
| path com `/lista/` | `$requestDataListagem(route, 'lista')` | `produtoLista-detalhe` | `categoria/*` |

## Computeds importantes

- `componentPage` — resolve qual componente renderizar com base no `nivel`.
- `categoriaNv` — profundidade de categoria (`$route.params.length > 1`).

## Outras paginas

- `pages/index.vue` — Home. Usa `GET /v2/front/url/home` no `asyncData`.
- `pages/_categoriaSegundoNv.vue`, `pages/_categoriaTerceiroNv.vue` — categorias aninhadas, mesmo modelo.
- `pages/marcas/` — listagem por marca.
- `pages/lista/` — listas (wishlist/curadoria).

## Lazy loading da segunda dobra

`layouts/default.vue` registra listener de scroll unico (`liberaSegundaDobra`). No primeiro scroll faz commit `setLoadSegundaDobra`. A pagina `pages/index.vue` observa esse flag e dispara `home/requestScroll` (carrega banner do meio, vitrines, instashop).
