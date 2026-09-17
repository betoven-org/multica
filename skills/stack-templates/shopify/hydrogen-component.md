---
name: hydrogen-component
description: Como criar componentes em Shopify Hydrogen — server components, loaders, Storefront API e client components.
---

# Componentes em Shopify Hydrogen

Como criar componentes no Hydrogen (Remix-based), usando server components por padrao e client components apenas quando necessario.

## Quando usar

- Em projetos Shopify headless com Hydrogen.
- Para paginas que precisam de dados da Storefront API.
- Para componentes interativos que requerem estado no cliente.

## Steps

### 1. Server Component (padrao)

Todo componente e server component por padrao. Nao precisa de declaracao especial.

```typescript
// app/components/ProductCard.tsx
import { Image, Money } from '@shopify/hydrogen'
import type { ProductItemFragment } from 'storefrontapi.generated'

interface ProductCardProps {
  product: ProductItemFragment
  loading?: 'eager' | 'lazy'
}

export function ProductCard({ product, loading = 'lazy' }: ProductCardProps) {
  const firstVariant = product.variants.nodes[0]
  const image = product.featuredImage

  return (
    <a href={`/products/${product.handle}`} className="product-card">
      {image && (
        <Image
          data={image}
          aspectRatio="1/1"
          sizes="(min-width: 45em) 20vw, 50vw"
          loading={loading}
        />
      )}
      <div className="product-card__info">
        <h3 className="product-card__title">{product.title}</h3>
        {firstVariant?.price && (
          <Money
            data={firstVariant.price}
            className="product-card__price"
          />
        )}
      </div>
    </a>
  )
}
```

### 2. Route com loader (dados da Storefront API)

```typescript
// app/routes/collections.$handle.tsx
import { defer, type LoaderFunctionArgs } from '@shopify/remix-oxygen'
import { useLoaderData, Await } from '@remix-run/react'
import { Suspense } from 'react'
import { getPaginationVariables } from '@shopify/hydrogen'

import { ProductCard } from '~/components/ProductCard'

export async function loader(args: LoaderFunctionArgs) {
  const { handle } = args.params
  const { storefront } = args.context

  const paginationVariables = getPaginationVariables(args.request, {
    pageBy: 12,
  })

  const { collection } = await storefront.query(COLLECTION_QUERY, {
    variables: { handle: handle!, ...paginationVariables },
  })

  if (!collection) {
    throw new Response('Collection not found', { status: 404 })
  }

  return defer({ collection })
}

export default function CollectionPage() {
  const { collection } = useLoaderData<typeof loader>()

  return (
    <div className="collection">
      <h1>{collection.title}</h1>
      {collection.description && (
        <p className="collection__description">{collection.description}</p>
      )}

      <div className="collection__grid">
        {collection.products.nodes.map((product, index) => (
          <ProductCard
            key={product.id}
            product={product}
            loading={index < 4 ? 'eager' : 'lazy'}
          />
        ))}
      </div>
    </div>
  )
}

const COLLECTION_QUERY = `#graphql
  query Collection(
    $handle: String!
    $first: Int
    $last: Int
    $startCursor: String
    $endCursor: String
  ) {
    collection(handle: $handle) {
      id
      handle
      title
      description
      products(
        first: $first
        last: $last
        before: $startCursor
        after: $endCursor
      ) {
        nodes {
          id
          title
          handle
          featuredImage {
            url
            altText
            width
            height
          }
          variants(first: 1) {
            nodes {
              price {
                amount
                currencyCode
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          hasPreviousPage
          startCursor
          endCursor
        }
      }
    }
  }
` as const
```

### 3. Client Component (interatividade)

Usar `'use client'` APENAS quando precisa de estado, efeitos ou event handlers no browser.

```typescript
// app/components/AddToCartButton.tsx
'use client'

import { useState } from 'react'
import { useFetcher } from '@remix-run/react'

interface AddToCartButtonProps {
  variantId: string
  availableForSale: boolean
}

export function AddToCartButton({
  variantId,
  availableForSale,
}: AddToCartButtonProps) {
  const fetcher = useFetcher()
  const [quantity, setQuantity] = useState(1)

  const isAdding = fetcher.state !== 'idle'

  return (
    <fetcher.Form method="post" action="/cart">
      <input type="hidden" name="cartAction" value="ADD_TO_CART" />
      <input type="hidden" name="variantId" value={variantId} />

      <div className="add-to-cart__quantity">
        <button
          type="button"
          onClick={() => setQuantity((q) => Math.max(1, q - 1))}
          aria-label="Diminuir quantidade"
        >
          -
        </button>
        <input
          type="number"
          name="quantity"
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
          min="1"
        />
        <button
          type="button"
          onClick={() => setQuantity((q) => q + 1)}
          aria-label="Aumentar quantidade"
        >
          +
        </button>
      </div>

      <button
        type="submit"
        disabled={!availableForSale || isAdding}
        className="add-to-cart__button"
      >
        {!availableForSale
          ? 'Esgotado'
          : isAdding
            ? 'Adicionando...'
            : 'Adicionar ao carrinho'}
      </button>
    </fetcher.Form>
  )
}
```

### 4. Combinar server e client components

```typescript
// app/routes/products.$handle.tsx (server component)
import { AddToCartButton } from '~/components/AddToCartButton'

export default function ProductPage() {
  const { product } = useLoaderData<typeof loader>()
  const firstVariant = product.variants.nodes[0]

  return (
    <div className="product">
      {/* Server-rendered content */}
      <h1>{product.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: product.descriptionHtml }} />

      {/* Client component — island de interatividade */}
      <AddToCartButton
        variantId={firstVariant.id}
        availableForSale={firstVariant.availableForSale}
      />
    </div>
  )
}
```

## Common mistakes

1. **Marcar tudo como `'use client'`** — Apenas componentes que PRECISAM de estado/efeitos devem ser client. Server e o padrao.
2. **Fetch no client component** — Buscar dados no loader (server), nao no useEffect (client).
3. **Nao usar `defer`** — Para dados secundarios, usar `defer` permite streaming e melhora TTFB.
4. **Queries sem tipagem** — Usar codegen para gerar tipos: `storefrontapi.generated.ts`.
5. **Imagens sem Image component** — O `<Image>` do Hydrogen otimiza automaticamente (srcset, sizes, lazy).
6. **Nao tratar 404** — Sempre verificar se o recurso existe e retornar `Response` com status correto.
7. **Passar dados sensíveis ao client** — Tokens e secrets so existem no loader (server). Nunca expor ao client.
8. **Esquecer `as const` na query** — Necessario para tipagem correta com codegen.
