---
name: performance
description: Otimizacao de performance em VTEX IO — cache, bundle, lazy load, imagens e GraphQL.
---

# Performance em VTEX IO

Tecnicas para otimizar performance de lojas VTEX IO, focando em Core Web Vitals (LCP, CLS, INP).

## Quando usar

- Sempre. Performance deve ser considerada em todo componente e resolver.
- Especialmente ao criar componentes acima do fold.
- Quando metricas do PageSpeed/Lighthouse estao abaixo do aceitavel.

## Steps

### 1. GraphQL — evitar overfetching

```graphql
# ERRADO: buscar tudo
query {
  productsByIdentifier(field: id, values: ["123"]) {
    # ... 50 campos que nao preciso
  }
}

# CORRETO: buscar apenas o necessario
query {
  productsByIdentifier(field: id, values: ["123"]) {
    productId
    productName
    items {
      itemId
      images(quantity: 1) {
        imageUrl
      }
      sellers(first: 1) {
        commertialOffer {
          Price
        }
      }
    }
  }
}
```

### 2. @cacheControl nas queries

Sempre declarar cache no schema GraphQL:

```graphql
type Query {
  # Dados publicos, muda pouco — cache medio
  productList(category: String!): [Product!]!
    @cacheControl(maxAge: MEDIUM, scope: PUBLIC)

  # Dados de sessao — sem cache
  userWishlist: [String!]!
    @cacheControl(maxAge: NONE, scope: PRIVATE)
    @auth

  # Dados quase estaticos — cache longo
  storeConfig: StoreConfig!
    @cacheControl(maxAge: LONG, scope: PUBLIC)
}
```

| Diretiva | Duracao aproximada |
|----------|-------------------|
| SHORT    | ~30 segundos      |
| MEDIUM   | ~5 minutos        |
| LONG     | ~30 minutos       |
| NONE     | Sem cache         |

### 3. Minimizar JS bundle

```typescript
// ERRADO: importar biblioteca inteira
import _ from 'lodash'
const result = _.get(obj, 'a.b.c')

// CORRETO: importar apenas a funcao
import get from 'lodash/get'
const result = get(obj, 'a.b.c')

// MELHOR: usar optional chaining nativo
const result = obj?.a?.b?.c
```

Evitar dependencias pesadas. Verificar tamanho com:
```bash
# No package.json do react/
npx bundlephobia lodash    # 71kB
npx bundlephobia lodash/get # 1kB
```

### 4. Lazy load de componentes

```typescript
import React, { lazy, Suspense } from 'react'

// Componente pesado carregado sob demanda
const HeavyChart = lazy(() => import('./HeavyChart'))

const Dashboard: React.FC = () => {
  return (
    <div>
      <h1>Dashboard</h1>
      <Suspense fallback={<div className="loading-skeleton" />}>
        <HeavyChart />
      </Suspense>
    </div>
  )
}
```

### 5. Imagens — SEMPRE com dimensoes

```typescript
// ERRADO: sem dimensoes = CLS
<img src={imageUrl} alt={name} />

// CORRETO: dimensoes explicitas
<img
  src={imageUrl}
  alt={name}
  width={300}
  height={300}
  loading="lazy"
/>
```

Para imagens acima do fold, NAO usar `loading="lazy"`:

```typescript
// Acima do fold — carregamento imediato
<img
  src={imageUrl}
  alt={name}
  width={600}
  height={400}
  loading="eager"
  fetchpriority="high"
/>
```

Usar parametros de redimensionamento da VTEX:

```typescript
// Redimensionar via URL
const optimizedUrl = `${imageUrl}?width=300&height=300&aspect=true`
```

### 6. Evitar re-renders desnecessarios

```typescript
import React, { useMemo, useCallback } from 'react'

const ProductList: React.FC<{ products: Product[] }> = ({ products }) => {
  // Memoizar computacoes caras
  const sortedProducts = useMemo(
    () => products.sort((a, b) => a.price - b.price),
    [products]
  )

  // Memoizar callbacks passados como props
  const handleClick = useCallback((id: string) => {
    // ...
  }, [])

  return (
    <div>
      {sortedProducts.map((p) => (
        <ProductCard key={p.id} product={p} onClick={handleClick} />
      ))}
    </div>
  )
}

// Memoizar componente filho
const ProductCard = React.memo<{ product: Product; onClick: (id: string) => void }>(
  ({ product, onClick }) => {
    // ...
  }
)
```

### 7. Prefetch de dados criticos

No store-theme, usar `prefetch` em blocos criticos:

```json
{
  "store.home": {
    "blocks": ["shelf#home"]
  },
  "shelf#home": {
    "props": {
      "prefetch": true,
      "maxItems": 8
    }
  }
}
```

### 8. LRUCache no backend

```typescript
import { LRUCache } from '@vtex/api'

const memoryCache = new LRUCache<string, unknown>({
  max: 5000,
})

// Usar no Service
export default new Service({
  clients: {
    options: {
      default: {
        memoryCache,
      },
    },
  },
})
```

## Common mistakes

1. **Sem `@cacheControl`** — Queries sem cache geram requests repetidos ao backend.
2. **Imagens sem width/height** — Causa CLS (Cumulative Layout Shift), penaliza Core Web Vitals.
3. **Lazy load em imagens acima do fold** — Atrasa LCP. Usar `loading="eager"` + `fetchpriority="high"`.
4. **Importar bibliotecas inteiras** — Tree-shaking nem sempre funciona. Importar submodulos.
5. **GraphQL overfetching** — Buscar 50 campos quando precisa de 5. Sempre limitar campos.
6. **Nao usar `React.memo`** — Listas grandes re-renderizam filhos desnecessariamente.
7. **Nao usar LRUCache** — Mesmo com `@cacheControl`, o memory cache evita chamadas HTTP repetidas.
8. **Fontes customizadas sem preload** — Adicionar `<link rel="preload">` para fontes criticas.
