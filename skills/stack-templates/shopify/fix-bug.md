---
name: fix-bug
description: Debugging em Shopify — theme check, preview, CLI, erros Liquid e problemas com metafields.
---

# Debugging em Shopify

Abordagem sistematica para identificar e corrigir bugs em temas Shopify (Liquid e Hydrogen).

## Quando usar

- Section nao renderiza ou renderiza incorretamente.
- Erros Liquid (undefined, nil, filtros incorretos).
- Metafields nao aparecem.
- Problemas de performance ou layout.
- Hydrogen: erros de build, loader, ou hydration.

## Steps

### 1. Theme Check (Liquid)

```bash
# Rodar theme check para encontrar erros e warnings
shopify theme check

# Check especifico por categoria
shopify theme check --category performance
shopify theme check --category suggestion

# Auto-corrigir problemas simples
shopify theme check --auto-correct
```

Erros comuns que o theme check encontra:
- `include` deprecated (usar `render`).
- `img` sem width/height.
- Filtros deprecated.
- Schema JSON invalido.

### 2. Preview local

```bash
# Iniciar servidor de desenvolvimento local
shopify theme dev

# Especificar loja
shopify theme dev --store=minha-loja.myshopify.com

# Com tema especifico
shopify theme dev --theme-editor-sync
```

O preview local permite:
- Hot reload de mudancas.
- Ver erros Liquid no terminal.
- Inspecionar output renderizado.

### 3. Debug com Liquid

```liquid
{% comment %} Inspecionar variavel {% endcomment %}
<pre>{{ product | json }}</pre>

{% comment %} Verificar se variavel existe {% endcomment %}
{% if product == blank %}
  <p>DEBUG: product is blank</p>
{% endif %}

{% comment %} Verificar tipo {% endcomment %}
<p>Type: {{ product.title | class }}</p>

{% comment %} Listar propriedades de um objeto {% endcomment %}
{% for prop in product %}
  <p>{{ prop[0] }}: {{ prop[1] }}</p>
{% endfor %}
```

**IMPORTANTE:** Remover todo debug antes de commitar.

### 4. Problemas comuns com Liquid

#### Variavel undefined/nil

```liquid
{% comment %} ERRADO: acesso direto pode dar nil {% endcomment %}
{{ product.metafields.custom.size }}

{% comment %} CORRETO: verificar antes {% endcomment %}
{%- assign size_metafield = product.metafields.custom.size -%}
{%- if size_metafield != blank -%}
  {{ size_metafield.value }}
{%- endif -%}
```

#### Filtro retorna nil

```liquid
{% comment %} ERRADO: where em array nil {% endcomment %}
{% assign filtered = collection.products | where: "available", true %}

{% comment %} CORRETO: where nao existe em Liquid. Usar for com if {% endcomment %}
{% for product in collection.products %}
  {% if product.available %}
    {% render 'product-card', product: product %}
  {% endif %}
{% endfor %}
```

#### Section settings nao aparecem

- Verificar se o JSON no `{% schema %}` e valido.
- Verificar se `presets` esta declarado (necessario para sections adicionaveis).
- Verificar se o `type` do setting e valido.

### 5. Metafields nao aparecem

Checklist:
1. O metafield existe no admin? Verificar em Settings > Custom data.
2. O namespace e key estao corretos? (case-sensitive).
3. O metafield tem valor para este produto/colecao?
4. Em Hydrogen: o metafield esta na query GraphQL?

```liquid
{% comment %} Debug metafield {% endcomment %}
<pre>
  namespace: custom
  key: material
  value: {{ product.metafields.custom.material.value | json }}
  type: {{ product.metafields.custom.material.type }}
</pre>
```

### 6. Debugging Hydrogen

#### Erros de build

```bash
# Ver erros detalhados
shopify hydrogen dev --verbose

# Limpar cache
rm -rf node_modules/.cache
rm -rf .cache
```

#### Erros de hydration

Hydration mismatch acontece quando server e client renderizam HTML diferente.

Causas comuns:
- Usar `Date.now()` ou `Math.random()` em server component.
- Condicional baseada em `window` ou `navigator`.
- Extensoes de browser que modificam o DOM.

```typescript
// ERRADO: diferente no server e client
function MyComponent() {
  return <p>{new Date().toLocaleString()}</p>
}

// CORRETO: usar useEffect para valores dinamicos no client
'use client'
import { useState, useEffect } from 'react'

function MyComponent() {
  const [time, setTime] = useState<string>()

  useEffect(() => {
    setTime(new Date().toLocaleString())
  }, [])

  return <p>{time ?? 'Carregando...'}</p>
}
```

#### Erros na Storefront API

```typescript
// Sempre verificar erros na resposta
const { product, errors } = await storefront.query(QUERY, {
  variables: { handle },
})

if (errors) {
  console.error('Storefront API errors:', errors)
  throw new Error('Failed to fetch product')
}

if (!product) {
  throw new Response('Not found', { status: 404 })
}
```

### 7. Console do navegador

Verificar:
- **Console** — Erros JavaScript, warnings de hydration.
- **Network** — Requests GraphQL falhando, status codes.
- **Elements** — HTML renderizado vs esperado.
- **Application** — Cookies, localStorage, cart token.

## Common mistakes

1. **Deixar `| json` em producao** — Debug output visivel para o usuario. Sempre remover.
2. **Nao usar `shopify theme check`** — A ferramenta pega a maioria dos erros antes de subir.
3. **Testar so no desktop** — Sempre verificar mobile. Layout quebra frequentemente em telas pequenas.
4. **Ignorar nil checks** — Liquid nao da erro em nil, simplesmente nao renderiza. Verificar explicitamente.
5. **Debug em tema publicado** — Sempre usar preview ou tema de desenvolvimento.
6. **Nao verificar API version** — Queries que funcionavam podem quebrar em versoes novas da API.
