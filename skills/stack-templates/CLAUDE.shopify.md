# Shopify — Convenções do Projeto

## Stack

Identifique pelo repo se é:
- **Liquid Theme** (Dawn-based) — sections/, snippets/, templates/
- **Hydrogen** (React/Remix headless) — app/routes/, app/components/
- **Shopify App** (API/webhooks) — shopify-app-js

## MCP Servers disponíveis

### shopify-dev-mcp
```
- search_docs_chunks(query) → Busca docs Shopify
- validate_graphql_codeblocks(code) → Valida queries Storefront/Admin API
- validate_component_codeblocks(code) → Valida componentes
- learn_shopify_api(query) → Aprende sobre APIs
```

**SEMPRE valide GraphQL queries via MCP antes de commitar.**

## Liquid (Theme Development)

### Estrutura (Dawn reference)
```
assets/       → CSS, JavaScript
config/       → settings_schema.json (tema)
layout/       → theme.liquid (wrapper base)
locales/      → Traduções (en.json, pt-BR.json)
sections/     → Componentes com schema (configuráveis)
snippets/     → Fragmentos reutilizáveis (sem schema)
templates/    → Templates de página
```

### Section com schema
```liquid
<div class="featured-collection">
  <h2>{{ section.settings.title }}</h2>
  {% for product in collections[section.settings.collection].products limit: section.settings.limit %}
    {% render 'product-card', product: product %}
  {% endfor %}
</div>

{% schema %}
{
  "name": "Featured Collection",
  "settings": [
    { "type": "text", "id": "title", "label": "Title", "default": "Featured" },
    { "type": "collection", "id": "collection", "label": "Collection" },
    { "type": "range", "id": "limit", "min": 2, "max": 12, "step": 2, "default": 4 }
  ],
  "presets": [{ "name": "Featured Collection" }]
}
{% endschema %}
```

### Regras Liquid
- Use `{% render %}` pra snippets (nunca `{% include %}` — deprecated)
- Sempre tenha `presets` pra section aparecer no editor
- Imagens otimizadas: `{{ image | image_url: width: 400 | image_tag: loading: 'lazy' }}`
- Traduções: `{{ "key" | t }}`
- HTML-first, JavaScript só quando necessário

## Hydrogen (Headless)

### Estrutura
```
app/
├── routes/        → Pages (React Router / Remix)
├── components/    → React components
├── lib/           → Storefront client, utilities
└── graphql/       → Queries e fragments
```

### Regras Hydrogen
- TypeScript obrigatório
- Use `useLoaderData` pra dados (não fetch client-side)
- Storefront API pra dados públicos, Admin API server-only
- Cache com CacheLong / CacheShort / CacheCustom
- Tipos auto-gerados com @shopify/hydrogen-codegen
- Versionamento Calver (2025.7.x) — updates trimestrais

### Componentes nativos
```tsx
import { Image, Money, CartForm } from '@shopify/hydrogen'

// Sempre usar componentes nativos quando disponíveis
<Image data={product.featuredImage} width={400} height={400} />
<Money data={product.priceRange.minVariantPrice} />
```

## Shopify Apps

### Stack
- @shopify/shopify-api — Core (OAuth, webhooks)
- @shopify/shopify-app-remix — Integração Remix
- @shopify/admin-api-client — Admin GraphQL/REST
- @shopify/storefront-api-client — Storefront GraphQL

### Regras Apps
- OAuth flow via shopify-app-js
- Webhooks registrados declarativamente
- Rate limiting: Admin 2 pontos/s, Storefront por IP
- API versionada trimestralmente (2025-07, etc.)
- Web Components pra UI (Polaris archived)

## Checklist antes de PR

- [ ] GraphQL validado via MCP (validate_graphql_codeblocks)
- [ ] Schema correto em sections Liquid (com presets)
- [ ] Imagens otimizadas (image_url com width, lazy load)
- [ ] Traduções em locales/
- [ ] Sem console.log
- [ ] TypeScript strict (Hydrogen/Apps)
- [ ] Testado com Shopify CLI (shopify theme dev / shopify app dev)

## Não faça

- Não use {% include %} — deprecated, use {% render %}
- Não faça fetch de Admin API no browser
- Não ignore rate limits
- Não use Polaris React em projetos novos (use Web Components)
- Não hardcode API version — use variável
