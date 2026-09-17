---
name: uappi-new-page
description: Creating new pages and sections - catch-all pattern, Vuex modules, API integration, showcase slugs.
---

# Criar paginas e secoes Uappi

## Entendendo o roteamento

A maioria das paginas passa pelo catch-all `src/pages/_produto.vue`, que usa `/v2/front/url/verify` para descobrir o tipo. Paginas explicitas (ex.: `pages/index.vue`, `pages/marcas/`) tem prioridade sobre o catch-all.

## Criar uma pagina explicita

Para paginas que nao passam pelo catch-all (ex.: institucional customizada):

```vue
<!-- src/pages/minha-pagina.vue -->
<template>
  <div>
    <component :is="componentPage" />
  </div>
</template>

<script>
export default {
  name: 'MinhaPagina',

  async asyncData ({ $axios, store, error }) {
    try {
      const { data } = await $axios.$get('/v2/front/url/page', {
        params: { url: '/minha-pagina' }
      });
      store.commit('setDadosPageAtual', data);
      return { pageData: data };
    }
    catch (e) {
      error({ statusCode: 404 });
    }
  }
};
</script>
```

## Criar um modulo Vuex

```js
// src/store/meu-modulo.js
export const state = () => ({
  dados: null,
  loading: false
});

export const mutations = {
  setDados (state, payload) {
    state.dados = payload;
  },
  toggleLoading (state, val) {
    state.loading = val;
  }
};

export const actions = {
  async fetchDados ({ commit }) {
    commit('toggleLoading', true);
    try {
      const { data } = await this.$axios.$get('/v2/front/showcase/products/meu-slug');
      commit('setDados', data);
    }
    finally {
      commit('toggleLoading', false);
    }
  }
};
```

## Usar vitrines e banners

Os slugs sao configurados no painel Uappi. Use os endpoints de showcase:

```js
// Buscar banner por slug
const banners = await this.$axios.$get('/v2/front/showcase/banners/meu-slug-banner');

// Buscar vitrine de produtos
const produtos = await this.$axios.$get('/v2/front/showcase/products/meu-slug-vitrine');

// Buscar menu/estrutura
const menu = await this.$axios.$get('/v2/front/struct/menus/meu-slug-menu');
```

## Criar componente para a secao

```vue
<!-- src/components/secao/minha-secao.vue -->
<!-- Uso: <secaoMinhSecao /> (auto-registrado) -->
<template>
  <section class="minha-secao">
    <h2>{{ titulo }}</h2>
    <div class="minha-secao__grid">
      <slot />
    </div>
  </section>
</template>

<script>
export default {
  name: 'MinhaSecao',

  props: {
    titulo: {
      type: String,
      default: ''
    }
  }
};
</script>

<style scoped>
.minha-secao {
  max-width: var(--container);
  padding: 0 var(--container-padding);
  margin: 0 auto;
}

.minha-secao__grid {
  display: grid;
  gap: var(--space-5);
}
</style>
```

## Criar uma listagem customizada

Use os helpers injetados pelo plugin `listagem.js`:

```js
async asyncData ({ route, app, store }) {
  // Busca dados da listagem usando o helper
  await app.$requestDataListagem(route, 'category', () => {
    // callback opcional apos carregar
  });

  const { pageData } = store.state.categoria;
  const qtdPages = app.$calcQtdPages(pageData.totalProducts, store.state.categoria.limit);
  const pg = parseInt(route.query.pg) || 1;
  app.$changeNextPrev(pg, qtdPages);

  return { pageData };
}
```

## Integrar com lazy loading

Se a secao fica abaixo da dobra, siga o padrao do projeto:

1. O `layouts/default.vue` ja faz commit `setLoadSegundaDobra` no primeiro scroll.
2. Na pagina, observe o flag e dispare a action:

```js
watch: {
  '$store.state.loadSegundaDobra' (val) {
    if (val) {
      this.$store.dispatch('meu-modulo/fetchDados');
    }
  }
}
```

## Checklist

- [ ] Endpoint da API existe? Confirmar slug no painel ou usar `/v2/collection/front`.
- [ ] Usar caminho relativo (`/v2/front/...`), nunca URL absoluta.
- [ ] Commit `setDadosPageAtual` para SEO/breadcrumb.
- [ ] Estilos scoped, usando tokens CSS (`var(--*)`).
- [ ] Componentes auto-registrados pelo prefixo do subdiretorio.
