---
name: nuvemshop-javascript
description: JavaScript em temas Nuvemshop — jQueryNuvem, LS.ready, store.js dual, preferir vanilla JS.
---

# JavaScript em temas Nuvemshop

## Problema do `store.js` dual

Alguns temas tem DOIS arquivos JS paralelos:

- `static/js/store.js.tpl` (v1)
- `static/js/store-v2.js.tpl` (v2)

O `layout.tpl` decide qual carregar em runtime:

```twig
{% if store.useStoreJsV2() %}
  {% include "static/js/store-v2.js.tpl" %}
{% else %}
  {% include "static/js/store.js.tpl" %}
{% endif %}
```

A plataforma define `store.useStoreJsV2()` por loja — voce nao controla. **Qualquer bloco novo em um precisa ser replicado identicamente no outro.** Adicionar em so um deixa a feature silenciosamente inativa na metade das lojas, sem erro no console.

Em temas que so tem `store.js.tpl` (sem v2), verificar se a loja usa v2 antes de assumir.

## `LS.ready.then()` — esperar jQuery

jQuery e carregado de forma assincrona. Codigo que usa `$` ou `jQueryNuvem` antes de estar disponivel quebra.

```twig
<script type="text/javascript">
  {# Libs sem dependencia de jQuery rodam imediatamente #}
  {% include "static/js/external-no-dependencies.js.tpl" %}

  LS.ready.then(function(){
    {# Codigo que depende de jQuery #}
    {% include "static/js/store.js.tpl" %}
  });
</script>
```

## `jQueryNuvem` — namespace protegido

**Nunca usar `$` global.** O lojista pode injetar JS via `store.assorted_js` que traz outra versao do jQuery. Usar `jQueryNuvem` — referencia protegida da plataforma.

```javascript
// Errado:
$('.js-foo').on('click', function() { ... });

// Certo:
jQueryNuvem('.js-foo').on('click', function() { ... });
```

## jQuery 1.11.1 (2014)

Essa e a versao padrao em temas classicos. Antiga, mas atualizar quebra codigo legado. Avaliar com cuidado.

## Preferir vanilla JS para codigo novo

`jQueryNuvem(document).on('click', selector, handler)` (delegate em document) pode falhar silenciosamente em algumas lojas — listener registrado mas nunca dispara. Causa provavel: bug jQuery 1.11.1 + JS injetado pelo lojista.

**Padrao: vanilla JS para codigo novo, especialmente delegacao de eventos.**

```javascript
// Em vez de delegate jQuery:
jQueryNuvem(document).on('click', '[data-foo]', function(e) { ... });

// Usar vanilla:
document.body.addEventListener('click', function(e) {
    var target = e.target.closest('[data-foo]');
    if (!target) return;
    e.preventDefault();
    var val = target.getAttribute('data-foo');
    // ...
}, false);
```

Helpers vanilla equivalentes:
- `e.target.closest(selector)` → substitui delegate do `.on()`
- `element.classList.add/remove/toggle` → substitui `$.addClass/removeClass`
- `element.setAttribute/getAttribute` → substitui `$.attr/data`
- `document.querySelector/querySelectorAll` → substitui `jQueryNuvem(selector)`
- `window.addEventListener('scroll', fn, { passive: true })` → scroll com performance

**Codigo legado continua em jQuery** — nao migre tudo. Foco: novo codigo que voce escrever.

## Carregamento no layout.tpl

```twig
{% set async_js = true %}
{% set nojquery = true %}

{% if load_jquery %}
  {{ '//ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js' | script_tag(true) }}
{% endif %}

{% head_content %}
```
