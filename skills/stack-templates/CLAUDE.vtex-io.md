# VTEX IO — Convenções do Projeto

## Stack

- Framework: VTEX IO Store Framework
- UI: React (TypeScript)
- Estilo: CSS Handles (useCssHandles)
- GraphQL: Apollo Client + resolvers em node/
- Backend: VTEX IO Node services (JanusClient, ExternalClient)
- i18n: messages/ (pt.json, en.json, es.json)

## MCP Servers disponíveis

### vtex-developer
```
- search_documentation(query) → Busca na doc VTEX
- search_endpoints(query) → Lista endpoints de API
- get_endpoint_details(endpoint_id) → Detalhes de um endpoint
- fetch_document(url) → Lê documento da VTEX
```

**USE SEMPRE antes de implementar qualquer feature.**

## Estrutura de um app VTEX IO

```
app-name/
├── manifest.json          # Metadados, builders, dependencies
├── store/                 # Blocos e configuração
│   ├── blocks.json       # Define blocos exportados
│   ├── interfaces.json   # Schema de props dos blocos
│   └── contentSchemas.json # Schemas para Site Editor
├── react/                 # Componentes React
│   ├── components/       # Componentes (.tsx)
│   ├── hooks/            # Custom hooks
│   ├── utils/            # Helpers
│   └── typings/          # Tipos TypeScript
├── node/                  # Backend (se aplicável)
│   ├── resolvers/        # GraphQL resolvers
│   ├── clients/          # API clients (JanusClient)
│   ├── index.ts          # Service entrypoint
│   └── service.json      # Config do service
├── messages/              # Internacionalização
│   ├── pt.json
│   ├── en.json
│   └── es.json
└── styles/                # CSS overrides
```

## Apps oficiais mais usados (vtex-apps)

Antes de criar algo do zero, verifique se já existe:

| App | Função |
|-----|--------|
| vtex.store-components | 18 componentes reutilizáveis |
| vtex.product-summary | Display de produto em shelves |
| vtex.search-result | PLP com galeria, filtros, paginação |
| vtex.minicart | Carrinho flutuante |
| vtex.store-header | Barra de navegação |
| vtex.store-footer | Footer com links e pagamentos |
| vtex.menu | Menu de navegação |
| vtex.flex-layout | Sistema de layout (rows/cols) |
| vtex.store-graphql | GraphQL: categorias, shipping, orders |
| vtex.search-graphql | GraphQL schema para search |
| vtex.list-context | Context provider para listas |

## Regras obrigatórias

### CSS Handles (SEMPRE)
```tsx
const CSS_HANDLES = ['container', 'title', 'price', 'image'] as const

function ProductCard() {
  const handles = useCssHandles(CSS_HANDLES)
  return (
    <div className={handles.container}>
      <h3 className={handles.title}>...</h3>
    </div>
  )
}
```
- NUNCA inline styles
- NUNCA className sem handles
- Handles descritivos (priceContainer, não pc)

### Componentes React
- Funcionais apenas (sem class components)
- TypeScript strict (sem `any`)
- Width/height obrigatórios em imagens
- Lazy load em imagens abaixo do fold
- Lógica de negócio em hooks/utils, não no componente
- Context patterns: useProduct(), useRuntime(), useListContext()

### Backend (node/)
- Use `ctx.clients` pra APIs VTEX (nunca fetch direto)
- Lógica em services, não em middlewares
- Validação de input com Zod
- Erros com mensagens descritivas
- `ctx.vtex.authToken` pra autenticação

### GraphQL
- Schema em `graphql/schema.graphql`
- Resolvers em `node/resolvers/`
- `@cacheControl` pra queries cacheáveis
- `@auth` pra queries autenticadas
- NUNCA breaking changes sem deprecation

### Blocks e Interfaces
- Novo bloco → adicionar em `blocks.json` + `interfaces.json`
- Props tipadas em `interfaces.json`
- Admin hints em `contentSchemas.json`
- Allowed children em `blocks.json`

### i18n
- Toda string visível em `messages/` (pt.json + en.json)
- Usar `<FormattedMessage id="key" />`
- Nunca hardcodar textos

### manifest.json
- Declare todas as policies (outbound-access)
- Dependencies explícitas com `x.y` versioning
- Sem dependências circulares

## Checklist antes de PR

- [ ] CSS Handles em todos os elementos
- [ ] Sem inline styles
- [ ] Imagens com width/height
- [ ] TypeScript strict (sem any)
- [ ] i18n em pt.json + en.json
- [ ] manifest.json com version incrementada
- [ ] blocks.json e interfaces.json atualizados
- [ ] Sem console.log
- [ ] ESLint passando
- [ ] Testado no workspace (vtex link)

## Workflow com MCP

1. `search_documentation("feature")` — verificar se já existe
2. `search_endpoints("recurso")` — encontrar APIs disponíveis
3. `get_endpoint_details(id)` — ler detalhes da API
4. Implementar seguindo as convenções acima
5. Validar GraphQL se aplicável

## Não faça

- Não crie HTTP clients custom pra APIs VTEX — use ctx.clients
- Não use fetch direto pra APIs internas — use JanusClient
- Não coloque secrets no código — use app settings
- Não faça deploy sem testar no workspace
- Não quebre schemas GraphQL existentes
- Não importe @prisma/client ou ORMs — VTEX tem Master Data
