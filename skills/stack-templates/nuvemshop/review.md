---
name: nuvemshop-review
description: Checklist de revisao para temas Nuvemshop — build, deploy, acessibilidade, responsividade, Bootstrap.
---

# Review checklist para temas Nuvemshop

## Pre-deploy

- [ ] **Builder rodou** — `npm run builder:build` executado. CSS em `static/css/` esta atualizado com as mudancas de `src/scss/`
- [ ] **FTP atualizado** — `npm run theme:push` executado. A loja reflete o FTP, nao os arquivos locais
- [ ] **Sem editar outputs** — mudancas feitas em `src/scss/`, NUNCA diretamente em `static/css/`

## Textos e traducoes

- [ ] **Sem texto hardcoded** — todo texto visivel vem de settings ou traducoes (`{{ 'chave' | translate }}`)
- [ ] **Traducoes existem** — chaves usadas no TPL existem no arquivo de traducoes
- [ ] **Setting nova no defaults** — toda setting nova tem valor padrao em `config/defaults.txt` (exceto `image`)

## Imagens

- [ ] **`alt` em toda `<img>`** — descritivo ou `alt=""` explicito se decorativa (WCAG 1.1.1)
- [ ] **`width` e `height` em toda `<img>`** — evita CLS (layout shift)
- [ ] **Variants corretos** — `1080p` para full-bleed (NAO `original`), `huge`/`large` para slots menores
- [ ] **srcset com descritores corretos** — descritor `w` corresponde a largura real do variant
- [ ] **`fetchpriority="high"` so no LCP** — primeira imagem above-the-fold. Demais com `loading="lazy"` + `decoding="async"`
- [ ] **Placeholder correto** — `placehold.co/{W}x{H}` sem cores/texto customizado, so no preview
- [ ] **Hint no settings.txt** — dimensoes na medida CSS (1x), `description` com tamanho recomendado

## Responsividade

- [ ] **Testado em mobile** — viewport < 576px (cutoff sm do Bootstrap)
- [ ] **Testado em tablet** — viewport 768px-1024px
- [ ] **Testado em desktop** — viewport >= 1250px (container max)
- [ ] **Aspect-ratio desktop vs mobile** — se diferente, usar `<picture>` com `<source media>`, NAO `object-fit: cover`
- [ ] **Sem scroll horizontal** — sliders com `overflow: visible` tem wrapper com `overflow-x: hidden`

## CSS

- [ ] **Sem `!important`** — exceto override de JS/lib externa
- [ ] **Especificidade correta** — `.contexto .elemento` (0,2,0) quando precisa vencer Bootstrap
- [ ] **Bootstrap preservado** — nao remover, nao sobrescrever classes globais do Bootstrap usadas pela plataforma
- [ ] **CSS condicional via classe no body** — nao `{% if %}` dentro do SCSS
- [ ] **Custom Properties para settings dinamicos** — nao `$vars` SCSS em `.scss.tpl`

## JavaScript

- [ ] **Dentro de `LS.ready.then()`** — se depende de jQuery
- [ ] **`jQueryNuvem`** — nunca `$` global
- [ ] **Replicado em ambos store.js** — se existem `store.js.tpl` e `store-v2.js.tpl`, codigo nos dois
- [ ] **Vanilla JS para codigo novo** — especialmente delegacao de eventos

## Twig

- [ ] **Sem `{% %}` dentro de `{# #}`** — comentarios com tags Twig vazam no front
- [ ] **`or params.preview`** — secoes condicionais visiveis no editor do admin
- [ ] **Scope de `{% set %}`** — nao usar `set` dentro de `for` esperando persistir fora
- [ ] **`page.handle`** — nao `page.slug` ou `page.url`

## Plataforma

- [ ] **Sem rotas customizadas** — paginas institucionais em `/pages/<handle>`
- [ ] **Componentes nativos respeitados** — `{{ component() }}` nao tem markup customizavel, so CSS
- [ ] **Cache de snipplets considerado** — mudancas podem demorar. Testar com `{% include %}` se necessario
