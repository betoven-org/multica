---
name: graphql-resolver
description: Como implementar GraphQL resolvers em VTEX IO com schema, Service class e diretivas de cache/auth.
---

# GraphQL Resolvers em VTEX IO

Como criar endpoints GraphQL customizados em apps VTEX IO backend, com schema, resolvers, cache e autenticacao.

## Quando usar

- Para expor dados customizados ao storefront via GraphQL.
- Para agregar dados de APIs externas ou Master Data.
- Para criar mutations que modificam dados no backend.

## Steps

### 1. Estrutura de arquivos

```
my-app/
  manifest.json
  graphql/
    schema.graphql
    types/
      Product.graphql
  node/
    index.ts
    resolvers/
      index.ts
      productResolver.ts
    clients/
      index.ts
      catalogClient.ts
```

### 2. Definir o schema GraphQL

```graphql
# graphql/schema.graphql
type Query {
  customProduct(slug: String!): CustomProduct
    @cacheControl(maxAge: SHORT, scope: PUBLIC)

  myPrivateData: PrivateData
    @cacheControl(maxAge: NONE, scope: PRIVATE)
    @auth
}

type Mutation {
  saveReview(input: ReviewInput!): ReviewResponse
    @auth
}
```

```graphql
# graphql/types/Product.graphql
type CustomProduct {
  id: ID!
  name: String!
  price: Float!
  availableQuantity: Int!
  images: [ProductImage!]!
}

type ProductImage {
  imageUrl: String!
  imageLabel: String
}

input ReviewInput {
  productId: String!
  rating: Int!
  text: String!
}

type ReviewResponse {
  id: String!
  success: Boolean!
}

type PrivateData {
  userId: String!
  wishlist: [String!]!
}
```

### 3. Implementar os resolvers

```typescript
// node/resolvers/productResolver.ts
import type { Context } from '../index'

export const productResolver = {
  Query: {
    customProduct: async (
      _root: unknown,
      args: { slug: string },
      ctx: Context
    ) => {
      const {
        clients: { catalog },
        vtex: { logger },
      } = ctx

      try {
        const product = await catalog.getProductBySlug(args.slug)

        return {
          id: product.productId,
          name: product.productName,
          price: product.items[0]?.sellers[0]?.commertialOffer?.Price ?? 0,
          availableQuantity:
            product.items[0]?.sellers[0]?.commertialOffer?.AvailableQuantity ?? 0,
          images: product.items[0]?.images?.map((img: any) => ({
            imageUrl: img.imageUrl,
            imageLabel: img.imageLabel,
          })) ?? [],
        }
      } catch (error) {
        logger.error({
          message: 'Error fetching custom product',
          slug: args.slug,
          error,
        })

        throw new Error('Product not found')
      }
    },
  },

  Mutation: {
    saveReview: async (
      _root: unknown,
      args: { input: { productId: string; rating: number; text: string } },
      ctx: Context
    ) => {
      const { masterdata } = ctx.clients
      const { sessionData } = ctx.vtex

      const doc = await masterdata.createDocument({
        dataEntity: 'RV',
        fields: {
          productId: args.input.productId,
          rating: args.input.rating,
          text: args.input.text,
          userId: sessionData?.namespaces?.profile?.id?.value,
        },
      })

      return { id: doc.DocumentId, success: true }
    },
  },
}
```

### 4. Registrar resolvers no index

```typescript
// node/resolvers/index.ts
import { productResolver } from './productResolver'

export const resolvers = {
  Query: {
    ...productResolver.Query,
  },
  Mutation: {
    ...productResolver.Mutation,
  },
}
```

### 5. Configurar Service class

```typescript
// node/index.ts
import type {
  ServiceContext,
  RecorderState,
  ParamsContext,
} from '@vtex/api'
import { Service, LRUCache, method } from '@vtex/api'

import { Clients } from './clients'
import { resolvers } from './resolvers'

const TREE_SECONDS_MS = 3 * 1000
const CONCURRENCY = 10

const memoryCache = new LRUCache<string, unknown>({
  max: 5000,
})

declare global {
  type Context = ServiceContext<Clients>
}

export { Context }

export default new Service<Clients, RecorderState, ParamsContext>({
  clients: {
    implementation: Clients,
    options: {
      default: {
        retries: 2,
        timeout: TREE_SECONDS_MS,
        concurrency: CONCURRENCY,
        memoryCache,
      },
    },
  },
  graphql: {
    resolvers,
  },
})
```

### 6. manifest.json — builders e policies

```json
{
  "builders": {
    "node": "7.x",
    "graphql": "1.x"
  },
  "policies": [
    {
      "name": "outbound-access",
      "attrs": {
        "host": "api.external-service.com",
        "path": "/*"
      }
    },
    {
      "name": "ADMIN_DS"
    },
    {
      "name": "vbase-read-write"
    }
  ]
}
```

## Diretivas importantes

| Diretiva | Uso |
|----------|-----|
| `@cacheControl(maxAge: SHORT, scope: PUBLIC)` | Cache publico, ~30s. Para dados nao sensíveis. |
| `@cacheControl(maxAge: MEDIUM)` | ~5min. Para dados que mudam pouco. |
| `@cacheControl(maxAge: LONG)` | ~30min. Para dados quase estaticos. |
| `@cacheControl(maxAge: NONE, scope: PRIVATE)` | Sem cache, dados sensíveis por usuario. |
| `@auth` | Requer usuario autenticado. Retorna 401 se nao logado. |

## Common mistakes

1. **Esquecer `@cacheControl`** — Sem diretiva, o cache e imprevisível. Sempre declare.
2. **Cache PUBLIC em dados de usuario** — Dados pessoais DEVEM usar `scope: PRIVATE` ou `maxAge: NONE`.
3. **Nao tratar erros no resolver** — Erros nao tratados resultam em 500 generico. Sempre use try/catch com logger.
4. **Resolver retornando formato diferente do schema** — Os campos retornados devem corresponder exatamente ao type GraphQL.
5. **Esquecer policies no manifest** — Requests a APIs externas falham silenciosamente sem `outbound-access`.
6. **Timeout curto demais** — O default de 3s pode nao ser suficiente para APIs lentas. Ajuste por client.
7. **Nao usar LRUCache** — O memory cache reduz drasticamente chamadas repetidas. Sempre configure.
