---
name: nuvemshop-fix-bug
description: Debugging em temas Nuvemshop — gotchas comuns, ciclo de deploy FTP, problemas de cache e especificidade.
---

# Debugging em temas Nuvemshop

## Primeiro passo: verificar gotchas conhecidos

Antes de investigar, checar se o sintoma ja e conhecido. Gotchas mais comuns por dominio:

### Config / Settings
- **Setting nova nao aparece no admin** — verificar se `settings.txt` esta correto e foi feito push
- **Loja inteira em 500** — pode ser remocao de settings de CMS que deixou lock vazio
- **Secao removida continua no painel** — `section_order` persiste no banco, push nao apaga
- **Default aparece literal** (`\n\n`) — quebra de linha no `defaults.txt` nao e interpretada

### CSS
- **CSS nao aparece** — hash do CDN ainda e o antigo, aguardar propagacao ou limpar cache
- **`$var` SCSS apareceu literal** — arquivo `.scss.tpl` pode nao compilar SCSS. Usar Custom Properties
- **`!important` para vencer Bootstrap** — errado. Usar especificidade `.contexto .elemento` (0,2,0)
- **Scroll horizontal** — slider com `overflow: visible` precisa de `overflow-x: hidden` no wrapper pai

### JavaScript
- **`$ is not defined`** — codigo fora de `LS.ready.then()`. jQuery carrega async
- **Feature funciona numa loja e nao em outra** — verificar se existe `store-v2.js.tpl`. Codigo so em um dos dois
- **Listener delegado nao dispara** — bug jQuery 1.11.1. Usar vanilla JS com `e.target.closest()`
- **Tracking do lojista quebra tema** — `store.assorted_js` injeta JS arbitrario que conflita

### Twig
- **Comentario aparecendo no front** — `{# #}` com `{% %}` dentro vaza. Descrever em prosa
- **Mudou snipplet e nao ve no front** — cache de `{% snipplet %}`. Testar com `{% include %}` temporario
- **`{% set %}` dentro de `{% for %}` nao persiste** — scope do loop. Usar captured block

### Imagens
- **Imagem borrada** — variant `original` e so 1024px. Para full-bleed usar `1080p`
- **`fetchpriority` em varias imagens piorou LCP** — so usar no LCP real
- **Screen reader le URL do arquivo** — falta `alt`

### Plataforma
- **Subi via FTP e site continua igual** — cache da plataforma, ou esqueceu `builder:build` antes do push
- **HTML de login/register nao muda** — e `{{ component() }}`, HTML da plataforma. So estilizar
- **Checkout visual diferente** — layout separado, so `checkout.scss.tpl` chega la

## Ciclo de debug

1. Reproduzir o sintoma no storefront (nao no localhost — nao existe localhost em Nuvemshop)
2. Verificar se o build esta atualizado: `npm run builder:build`
3. Verificar se o FTP esta atualizado: `npm run theme:push`
4. Limpar cache do navegador e testar em aba anonima
5. Se o problema persiste, verificar se e cache da plataforma (snipplets cacheados)
6. Inspecionar DevTools: CSS aplicado, JS carregado, erros no console
7. Verificar `store.useStoreJsV2()` se o problema e JS

## Problemas de especificidade CSS

Hierarquia para referencia rapida:

| Nivel | Seletor | Especif. | Quando |
|---|---|---|---|
| Reset global | `input[type=text]` | 0,1,0 | Apenas em reset |
| BEM puro | `.bloco__elemento` | 0,1,0 | Sem conflito com framework |
| BEM em contexto | `.pai .bloco__elemento` | 0,2,0 | Padrao para vencer Bootstrap |
| Estado | `.pai .bloco__elemento--mod` | 0,2,0+ | Estados visuais |
| `!important` | — | — | Proibido, exceto override de JS/lib externa |
