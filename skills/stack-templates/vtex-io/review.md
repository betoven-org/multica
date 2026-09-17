---
name: review
description: Checklist de code review para apps VTEX IO — CSS Handles, TypeScript, i18n, policies e boas praticas.
---

# Code Review Checklist — VTEX IO

Checklist sistematico para revisar PRs de apps VTEX IO. Cada item deve ser verificado antes de aprovar.

## Quando usar

- Em todo PR de app VTEX IO antes de merge.
- Como self-review antes de abrir o PR.
- Como validacao final antes de deploy.

## Checklist

### CSS e Estilizacao

- [ ] **CSS Handles em todos elementos visiveis** — Nenhum elemento renderizado sem handle.
- [ ] **Sem inline styles** — Zero `style={{}}` no JSX. Usar handles + classes Tachyons ou CSS override.
- [ ] **Nomenclatura camelCase** — Handles seguem `componentNameElement` (ex: `productCardTitle`).
- [ ] **Handles com `as const`** — Array de handles declarado com `as const` para tipagem.
- [ ] **Sem CSS Modules** — VTEX IO usa CSS Handles, nao CSS Modules.
- [ ] **Sem classes CSS hardcoded** — Exceto classes Tachyons oficiais do VTEX Styleguide.

### TypeScript

- [ ] **Strict mode** — Sem `any` explicito. Tipar tudo.
- [ ] **Interfaces para props** — Todo componente tem interface de props tipada.
- [ ] **Generics em http calls** — `this.http.get<MyType>(...)` sempre tipado.
- [ ] **Sem `@ts-ignore`** — Resolver o erro de tipo, nao ignorar.
- [ ] **Sem `as any`** — Type assertions devem ser para tipos especificos.

### Console e Debug

- [ ] **Sem `console.log`** — Remover todos antes de merge. Usar `ctx.vtex.logger` no backend.
- [ ] **Sem `debugger`** — Remover statements de debug.
- [ ] **Sem codigo comentado** — Remover codigo morto. Git guarda historico.

### Internacionalizacao (i18n)

- [ ] **Todas strings visiveis com i18n** — Usar `intl.formatMessage()` ou `<FormattedMessage>`.
- [ ] **Messages em pt, en, es** — Minimo 3 idiomas nos arquivos `messages/`.
- [ ] **Prefixo correto** — `store/` para loja, `admin/` para Site Editor.
- [ ] **defineMessages** — Mensagens declaradas com `defineMessages` para extracao automatica.

### manifest.json

- [ ] **Policies declaradas** — Todo host externo tem `outbound-access`.
- [ ] **Versao semver correta** — Bump de versao condiz com a mudanca (patch/minor/major).
- [ ] **Builders corretos** — Todos os builders necessarios estao listados.
- [ ] **Dependencies atualizadas** — Sem dependencias em versoes deprecated.

### GraphQL (se aplicavel)

- [ ] **@cacheControl em todas queries** — Nenhuma query sem diretiva de cache.
- [ ] **scope PRIVATE para dados de usuario** — Dados pessoais nunca em cache PUBLIC.
- [ ] **@auth em mutations** — Mutations que modificam dados protegidas com @auth.
- [ ] **Campos retornados correspondem ao schema** — Nomes e tipos exatos.

### Performance

- [ ] **Imagens com width e height** — Todas `<img>` tem dimensoes explicitas.
- [ ] **Lazy load em imagens abaixo do fold** — `loading="lazy"` em imagens nao criticas.
- [ ] **Sem import de biblioteca inteira** — Importar submodulos: `lodash/get`, nao `lodash`.
- [ ] **LRUCache configurado** — Backend usa memory cache.
- [ ] **Sem overfetching GraphQL** — Queries buscam apenas campos necessarios.

### Seguranca

- [ ] **Sem secrets hardcoded** — API keys, tokens em app settings, nao no codigo.
- [ ] **Input validado** — Argumentos de resolver validados antes de usar.
- [ ] **Sem SQL injection em Master Data** — Sanitizar filtros de busca.

### Estrutura

- [ ] **Separacao de responsabilidades** — Componentes pequenos, resolvers focados.
- [ ] **Sem logica de negocios em componentes React** — Logica no backend/resolvers.
- [ ] **interfaces.json atualizado** — Novos blocos registrados corretamente.
- [ ] **Schema do Site Editor** — `MyComponent.schema` presente para componentes configuraveis.

## Common mistakes em review

1. **Aprovar sem testar no workspace** — Sempre linkar e testar visualmente.
2. **Ignorar warnings TypeScript** — Warnings viram bugs em producao.
3. **Nao verificar mobile** — Testar responsividade, especialmente CLS em telas pequenas.
4. **Esquecer de verificar o build** — `vtex link` deve completar sem erros.
5. **Nao verificar impacto em performance** — Comparar Lighthouse antes e depois.
