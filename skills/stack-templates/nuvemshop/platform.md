---
name: nuvemshop-platform
description: Regras fundamentais da plataforma Nuvemshop — linhagem de tema, areas nao-controlaveis, deploy via FTP.
---

# Plataforma Nuvemshop

## Duas linhagens de tema

A Nuvemshop tem duas linhagens com APIs Twig diferentes. Identificar qual voce esta usando e a primeira coisa antes de qualquer decisao.

**Tema classico:**
- Estrutura com `snipplets/`, `templates/`, `layout.tpl` unico em `layouts/`
- APIs Twig mais limitadas
- Features avancadas via `{{ component(...) }}` (HTML nao-controlavel)
- `product.subscription_plans` NAO existe — usar `{{ component('subscriptions/subscription-selector') }}`

**Morelia 2.x+:**
- Pasta `sections/` na raiz (nao existe em classico)
- APIs Twig estendidas (`product.subscription_plans` exposto direto)
- Mais flexibilidade no markup

**Como identificar:** tem pasta `sections/`? Morelia 2.x+. Tem `snipplets/` e `layout.tpl` unico? Classico.

## Areas onde o HTML e da plataforma

Voce NAO controla o markup nestas areas — so estiliza via CSS:

- **Checkout puro** — layout proprio da Nuvemshop. Unico CSS que chega: `checkout.scss.tpl` (se `store.allows_checkout_styling == true`)
- **`/comprar`** — usa `layout.tpl` do tema mas HTML parcial da plataforma com classes Bootstrap
- **Login/register** — `{{ component('forms/account/login') }}` / `register`. HTML com classes Bootstrap fixas. Customizacao limitada a 3 params: `validation_classes`, `spacing_classes`, `form_classes`

Consequencia: **Bootstrap nao pode ser removido**. Essas areas dependem dele.

## Componentes nativos

`{{ component('nome', { params }) }}` renderiza HTML controlado pela Nuvemshop com classes Bootstrap fixas. Voce passa parametros quando expostos, mas nao controla o markup interno.

## Ambiente e deploy

- **Sem build no servidor.** Nuvemshop processa `.tpl` (Twig) e compila `.scss`, mas NAO roda npm/webpack/esbuild.
- **Build local obrigatorio.** Se o projeto tem builder proprio, rodar antes do push. Output commitado e enviado via FTP.
- **Deploy via FTP.** `.nube` na raiz contem credenciais. CLI Nuvemshop expoe `theme:push`, `theme:pull`, `theme:watch`.
- **A loja reflete o FTP, nao os arquivos locais.** Editar local sem subir nao muda nada na loja.
- **Sem CI.** Esquecer o build antes do push envia codigo desatualizado em producao.

## Restricoes

- Sem rotas customizadas — paginas institucionais sempre em `/pages/<handle>`
- Sem hooks de build no servidor
- Sem acesso ao banco — dados via Twig vars (`product.*`, `customer.*`, `cart.*`)
- Sem APIs de assinatura customizadas em tema classico
- Cache de `{% snipplet %}` — mudancas podem demorar a aparecer

## Estrutura de pastas fixa (tema classico)

```
layouts/layout.tpl        # unico layout principal
templates/                 # uma pagina por tipo (home, product, category, cart, page, etc.)
  account/                 # login, register, info, orders, etc.
snipplets/                 # componentes reutilizaveis (atencao: 2 L, snippLets)
static/css/, static/js/, static/images/
config/settings.txt, config/defaults.txt
.nube                      # credenciais FTP
```
