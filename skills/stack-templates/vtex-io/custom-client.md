---
name: custom-client
description: Como criar clientes de API customizados em VTEX IO — ExternalClient, JanusClient, IOClients.
---

# Custom API Clients em VTEX IO

Como criar clientes HTTP customizados para integrar APIs externas ou internas no backend VTEX IO.

## Quando usar

- Integrar API externa (ERP, CRM, gateway de pagamento).
- Acessar APIs internas da VTEX via JanusClient.
- Encapsular chamadas HTTP com tipagem, retry e cache.

## Steps

### 1. Estrutura de arquivos

```
node/
  clients/
    index.ts          # IOClients class
    myApiClient.ts     # ExternalClient customizado
    catalogClient.ts   # JanusClient para APIs VTEX
```

### 2. ExternalClient — APIs externas

```typescript
// node/clients/myApiClient.ts
import type { InstanceOptions, IOContext } from '@vtex/api'
import { ExternalClient } from '@vtex/api'

interface ProductResponse {
  id: string
  name: string
  price: number
}

interface CreateOrderPayload {
  items: Array<{ sku: string; quantity: number }>
  customer: { email: string; name: string }
}

interface OrderResponse {
  orderId: string
  status: string
}

export class MyApiClient extends ExternalClient {
  constructor(ctx: IOContext, options?: InstanceOptions) {
    super('http://api.external-service.com', ctx, {
      ...options,
      headers: {
        ...options?.headers,
        'Content-Type': 'application/json',
        'X-Api-Key': ctx.authToken, // ou usar settings da app
      },
      retries: 2,
      timeout: 5000,
    })
  }

  public async getProduct(productId: string): Promise<ProductResponse> {
    return this.http.get<ProductResponse>(`/products/${productId}`, {
      metric: 'my-api-get-product',
    })
  }

  public async createOrder(payload: CreateOrderPayload): Promise<OrderResponse> {
    return this.http.post<OrderResponse>('/orders', payload, {
      metric: 'my-api-create-order',
    })
  }

  public async updateProduct(
    productId: string,
    data: Partial<ProductResponse>
  ): Promise<ProductResponse> {
    return this.http.put<ProductResponse>(`/products/${productId}`, data, {
      metric: 'my-api-update-product',
    })
  }

  public async deleteProduct(productId: string): Promise<void> {
    return this.http.delete(`/products/${productId}`, {
      metric: 'my-api-delete-product',
    })
  }
}
```

### 3. JanusClient — APIs internas VTEX

```typescript
// node/clients/catalogClient.ts
import type { InstanceOptions, IOContext } from '@vtex/api'
import { JanusClient } from '@vtex/api'

interface VtexProduct {
  productId: string
  productName: string
  items: Array<{
    itemId: string
    sellers: Array<{
      commertialOffer: {
        Price: number
        AvailableQuantity: number
      }
    }>
    images: Array<{
      imageUrl: string
      imageLabel: string
    }>
  }>
}

export class CatalogClient extends JanusClient {
  constructor(ctx: IOContext, options?: InstanceOptions) {
    super(ctx, {
      ...options,
      headers: {
        ...options?.headers,
        VtexIdclientAutCookie: ctx.authToken,
      },
    })
  }

  public async getProductBySlug(slug: string): Promise<VtexProduct> {
    return this.http.get<VtexProduct>(
      `/api/catalog_system/pub/products/search/${slug}`,
      {
        metric: 'catalog-get-product-by-slug',
      }
    )
  }

  public async getProductById(id: string): Promise<VtexProduct> {
    return this.http.get<VtexProduct>(
      `/api/catalog/pvt/product/${id}`,
      {
        metric: 'catalog-get-product-by-id',
      }
    )
  }
}
```

### 4. Registrar no IOClients

```typescript
// node/clients/index.ts
import { IOClients } from '@vtex/api'

import { MyApiClient } from './myApiClient'
import { CatalogClient } from './catalogClient'

export class Clients extends IOClients {
  public get myApi() {
    return this.getOrSet('myApi', MyApiClient)
  }

  public get catalog() {
    return this.getOrSet('catalog', CatalogClient)
  }
}
```

### 5. Usar nos resolvers ou middlewares

```typescript
// node/resolvers/productResolver.ts
export const productResolver = {
  Query: {
    externalProduct: async (_root: unknown, args: { id: string }, ctx: Context) => {
      // Acesso via ctx.clients
      const product = await ctx.clients.myApi.getProduct(args.id)
      return product
    },
  },
}
```

### 6. Configurar options por client no Service

```typescript
// node/index.ts
export default new Service<Clients, RecorderState, ParamsContext>({
  clients: {
    implementation: Clients,
    options: {
      default: {
        retries: 2,
        timeout: 3000,
        concurrency: 10,
      },
      // Override especifico para um client lento
      myApi: {
        retries: 3,
        timeout: 10000,
        concurrency: 5,
      },
    },
  },
  graphql: { resolvers },
})
```

### 7. Policy no manifest.json

```json
{
  "policies": [
    {
      "name": "outbound-access",
      "attrs": {
        "host": "api.external-service.com",
        "path": "/*"
      }
    },
    {
      "name": "outbound-access",
      "attrs": {
        "host": "{{account}}.vtexcommercestable.com.br",
        "path": "/api/*"
      }
    }
  ]
}
```

## Common mistakes

1. **Nao adicionar `outbound-access`** — O request falha silenciosamente com 403. Sempre adicionar para cada host externo.
2. **Timeout curto para APIs lentas** — O default de 3s pode nao ser suficiente. Configurar por client.
3. **Nao usar `metric`** — O parametro `metric` e obrigatorio para monitoramento. Sempre passar.
4. **Usar authToken em API externa** — `ctx.authToken` e o token VTEX. Para APIs externas, use app settings ou secrets.
5. **Esquecer tipagem no retorno** — Sempre tipar generics: `this.http.get<MyType>(...)`.
6. **Client sem retry** — APIs externas falham. Sempre configurar pelo menos 1 retry.
7. **Nao usar `getOrSet`** — Sem `getOrSet`, uma nova instancia e criada a cada request. Sempre usar o padrao de getter com `getOrSet`.
