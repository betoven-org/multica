# deco.cx — Convenções do Projeto

## Stack

- Runtime: Deno (TypeScript nativo)
- UI: Preact JSX (server-side) + HTMX (interatividade client-side)
- Estilo: Tailwind CSS
- Deploy: Deno Deploy / Cloudflare Workers

## MCP Server disponível

### deco MCP (se site está em produção)
O site deco expõe automaticamente um MCP server em `/mcp/messages`.
Loaders e Actions do projeto ficam disponíveis como tools.

```
Endpoint HTTP: https://site-do-cliente.com/mcp/messages
WebSocket: wss://site-do-cliente.com/mcp/ws
```

O agente pode invocar loaders/actions do site pra testar e validar:
- Listar tools: POST /mcp/messages com tools/list
- Executar tool: POST /mcp/messages com tools/call

## Arquitetura de Blocks (7 tipos)

### Loaders (dados, read-only, cacheáveis)
```ts
// loaders/productList.ts
export interface Props {
  count: number
  query?: string
}

export default async function loader(props: Props, _req: Request, ctx: FnContext) {
  return await ctx.state.api["GET /products"]({ limit: props.count })
}

export const cacheKey = (props: Props) => `products:${props.count}:${props.query ?? ""}`
export const cache = "stale-while-revalidate"
```

### Sections (UI, Preact, SSR)
```tsx
import type { ImageWidget, HTMLWidget } from "apps/admin/widgets.ts"

/** @title Configurações do Banner */
export interface Props {
  /** @description Imagem principal */
  image: ImageWidget
  /** @description Texto do banner */
  text?: HTMLWidget
  /** @description Alinhamento */
  alignment?: "left" | "center" | "right"
}

export default function Banner({ image, text, alignment = "center" }: Props) {
  return (
    <section class="container py-8" style={{ textAlign: alignment }}>
      <img src={image} width={1200} height={400} loading="lazy" alt="" />
      {text && <div dangerouslySetInnerHTML={{ __html: text }} />}
    </section>
  )
}
```

### Actions (mutations, nunca retornam JSX)
### Islands (interatividade client-side, usar mínimo)
### Handlers (rotas HTTP custom)
### Matchers (lógica de routing)
### Workflows (tarefas longas)

## Apps do ecossistema (deco-cx/apps)

Antes de criar loader/action, verifique se já existe:

| App | Integrações |
|-----|-------------|
| apps/vtex/ | Produtos, carrinho, pedidos, search |
| apps/shopify/ | Storefront API, collections |
| apps/nuvemshop/ | REST API |
| apps/analytics/ | GA4, Segment |
| apps/anthropic/ | Claude API |

**Client tipado:**
```ts
export interface MyClient {
  "GET /products/:id": { response: Product }
  "POST /orders": { body: OrderInput; response: Order }
}
const api = createHttpClient<MyClient>({ base: "https://..." })
```

## Regras obrigatórias

### Performance
- Width/height obrigatórios em imagens
- Lazy load em imagens abaixo do fold
- Sem CSS-in-JS — use Tailwind
- Loaders com fetch externo DEVEM ter cacheKey
- Cache strategies: "stale-while-revalidate", { maxAge: 3600 }, "no-cache"

### Qualidade
- Toda Section tem interface Props tipada
- Use @description JSDoc pra documentar props no editor
- Use ImageWidget pra imagens, HTMLWidget pra rich text
- Union types pra opções: "left" | "center" | "right"
- Sem imports de módulos Node.js (fs, path, dns — é Deno)
- Sem console.log em produção
- Sem `any`

### Islands (mínimo)
- APENAS quando precisa interatividade no browser
- Prefira HTMX (hx-get, hx-post, hx-swap) quando possível
- Islands aumentam bundle — minimize uso

### Estrutura
```
sections/    → UI components (SSR)
loaders/     → Data fetching (cacheável)
actions/     → Mutations
islands/     → Client-side interactivity (mínimo)
components/  → Componentes compartilhados
static/      → Assets estáticos
```

## Checklist antes de PR

- [ ] Loader com cacheKey se faz fetch externo
- [ ] Section com Props tipadas e @description
- [ ] Action não retorna JSX
- [ ] Islands usadas apenas quando necessário
- [ ] Imagens com width/height
- [ ] Sem imports Node.js
- [ ] Sem console.log
- [ ] Sem any

## Não faça

- Não use useState/useEffect em Sections (são SSR)
- Não faça fetch direto em Sections — use Loaders
- Não importe módulos Node.js
- Não crie islands pra conteúdo estático
- Não ignore cache — todo loader externo precisa de estratégia
- Não reinvente — verifique apps/ primeiro
