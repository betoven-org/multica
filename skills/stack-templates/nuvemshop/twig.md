---
name: nuvemshop-twig
description: Twig em temas Nuvemshop — snipplet vs include, scope de set, comentarios que vazam, classes interpoladas.
---

# Twig em temas Nuvemshop

A Nuvemshop usa Twig com extensoes proprias. Arquivos `.tpl` tem `{% %}` (tags), `{{ }}` (expressoes) e `{# #}` (comentarios).

## `{% snipplet %}` vs `{% include %}`

- `{% snipplet "header/header.tpl" %}` — **cacheado pela plataforma**. Busca implicita em `snipplets/`. Mudou o arquivo e nao ve efeito? E o cache.
- `{% include "static/js/store.js.tpl" %}` — Twig padrao, **nao cacheado**, path absoluto.

**Regra:** componentes visuais que mudam pouco (header, footer, card) usam `{% snipplet %}`. Templates JS/CSS com Twig interpolado usam `{% include %}`.

Em desenvolvimento, se mudou snipplet e nao ve efeito, trocar pontualmente para `{% include 'snipplets/foo.tpl' %}` para confirmar se e cache.

## Comentarios `{# #}` vazam quando contem `{% %}`

Bug real da plataforma. A engine nao escapa tags Twig dentro de comentarios — renderiza como texto cru no storefront.

```twig
{# ERRADO — vai vazar no front: #}
{# Uso: {% include 'snipplets/faq.tpl' with {title: 'X'} %} #}

{# CERTO — descrever em prosa: #}
{# Uso: ver snipplets/home/home-faq.tpl para exemplo real #}
```

## `{% set %}` dentro de `{% for %}` NAO escapa scope

```twig
{# NAO funciona — flag continua false depois do loop #}
{% set flag = false %}
{% for item in items %}
  {% if item.match %}{% set flag = true %}{% endif %}
{% endfor %}
{# flag aqui ainda e false #}
```

**Workaround:** captured block:

```twig
{% set match_str %}
  {% for item in items %}{% if item.match %}x{% endif %}{% endfor %}
{% endset %}
{% set has_match = match_str | trim is not empty %}
```

## Classes HTML interpoladas — armadilha para scanners CSS

```twig
<span class="{{ order.payment_status }}">...</span>
```

Essas classes nao sao detectaveis em build time por scanners CSS (Tailwind, PurgeCSS).

Solucoes:
1. **Safelist** — listar valores possiveis no config do scanner
2. **Classe estatica + data-attribute:**
   ```twig
   <span class="payment-status" data-payment-status="{{ order.payment_status }}">...</span>
   ```

## Componentes `{{ component(...) }}`

Renderizam HTML nao-controlavel com classes Bootstrap fixas. Voce passa parametros quando expostos, nao controla markup interno.

## Paginas institucionais via `page.handle`

Todas caem em `templates/page.tpl`. Branching por handle:

```twig
{% if page.handle == 'a-loja' %}
  {% snipplet "pages/about.tpl" %}
{% elseif page.handle == 'politica-de-troca' %}
  {% snipplet "pages/policy.tpl" %}
{% else %}
  <div class="page-content">{{ page.content | raw }}</div>
{% endif %}
```

Usar `page.handle`, NAO `page.slug` ou `page.url` (nao funcionam).

## Modo preview (`params.preview`)

True quando o lojista visualiza o tema no admin. Forcar renderizacao de secoes condicionais:

```twig
{% if settings.show_hero or params.preview %}
  {% snipplet "home/hero.tpl" %}
{% endif %}
```

## Variacoes de template via classe no `<body>`

```twig
<body class="template-{{ template | replace('.', '-') }}
  {% if customer %}customer-logged-in{% endif %}">
```

CSS escopado sem duplicar regras:

```scss
.template-product .product__title { ... }
.customer-logged-in .header__login { display: none; }
```
