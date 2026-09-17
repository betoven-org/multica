---
name: graphql-query
description: Como construir queries na Storefront API da Shopify — fragments, paginacao, metafields e validacao.
---

# Storefront API Queries — Shopify

Como construir queries GraphQL eficientes para a Storefront API da Shopify, com fragments, paginacao e metafields.

## Quando usar

- Em qualquer projeto Shopify headless (Hydrogen, Next.js, custom).
- Para buscar produtos, colecoes, paginas, metafields.
- Para operacoes de carrinho (mutations).

## Steps

### 1. Query basica de produto

```graphql
query Product($handle: String!) {
  product(handle: $handle) {
    id
    title
    handle
    description
    descriptionHtml
    vendor
    productType
    tags
    publishedAt
    featuredImage {
      url
      altText
      width
      height
    }
    priceRange {
      minVariantPrice {
        amount
        currencyCode
      }
      maxVariantPrice {
        amount
        currencyCode
      }
    }
    variants(first: 10) {
      nodes {
        id
        title
        availableForSale
        quantityAvailable
        price {
          amount
          currencyCode
        }
        compareAtPrice {
          amount
          currencyCode
        }
        selectedOptions {
          name
          value
        }
        image {
          url
          altText
          width
          height
        }
      }
    }
    options {
      name
      values
    }
    seo {
      title
      description
    }
  }
}
```

### 2. Usar fragments para reutilizar campos

```graphql
fragment MoneyFragment on MoneyV2 {
  amount
  currencyCode
}

fragment ImageFragment on Image {
  url
  altText
  width
  height
}

fragment ProductCardFragment on Product {
  id
  title
  handle
  featuredImage {
    ...ImageFragment
  }
  priceRange {
    minVariantPrice {
      ...MoneyFragment
    }
  }
  variants(first: 1) {
    nodes {
      id
      availableForSale
      price {
        ...MoneyFragment
      }
      compareAtPrice {
        ...MoneyFragment
      }
    }
  }
}

query CollectionProducts($handle: String!, $first: Int!) {
  collection(handle: $handle) {
    title
    products(first: $first) {
      nodes {
        ...ProductCardFragment
      }
    }
  }
}
```

### 3. Paginacao com cursor

```graphql
query Products(
  $first: Int
  $last: Int
  $after: String
  $before: String
  $sortKey: ProductSortKeys
  $reverse: Boolean
  $query: String
) {
  products(
    first: $first
    last: $last
    after: $after
    before: $before
    sortKey: $sortKey
    reverse: $reverse
    query: $query
  ) {
    nodes {
      ...ProductCardFragment
    }
    pageInfo {
      hasNextPage
      hasPreviousPage
      startCursor
      endCursor
    }
  }
}
```

Uso em codigo:

```typescript
// Primeira pagina
const { products } = await storefront.query(PRODUCTS_QUERY, {
  variables: { first: 12, sortKey: 'BEST_SELLING' },
})

// Proxima pagina
const { products: nextPage } = await storefront.query(PRODUCTS_QUERY, {
  variables: {
    first: 12,
    after: products.pageInfo.endCursor,
  },
})

// Pagina anterior
const { products: prevPage } = await storefront.query(PRODUCTS_QUERY, {
  variables: {
    last: 12,
    before: products.pageInfo.startCursor,
  },
})
```

### 4. Metafields

```graphql
query ProductWithMetafields($handle: String!) {
  product(handle: $handle) {
    id
    title

    # Metafield unico
    specifications: metafield(namespace: "custom", key: "specifications") {
      value
      type
    }

    # Metafield de referencia (arquivo, produto, etc)
    sizeGuide: metafield(namespace: "custom", key: "size_guide") {
      reference {
        ... on MediaImage {
          image {
            url
            altText
            width
            height
          }
        }
      }
    }

    # Lista de metafields
    metafields(identifiers: [
      { namespace: "custom", key: "material" },
      { namespace: "custom", key: "care_instructions" },
      { namespace: "custom", key: "warranty_months" }
    ]) {
      key
      value
      type
    }
  }
}
```

Parsear valores de metafield:

```typescript
function parseMetafieldValue(metafield: { value: string; type: string }) {
  switch (metafield.type) {
    case 'number_integer':
      return parseInt(metafield.value, 10)
    case 'number_decimal':
      return parseFloat(metafield.value)
    case 'boolean':
      return metafield.value === 'true'
    case 'json':
      return JSON.parse(metafield.value)
    case 'list.single_line_text_field':
      return JSON.parse(metafield.value) as string[]
    default:
      return metafield.value
  }
}
```

### 5. Filtros de colecao

```graphql
query CollectionWithFilters(
  $handle: String!
  $filters: [ProductFilter!]
  $sortKey: ProductCollectionSortKeys
  $reverse: Boolean
  $first: Int!
) {
  collection(handle: $handle) {
    title
    products(
      first: $first
      filters: $filters
      sortKey: $sortKey
      reverse: $reverse
    ) {
      filters {
        id
        label
        type
        values {
          id
          label
          count
          input
        }
      }
      nodes {
        ...ProductCardFragment
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

### 6. Mutations de carrinho

```graphql
mutation CartCreate($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
      totalQuantity
      lines(first: 100) {
        nodes {
          id
          quantity
          merchandise {
            ... on ProductVariant {
              id
              title
              price {
                amount
                currencyCode
              }
              product {
                title
                handle
              }
            }
          }
        }
      }
      cost {
        totalAmount {
          amount
          currencyCode
        }
        subtotalAmount {
          amount
          currencyCode
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}

mutation CartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
  cartLinesAdd(cartId: $cartId, lines: $lines) {
    cart {
      id
      totalQuantity
    }
    userErrors {
      field
      message
    }
  }
}
```

### 7. Validar queries

```bash
# Usar Shopify CLI para validar
shopify hydrogen codegen

# Ou testar no GraphiQL
# https://{store}.myshopify.com/api/2024-01/graphql.json
# Header: X-Shopify-Storefront-Access-Token: {token}
```

## Common mistakes

1. **Overfetching** — Buscar todos os campos quando precisa de poucos. Sempre limitar campos e usar `first: N`.
2. **Nao usar fragments** — Repetir campos em multiplas queries. Extrair em fragments reutilizaveis.
3. **Paginacao sem cursor** — Usar offset-based pagination nao e suportado. Sempre usar cursor-based.
4. **Ignorar `userErrors`** — Mutations retornam `userErrors` com detalhes. Sempre verificar.
5. **Metafield sem type check** — O `value` e sempre string. Parsear de acordo com o `type`.
6. **API version hardcoded** — Usar a versao configurada no Hydrogen/client, nao hardcodar.
7. **Nao usar `as const`** — Em Hydrogen, queries devem ter `as const` para codegen funcionar.
8. **Query muito pesada** — A Storefront API tem rate limiting por complexidade. Queries com muitos nodes podem falhar.
