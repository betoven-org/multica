---
name: performance
description: Otimizacao de performance em Shopify — imagens, lazy loading, Liquid loops, scripts e preload.
---

# Performance em Shopify

Tecnicas para otimizar performance de lojas Shopify, focando em Core Web Vitals (LCP, CLS, INP).

## Quando usar

- Em toda section e template criada ou modificada.
- Quando metricas de Lighthouse/PageSpeed estao abaixo do aceitavel.
- Especialmente em paginas de colecao e produto (alto trafego).

## Steps

### 1. Imagens — image_url com width

```liquid
{% comment %} ERRADO: imagem sem otimizacao {% endcomment %}
<img src="{{ product.featured_image | img_url: 'master' }}" alt="{{ product.title }}">

{% comment %} CORRETO: imagem otimizada com dimensoes {% endcomment %}
<img
  srcset="
    {{ product.featured_image | image_url: width: 165 }} 165w,
    {{ product.featured_image | image_url: width: 360 }} 360w,
    {{ product.featured_image | image_url: width: 533 }} 533w,
    {{ product.featured_image | image_url: width: 720 }} 720w,
    {{ product.featured_image | image_url: width: 940 }} 940w
  "
  src="{{ product.featured_image | image_url: width: 533 }}"
  sizes="(min-width: 1200px) 267px, (min-width: 750px) 33vw, 50vw"
  alt="{{ product.featured_image.alt | escape }}"
  loading="lazy"
  width="{{ product.featured_image.width }}"
  height="{{ product.featured_image.height }}"
>
```

**Regras para imagens:**
- `loading="lazy"` em imagens abaixo do fold.
- `loading="eager"` + `fetchpriority="high"` na imagem principal (LCP).
- SEMPRE declarar `width` e `height` para evitar CLS.
- Usar `image_url` (nao `img_url` que e deprecated).

```liquid
{% comment %} Imagem hero/LCP — carregamento prioritario {% endcomment %}
<img
  src="{{ section.settings.image | image_url: width: 1920 }}"
  srcset="
    {{ section.settings.image | image_url: width: 750 }} 750w,
    {{ section.settings.image | image_url: width: 1100 }} 1100w,
    {{ section.settings.image | image_url: width: 1500 }} 1500w,
    {{ section.settings.image | image_url: width: 1920 }} 1920w
  "
  sizes="100vw"
  alt="{{ section.settings.image.alt | escape }}"
  loading="eager"
  fetchpriority="high"
  width="{{ section.settings.image.width }}"
  height="{{ section.settings.image.height }}"
>
```

### 2. Lazy loading inteligente

```liquid
{% comment %} Primeiros 4 produtos: eager. Resto: lazy {% endcomment %}
{% for product in collection.products %}
  {% if forloop.index <= 4 %}
    {% assign img_loading = 'eager' %}
  {% else %}
    {% assign img_loading = 'lazy' %}
  {% endif %}

  {% render 'product-card', product: product, loading: img_loading %}
{% endfor %}
```

### 3. Reduzir Liquid loops

```liquid
{% comment %} ERRADO: loop pesado sem limite {% endcomment %}
{% for product in collection.products %}
  {% for variant in product.variants %}
    {% for option in variant.options %}
      ...
    {% endfor %}
  {% endfor %}
{% endfor %}

{% comment %} CORRETO: limitar iteracoes {% endcomment %}
{% for product in collection.products limit: 12 %}
  {% assign first_variant = product.variants | first %}
  {% render 'product-card', product: product, variant: first_variant %}
{% endfor %}
```

Otimizacoes de Liquid:
- Usar `limit:` em loops.
- Extrair computacoes do loop com `assign`.
- Evitar loops aninhados (3+ niveis).
- Usar `break` quando possivel.

```liquid
{% comment %} Otimizar busca em loop {% endcomment %}
{% comment %} ERRADO: busca linear dentro do loop {% endcomment %}
{% for product in collection.products %}
  {% for tag in product.tags %}
    {% if tag == 'featured' %}
      {% render 'product-card', product: product %}
    {% endif %}
  {% endfor %}
{% endfor %}

{% comment %} CORRETO: usar contains {% endcomment %}
{% for product in collection.products %}
  {% if product.tags contains 'featured' %}
    {% render 'product-card', product: product %}
  {% endif %}
{% endfor %}
```

### 4. Minimizar app scripts

Apps de terceiros adicionam JS que impacta performance:

- Auditar apps instaladas — remover as que nao estao em uso.
- Verificar impacto no Lighthouse (Third-party code blocking).
- Preferir apps que usam `ScriptTag` com `defer` ou `async`.
- Considerar reimplementar funcionalidades simples no tema.

### 5. Preload de recursos criticos

```liquid
{% comment %} layout/theme.liquid — no <head> {% endcomment %}

{% comment %} Preload da fonte principal {% endcomment %}
<link
  rel="preload"
  as="font"
  href="{{ 'custom-font.woff2' | asset_url }}"
  type="font/woff2"
  crossorigin
>

{% comment %} Preload da imagem LCP (hero banner) {% endcomment %}
{%- if template == 'index' -%}
  {%- assign hero_image = sections['hero-banner'].settings.image -%}
  {%- if hero_image -%}
    <link
      rel="preload"
      as="image"
      href="{{ hero_image | image_url: width: 1500 }}"
      imagesrcset="
        {{ hero_image | image_url: width: 750 }} 750w,
        {{ hero_image | image_url: width: 1100 }} 1100w,
        {{ hero_image | image_url: width: 1500 }} 1500w
      "
      imagesizes="100vw"
    >
  {%- endif -%}
{%- endif -%}

{% comment %} Preconnect para dominios externos {% endcomment %}
<link rel="preconnect" href="https://cdn.shopify.com" crossorigin>
<link rel="preconnect" href="https://fonts.shopifycdn.com" crossorigin>
```

### 6. CSS critico inline

```liquid
{% comment %} Inline CSS critico no <head> para evitar render-blocking {% endcomment %}
<style>
  /* Apenas estilos above-the-fold */
  .header { ... }
  .hero-banner { ... }
  .product-card { ... }
</style>

{% comment %} CSS restante carregado async {% endcomment %}
<link
  rel="stylesheet"
  href="{{ 'base.css' | asset_url }}"
  media="print"
  onload="this.media='all'"
>
<noscript>
  <link rel="stylesheet" href="{{ 'base.css' | asset_url }}">
</noscript>
```

### 7. JavaScript async/defer

```liquid
{% comment %} ERRADO: JS bloqueante {% endcomment %}
<script src="{{ 'heavy-script.js' | asset_url }}"></script>

{% comment %} CORRETO: defer para scripts nao criticos {% endcomment %}
<script src="{{ 'heavy-script.js' | asset_url }}" defer></script>

{% comment %} CORRETO: modulos para componentes interativos {% endcomment %}
<script src="{{ 'interactive-component.js' | asset_url }}" type="module"></script>
```

### 8. Hydrogen: otimizacoes especificas

```typescript
// Streaming com defer para dados secundarios
export async function loader({ params, context }: LoaderFunctionArgs) {
  const { storefront } = context

  // Dados criticos — aguardar
  const product = await storefront.query(PRODUCT_QUERY, {
    variables: { handle: params.handle! },
  })

  // Dados secundarios — streaming
  const recommendations = storefront.query(RECOMMENDATIONS_QUERY, {
    variables: { productId: product.id },
  })

  return defer({
    product,         // resolvido imediatamente
    recommendations, // streamed quando pronto
  })
}
```

## Common mistakes

1. **Imagens sem width/height** — Causa CLS. Sempre declarar dimensoes.
2. **Lazy load na imagem hero** — Atrasa LCP. Usar `loading="eager"` + `fetchpriority="high"`.
3. **`img_url` em vez de `image_url`** — `img_url` e deprecated e nao suporta todos formatos.
4. **Loops sem limit** — Colecoes com centenas de produtos travam a renderizacao.
5. **Nao preload de fontes** — Fontes customizadas causam FOIT/FOUT. Sempre preload com `crossorigin`.
6. **Scripts no `<head>` sem defer** — Bloqueia renderizacao. Usar `defer` ou mover para antes do `</body>`.
7. **Nao auditar apps** — Apps de terceiros sao a principal causa de JS bloqueante.
8. **CSS inteiro inline** — Apenas CSS critico (above-the-fold) deve ser inline. Resto async.
