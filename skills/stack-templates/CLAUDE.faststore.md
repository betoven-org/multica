# FastStore — Convenções do Projeto

## Stack

- Framework: VTEX FastStore (Next.js)
- UI: React + TypeScript
- Estilo: CSS Modules / Tailwind
- Data: VTEX Intelligent Search + Checkout API
- BFF: GraphQL extensions

## MCP Servers disponíveis

### vtex-developer
```
- search_documentation(query) → Busca doc VTEX
- search_endpoints(query) → Lista endpoints
- get_endpoint_details(id) → Detalhes endpoint
```

**Use sempre antes de criar fetchers custom.**

## Arquitetura FastStore

### Section Overrides (preferência #1)
Sempre prefira override de sections existentes a criar componentes do zero.

```tsx
// src/components/overrides/ProductShelf/index.tsx
import { SectionOverride } from "@faststore/core"

const override: SectionOverride = {
  section: "ProductShelf",
  components: {
    ProductCard: {
      Component: CustomProductCard,
      props: { showBadge: true },
    },
  },
}

export default override
```

### Sections custom (quando override não basta)
```tsx
// src/components/sections/CustomBanner/index.tsx
export interface CustomBannerProps {
  title: string
  image: { src: string; alt: string }
  cta?: { text: string; url: string }
}

export default function CustomBanner({ title, image, cta }: CustomBannerProps) {
  return (
    <section>
      <img src={image.src} alt={image.alt} width={1200} height={400} loading="lazy" />
      <h2>{title}</h2>
      {cta && <a href={cta.url}>{cta.text}</a>}
    </section>
  )
}
```

### BFF (Backend for Frontend)
```
src/
├── graphql/
│   ├── thirdParty/
│   │   ├── resolvers/          → Resolvers custom
│   │   └── typeDefs/           → Schema extensions
│   └── vtex/
│       ├── resolvers/          → Override resolvers VTEX
│       └── typeDefs/           → Extend schema VTEX
```

```ts
// src/graphql/thirdParty/resolvers/customQuery.ts
export const resolvers = {
  Query: {
    customData: async (_: unknown, args: { id: string }) => {
      const res = await fetch(`https://api.exemplo.com/data/${args.id}`)
      return res.json()
    },
  },
}
```

## Regras obrigatórias

### Performance (Core Web Vitals)
- LCP: imagens hero com `loading="eager"` e `fetchPriority="high"`
- CLS: SEMPRE width/height em imagens e mídia
- INP: sem JavaScript bloqueante no main thread
- Prefira section overrides a components novos (menos bundle)
- Sem CSS-in-JS — use CSS Modules ou Tailwind

### Dados
- Nunca chame APIs VTEX diretamente do browser
- Use o BFF (graphql/) pra proxy de APIs privadas
- APIs públicas (Intelligent Search, Catalog) podem ser cacheadas
- APIs privadas (Checkout, Profile) NUNCA cachear

### Caching
```
Pode cachear (TTL > 0):
- Intelligent Search (product_search, facets)
- Catalog API (products, categories, brands)
- CMS content

NUNCA cachear:
- Checkout API (orderForm)
- Profile API (user data)
- OMS API (orders)
- Session API
```

### Estilo
- Use CSS Handles do FastStore quando disponíveis
- CSS Modules pra componentes custom
- Variáveis de design tokens do tema
- Sem `!important`
- Sem estilos globais (exceto tema)

## Checklist antes de PR

- [ ] Section override usado quando possível (vs componente novo)
- [ ] Imagens com width/height
- [ ] Loading lazy em imagens abaixo do fold
- [ ] Hero images com loading eager + fetchPriority high
- [ ] Sem fetch de API privada no client-side
- [ ] BFF pra dados que precisam de proxy
- [ ] Sem console.log
- [ ] Tipos completos (sem any)

## Não faça

- Não crie componentes novos quando um override resolve
- Não chame APIs privadas VTEX do browser
- Não cache dados de checkout/profile
- Não use CSS-in-JS
- Não importe libs pesadas no client bundle sem lazy load
- Não ignore Core Web Vitals
