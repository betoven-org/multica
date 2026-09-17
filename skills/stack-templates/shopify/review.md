---
name: review
description: Checklist de code review para Shopify — schema, imagens, traducoes, secrets e snippets.
---

# Code Review Checklist — Shopify

Checklist sistematico para revisar PRs de temas Shopify (Liquid e Hydrogen).

## Quando usar

- Em todo PR de tema Shopify antes de merge.
- Como self-review antes de abrir o PR.
- Como validacao final antes de publicar o tema.

## Checklist — Liquid Themes

### Schema e Sections

- [ ] **Schema JSON valido** — `{% schema %}` parseia sem erros. Rodar `shopify theme check`.
- [ ] **Presets declarados** — Sections adicionaveis tem `presets` no schema.
- [ ] **Settings com labels descritivos** — Cada setting tem `label` claro usando `t:` prefix.
- [ ] **Defaults razoaveis** — Settings tem valores default que funcionam sem configuracao.
- [ ] **Tipos de setting corretos** — Usar `collection` para colecao, `product` para produto, etc.
- [ ] **disabled_on configurado** — Sections que nao devem aparecer em header/footer tem `disabled_on`.

### Imagens

- [ ] **image_url (nao img_url)** — Usar filtro `image_url` moderno.
- [ ] **width e height declarados** — Toda `<img>` tem dimensoes explicitas.
- [ ] **srcset com multiplos tamanhos** — Imagens responsivas com srcset.
- [ ] **sizes correto** — Atributo `sizes` reflete o layout real.
- [ ] **loading="lazy" abaixo do fold** — Imagens nao visíveis inicialmente.
- [ ] **loading="eager" para LCP** — Imagem principal sem lazy load.
- [ ] **alt text presente** — Toda imagem tem `alt` (usar `| escape`).

### Traducoes (i18n)

- [ ] **Sem strings hardcoded** — Textos visiveis usam `| t` ou `t:` no schema.
- [ ] **Arquivos em locales/** — Todas traducoes nos arquivos de locale.
- [ ] **Minimo pt-BR e en** — Suporte a pelo menos 2 idiomas.
- [ ] **Chaves organizadas** — Seguir hierarquia `sections.nome_section.settings.*`.

### Liquid Best Practices

- [ ] **render em vez de include** — `{% include %}` esta deprecated.
- [ ] **Sem logica complexa** — Extrair logica em snippets separados.
- [ ] **Variaveis com assign** — Usar `assign` fora de loops quando possivel.
- [ ] **Loops com limit** — Loops em colecoes tem `limit:` explicito.
- [ ] **Nil checks** — Verificar `blank` antes de usar variaveis que podem ser nil.
- [ ] **escape em outputs** — `{{ text | escape }}` para prevenir XSS.

### Seguranca

- [ ] **Sem secrets hardcoded** — API keys, tokens nao estao no codigo do tema.
- [ ] **Sem tokens no JS** — Storefront Access Token pode ser publico, mas Admin API tokens NUNCA.
- [ ] **Output escapado** — Inputs do usuario passam por `| escape` ou `| sanitize`.

### Snippets

- [ ] **Reutilizaveis** — Snippets aceitem parametros via `render`.
- [ ] **Documentados** — Comment no topo com parametros aceitos.
- [ ] **Sem side effects** — Snippets nao devem depender de variaveis globais implicitas.

### Performance

- [ ] **shopify theme check --category performance** — Zero erros de performance.
- [ ] **Scripts com defer** — JS nao-critico carrega com `defer`.
- [ ] **Fontes com preload** — Fontes customizadas tem `<link rel="preload">`.
- [ ] **CSS critico inline** — Above-the-fold CSS no `<head>`.

## Checklist — Hydrogen

### Server Components

- [ ] **Server por padrao** — Componentes sem `'use client'` sao server.
- [ ] **Client apenas quando necessario** — `'use client'` so para interatividade (state, effects, events).
- [ ] **Dados no loader** — Fetch via loader, nunca useEffect no client.

### GraphQL

- [ ] **Queries tipadas** — Usar codegen: `storefrontapi.generated.ts`.
- [ ] **`as const` nas queries** — Necessario para codegen.
- [ ] **Sem overfetching** — Buscar apenas campos necessarios.
- [ ] **Fragments reutilizados** — Campos comuns em fragments.
- [ ] **Paginacao com cursor** — Usar `first/after` ou `last/before`.
- [ ] **userErrors verificados** — Mutations checam `userErrors` na resposta.

### Performance Hydrogen

- [ ] **defer para dados secundarios** — Dados nao-criticos usam `defer` + `Await`.
- [ ] **Image component** — Usar `<Image>` do Hydrogen, nao `<img>` direto.
- [ ] **Money component** — Usar `<Money>` para precos formatados.
- [ ] **Cache headers** — Configurar cache em loaders quando apropriado.

### Erros

- [ ] **404 tratado** — Recursos nao encontrados retornam `Response` com status 404.
- [ ] **Error boundaries** — Paginas tem `ErrorBoundary` export.
- [ ] **Sem console.log** — Remover antes de merge.

## Processo de review

1. Rodar `shopify theme check` (Liquid) ou `shopify hydrogen typecheck` (Hydrogen).
2. Verificar cada item do checklist acima.
3. Preview visual em desktop e mobile.
4. Verificar Lighthouse score (minimo 90 em Performance).
5. Testar funcionalidade completa (happy path + edge cases).

## Common mistakes em review

1. **Aprovar sem preview visual** — Sempre ver o resultado renderizado.
2. **Ignorar warnings do theme check** — Warnings viram problemas em producao.
3. **Nao testar mobile** — Layout Liquid frequentemente quebra em telas pequenas.
4. **Esquecer acessibilidade** — Verificar contrast ratio, aria labels, keyboard navigation.
5. **Nao verificar com dados reais** — Testar com produtos/colecoes reais, nao apenas placeholders.
