---
name: uappi-vuex-store
description: Vuex store patterns - root state, namespaced modules, common actions and mutations.
---

# Vuex Store Uappi

## Root store (`store/index.js`)

Estado raiz:

```js
state: {
  config: {},           // settings da loja (via /v2/front/settings)
  user: null,           // usuario logado (via /v2/front/checkout/user)
  carrinho: {},         // carrinho (via /v2/front/checkout/cart)
  dadosPageAtual: {},   // dados da pagina atual (SEO, breadcrumb)
  screenWidth: 1366,    // largura da tela (360 mobile / 1366 desktop)
  loader: false,        // estado de loading
  tipoImg: 'webp',     // formato de imagem (webp ou originais para Mac)
  manutencaoLoja: false,
  loadSegundaDobra: false, // flag para lazy load da segunda dobra
  nomeSite: 'Loja modelo front-end', // TROCAR por loja
  siteUrl: process.env.SUB_DOMAIN_URL,
  siteUrlFront: process.env.SITE_URL
}
```

Registra modulos de `@wapstore`: `busca`, `carrinhoFrete`, `zoomImagem`, `detalheDuasColunas`, `compreJunto`.

### Actions raiz comuns

- `init` — chama `getScreenWidth` (listener de `resize`).
- `getCarrinho` — `GET /v2/front/checkout/cart` e commit `setCarrinho`.
- `toggleSub` — animacao de submenu.

### Mutations raiz

- `setConfig`, `setUser`, `setCarrinho`, `setDadosPageAtual`
- `setScreenWidth`, `changeLoader`, `defineTipoImg`
- `setLoadSegundaDobra`, `setProdsFavoritos`

## Modulo `store/home.js`

Banners e vitrines da home. Conteudo carregado de forma **lazy**:

```js
actions: {
  async requestScroll({ commit }) {
    // Disparado quando loadSegundaDobra = true (primeiro scroll)
    // Carrega: banner do meio, vitrines, instashop
    const bannerMeio = await this.$axios.$get('/v2/front/showcase/banners/modelo-meio-home');
    commit('setBannerMeio', bannerMeio.data);
    // ... vitrines, instashop
  }
}
```

## Modulo `store/categoria.js`

Estado da listagem de produtos:

```js
state: {
  pageData: {},      // dados da pagina de listagem
  limit: 8,          // produtos por pagina
  loadProds: false,  // flag de loading
  showFilter: false  // visibilidade do filtro mobile
}
```

Mutations: `changePageData`, `toggleLoadProds`, `toggleShowFilter`.

## Modulo `store/listagem.js`

Links de paginacao para SEO:

```js
state: {
  nextPg: '',
  prevPg: ''
}
// Mutations: changeNextPg, changePrevPg
```

## Menu (namespaced)

Geralmente em `store/cabecalho/menu.js` (pode variar por loja):

```js
// Actions/mutations: toggleMenu, setMenu, loadMenu
```

## Outros modulos comuns

- `detalhe` — estado do produto (dados, SKU selecionado, galeria).
- `popup` — controle de popups.
- `rodape` — dados do rodape.
- `institucional` — paginas institucionais.
- `lista/` — listas (wishlist/curadoria).

> Os nomes exatos variam por loja. Sempre confira o `store/` do projeto.

## Padrao de uso

```js
// Em asyncData (SSR)
async asyncData({ store, route }) {
  const data = await store.dispatch('home/requestBanners');
  store.commit('setDadosPageAtual', data);
}

// Em computed
computed: {
  ...mapState(['config', 'carrinho', 'screenWidth']),
  ...mapState('categoria', ['pageData', 'loadProds'])
}

// Em methods
methods: {
  ...mapActions(['getCarrinho']),
  ...mapMutations('categoria', ['changePageData'])
}
```
