---
name: nuvemshop-css
description: Arquitetura CSS em temas Nuvemshop — SCSS modular, 3 camadas, especificidade contra Bootstrap, Custom Properties.
---

# CSS em temas Nuvemshop

## Arquitetura de 3 camadas

**1. Critical CSS** — inline no `<head>` via `| static_inline`. Layout fundamental, grid, tipografia basica. Manter enxuto.

**2. Async CSS** — `<link media="print" onload="this.media='all'">`. Maioria dos estilos. Nao bloqueia render.

**3. Settings-driven CSS** — Twig com interpolacao de `settings.*`, inline. Carrega por ultimo, vence no cascade para mesma especificidade. Customizacoes do lojista tem precedencia.

## Builder local (projeto Ori)

O projeto usa builder local que concatena `.scss` modulares em `src/scss/` para gerar outputs em `static/css/`:

- `src/scss/critical/` → `static/css/style-critical.scss`
- `src/scss/style/` → `static/css/style-async.scss`
- `src/scss/_colors.scss` → `static/css/style-colors.scss`
- Ordem definida em `src/scss/manifest.json`

**SEMPRE editar em `src/scss/`, NUNCA nos outputs.**

Build: `npm run builder:build` (uma vez) ou `npm run builder:watch` (watch).

## Especificidade contra Bootstrap

HTML da plataforma (login, register, checkout, `/comprar`) usa classes Bootstrap fixas com especificidade 0,1,0. BEM puro empata — fragil.

**Padrao: BEM com contexto (0,2,0) para vencer Bootstrap:**

```scss
// Empata (fragil):
.footer { &__input { border-radius: 0; } }  // .footer__input (0,1,0)

// Vence:
.footer { .footer__input { border-radius: 0; } }  // .footer .footer__input (0,2,0)
```

Aplicar contexto sempre que o elemento esta dentro de pai nomeado e precisa vencer regras globais de input/button/select.

## Regras fundamentais

- **Nunca usar `!important`** para compensar base ruim. Unico uso aceito: override de JS/lib externa.
- **Bootstrap nao pode ser removido** — areas nao-controlaveis dependem dele.
- **CSS condicional por setting** → classe no `<body>`, nao `{% if %}` no SCSS. Mantem SCSS puro e cacheavel.
- **Settings dinamicos do painel** → CSS Custom Properties (`var(--token)`), nao `$vars` SCSS.

## `.scss` vs `.scss.tpl`

Comportamento incerto entre temas. Convencao pragmatica: **usar CSS Custom Properties em vez de `$vars` SCSS** para qualquer coisa settings-driven. `$vars` SCSS so em arquivos `.scss` puros (sem `.tpl`).

## CSS condicional por setting — receita

```twig
{# No layout.tpl: #}
<body class="grid-desktop-{{ settings.grid_columns_desktop }}">
```

```scss
// No SCSS (puro, sem Twig):
.grid-desktop-3 .grid__item { @media (min-width: 992px) { width: 33.333%; } }
.grid-desktop-4 .grid__item { @media (min-width: 992px) { width: 25%; } }
```
