---
name: uappi-components
description: Component patterns - auto-registration, @wapstore packages, showcase and listagem helpers.
---

# Componentes Uappi

## Auto-registro de componentes locais

Componentes em `src/components/` sao registrados automaticamente com prefixo camelCase baseado no subdiretorio:

```
src/components/geral/header.vue      → <geralHeader />
src/components/geral/footer.vue      → <geralFooter />
src/components/produto/detalhe.vue   → <produtoDetalhe />
src/components/listagem/filtros.vue  → <listagemFiltros />
```

Configurado no `nuxt.config.js`:

```js
components: ['~/components', '../node_modules/@wapstore']
```

## Componentes @wapstore

Pacotes da plataforma, auto-importados diretamente (sem prefixo de diretorio):

```html
<ordenacao-produtos />
<card-full :produto="item" />
<carrinho-lateral />
<pop-up-login />
```

Transpilados via `build.transpile: ['@wapstore']`.

## Helpers injetados via plugins

### Plugin `listagem.js` — helpers `$`

```js
// Busca dados da listagem (categoria, brand, search, landing-page, lista)
this.$requestDataListagem(rotaAtual, endPoint, callback?)
// endPoint: 'category' | 'landing-page' | 'brand' | 'search' | 'lista'
// Monta URL, calcula offset/limit a partir de ?pg/?ipp
// Faz commit em setDadosPageAtual + categoria/changePageData + categoria/toggleLoadProds

// Calcula total de paginas
this.$calcQtdPages(totalProds, limitProdsPP) // Math.ceil

// Atualiza links next/prev para SEO
this.$changeNextPrev(pg, qtdPages) // commits em listagem/changeNextPg e changePrevPg
```

### Helpers @wapstore injetados

| Plugin | Helpers |
|---|---|
| `dados-estruturados` | `$setPaginaDadosEstruturados`, `$seoSetPaginaHome`, `$seoSetPaginaDetalheProduto`, `$seoSetPaginaListagem` |
| `gtm/gtm` | `$gtmBannerEvent`, `$gtmVitrineDataLayer`, `$gtmProductClick`, `$gtmEventAddToCart`, `$gtmEventRemoveFromCart`, `$gtmEventUserProfile` |
| `gtm/gtm-paginas` | `$gtmGetData`, `$setPagina`, `$setPaginaHome`, `$setPaginaListagem`, `$setPaginaDetalheProduto` |
| `carrinho` | `$carrinhoAdd`, `$carrinhoRemove`, `$carrinhoUpdate`, `$carrinhoGet`, `$carrinhoShop`, `$carrinhoRedirect` |
| `utils.client` | `$setVarCss` (seta variavel CSS em runtime) |

> Antes de criar um helper novo, verifique se ja existe um `$` equivalente dos plugins @wapstore.

### Plugin `filters.js` — filtros Vue globais

```html
{{ preco | formatPrice }}     <!-- R$ 99,90 -->
{{ valor | totalParcelado }}
{{ texto | geraBold }}        <!-- converte *texto* em <b> -->
{{ cep | cep }}               <!-- 00000-000 -->
```

### Plugin `axios.js`

- Gerencia `PHPSESSID` (le cookie, injeta header `Session`).
- Intercepta `/checkout/cart` → commit `setCarrinho`.
- Intercepta `/shipment/product`.
- `?debug` mostra detalhes do erro da API.

### Plugin `config.server.js` (server-only)

- `GET /v2/front/settings` no SSR → commit `setConfig`.

### Plugin `favoritos.client.js` (client-only)

- `$getFavoritos()` → `GET /v2/front/wishlist` → commit `setProdsFavoritos`.

## Padroes de componente

### SVGs como componentes

Nunca inline no template. Criar em `components/icons/` (ou `components/icon/`):

```vue
<!-- components/icon/cart.vue -->
<template>
  <svg viewBox="0 0 24 24" ...>
    <path d="..." />
  </svg>
</template>
```

Uso: `<icon-cart />` (auto-registrado).

### Estilos scoped

Usar `<style scoped>` por padrao. Estilos globais apenas em `src/static/css/geral.css`.

### Ordem das opcoes no componente

1. `name`
2. `components`
3. `props`
4. `data`
5. `computed`
6. `watch`
7. Lifecycle hooks (`created`, `mounted`, etc.)
8. `methods`
