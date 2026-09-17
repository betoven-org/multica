---
name: liquid-section
description: Como criar uma Liquid section em Shopify com schema, settings, blocks e presets.
---

# Liquid Sections em Shopify

Como criar sections customizadas para temas Shopify usando Liquid, com schema completo e boas praticas.

## Quando usar

- Para criar blocos de conteudo configuraveis pelo lojista no Theme Editor.
- Para qualquer secao de pagina que precisa de settings customizaveis.
- Para blocos reutilizaveis entre paginas (homepage, product, collection).

## Steps

### 1. Estrutura de arquivos

```
theme/
  sections/
    featured-collection.liquid    # Section principal
  snippets/
    product-card.liquid           # Snippet reutilizavel
  assets/
    featured-collection.css       # CSS especifico (opcional)
  locales/
    pt-BR.json                    # Traducoes
    en.default.json
```

### 2. Criar a section

```liquid
{% comment %} sections/featured-collection.liquid {% endcomment %}

<section
  class="featured-collection"
  style="
    --section-padding-top: {{ section.settings.padding_top }}px;
    --section-padding-bottom: {{ section.settings.padding_bottom }}px;
  "
>
  <div class="page-width">
    {%- if section.settings.title != blank -%}
      <h2 class="featured-collection__title {{ section.settings.heading_size }}">
        {{ section.settings.title | escape }}
      </h2>
    {%- endif -%}

    {%- if section.settings.description != blank -%}
      <div class="featured-collection__description rte">
        {{ section.settings.description }}
      </div>
    {%- endif -%}

    <div class="featured-collection__grid grid grid--{{ section.settings.columns_desktop }}-col">
      {%- for product in section.settings.collection.products limit: section.settings.products_to_show -%}
        <div class="featured-collection__item grid__item">
          {% render 'product-card', product: product, show_vendor: section.settings.show_vendor %}
        </div>
      {%- else -%}
        {%- for i in (1..section.settings.products_to_show) -%}
          <div class="featured-collection__item grid__item">
            {% render 'product-card-placeholder' %}
          </div>
        {%- endfor -%}
      {%- endfor -%}
    </div>

    {%- if section.settings.show_view_all -%}
      <div class="featured-collection__view-all center">
        <a
          href="{{ section.settings.collection.url }}"
          class="button button--secondary"
        >
          {{ 'sections.featured_collection.view_all' | t }}
        </a>
      </div>
    {%- endif -%}
  </div>
</section>

{% schema %}
{
  "name": "t:sections.featured_collection.name",
  "tag": "section",
  "class": "section",
  "disabled_on": {
    "groups": ["header", "footer"]
  },
  "settings": [
    {
      "type": "inline_richtext",
      "id": "title",
      "default": "Featured collection",
      "label": "t:sections.featured_collection.settings.title.label"
    },
    {
      "type": "richtext",
      "id": "description",
      "label": "t:sections.featured_collection.settings.description.label"
    },
    {
      "type": "collection",
      "id": "collection",
      "label": "t:sections.featured_collection.settings.collection.label"
    },
    {
      "type": "range",
      "id": "products_to_show",
      "min": 2,
      "max": 12,
      "step": 1,
      "default": 4,
      "label": "t:sections.featured_collection.settings.products_to_show.label"
    },
    {
      "type": "select",
      "id": "columns_desktop",
      "options": [
        { "value": "2", "label": "2" },
        { "value": "3", "label": "3" },
        { "value": "4", "label": "4" }
      ],
      "default": "4",
      "label": "t:sections.featured_collection.settings.columns_desktop.label"
    },
    {
      "type": "select",
      "id": "heading_size",
      "options": [
        { "value": "h2", "label": "t:sections.all.heading_size.options__1.label" },
        { "value": "h1", "label": "t:sections.all.heading_size.options__2.label" },
        { "value": "h0", "label": "t:sections.all.heading_size.options__3.label" }
      ],
      "default": "h1",
      "label": "t:sections.all.heading_size.label"
    },
    {
      "type": "checkbox",
      "id": "show_vendor",
      "default": false,
      "label": "t:sections.featured_collection.settings.show_vendor.label"
    },
    {
      "type": "checkbox",
      "id": "show_view_all",
      "default": true,
      "label": "t:sections.featured_collection.settings.show_view_all.label"
    },
    {
      "type": "header",
      "content": "t:sections.all.padding.section_padding_heading"
    },
    {
      "type": "range",
      "id": "padding_top",
      "min": 0,
      "max": 100,
      "step": 4,
      "unit": "px",
      "label": "t:sections.all.padding.padding_top",
      "default": 36
    },
    {
      "type": "range",
      "id": "padding_bottom",
      "min": 0,
      "max": 100,
      "step": 4,
      "unit": "px",
      "label": "t:sections.all.padding.padding_bottom",
      "default": 36
    }
  ],
  "presets": [
    {
      "name": "t:sections.featured_collection.presets.name"
    }
  ]
}
{% endschema %}
```

### 3. Snippet reutilizavel

```liquid
{% comment %} snippets/product-card.liquid {% endcomment %}
{% comment %}
  Renders a product card.

  Accepts:
  - product: {Object} Product Liquid object
  - show_vendor: {Boolean} Show vendor name

  Usage:
  {% render 'product-card', product: product, show_vendor: true %}
{% endcomment %}

<div class="product-card">
  <a href="{{ product.url }}" class="product-card__link">
    {%- if product.featured_media -%}
      <img
        srcset="
          {%- if product.featured_media.width >= 165 -%}{{ product.featured_media | image_url: width: 165 }} 165w,{%- endif -%}
          {%- if product.featured_media.width >= 360 -%}{{ product.featured_media | image_url: width: 360 }} 360w,{%- endif -%}
          {%- if product.featured_media.width >= 533 -%}{{ product.featured_media | image_url: width: 533 }} 533w,{%- endif -%}
          {{ product.featured_media | image_url }} {{ product.featured_media.width }}w
        "
        src="{{ product.featured_media | image_url: width: 533 }}"
        sizes="(min-width: 1200px) 267px, (min-width: 750px) 25vw, 50vw"
        alt="{{ product.featured_media.alt | escape }}"
        class="product-card__image"
        loading="lazy"
        width="{{ product.featured_media.width }}"
        height="{{ product.featured_media.height }}"
      >
    {%- endif -%}

    <div class="product-card__info">
      {%- if show_vendor -%}
        <span class="product-card__vendor caption-with-letter-spacing">
          {{ product.vendor }}
        </span>
      {%- endif -%}

      <h3 class="product-card__title">
        {{ product.title | escape }}
      </h3>

      {% render 'price', product: product %}
    </div>
  </a>
</div>
```

### 4. Traducoes

```json
// locales/pt-BR.json
{
  "sections": {
    "featured_collection": {
      "name": "Colecao em destaque",
      "view_all": "Ver todos",
      "settings": {
        "title": { "label": "Titulo" },
        "description": { "label": "Descricao" },
        "collection": { "label": "Colecao" },
        "products_to_show": { "label": "Produtos a exibir" },
        "columns_desktop": { "label": "Colunas no desktop" },
        "show_vendor": { "label": "Exibir fabricante" },
        "show_view_all": { "label": "Exibir botao ver todos" }
      },
      "presets": {
        "name": "Colecao em destaque"
      }
    }
  }
}
```

## Tipos de settings disponiveis

| Tipo | Uso |
|------|-----|
| `text` | Input de texto curto |
| `textarea` | Texto longo |
| `richtext` | Texto com formatacao HTML |
| `inline_richtext` | Texto com formatacao inline |
| `image_picker` | Upload de imagem |
| `url` | Link |
| `collection` | Seletor de colecao |
| `product` | Seletor de produto |
| `color` | Cor (hex) |
| `color_scheme` | Esquema de cores do tema |
| `range` | Slider numerico |
| `select` | Dropdown |
| `checkbox` | Boolean |
| `number` | Numerico |
| `video_url` | URL de video (YouTube/Vimeo) |
| `header` | Separador visual no editor |
| `paragraph` | Texto informativo no editor |

## Common mistakes

1. **Usar `include` em vez de `render`** — `include` esta deprecated. Sempre usar `{% render 'snippet' %}`.
2. **Esquecer `| escape` em textos do usuario** — Previne XSS. Sempre escapar outputs de texto.
3. **Sem presets** — Sem `presets`, a section nao aparece no "Add section" do Theme Editor.
4. **Imagens sem width/height** — Causa CLS. Sempre declarar dimensoes.
5. **Sem traducoes** — Strings hardcoded em ingles. Usar `t:` prefix no schema e filtro `| t` no Liquid.
6. **Schema invalido** — JSON invalido no `{% schema %}` causa erro silencioso. Validar com `shopify theme check`.
7. **Sections muito grandes** — Extrair logica reutilizavel em snippets com `{% render %}`.
