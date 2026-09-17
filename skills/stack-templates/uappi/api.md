---
name: uappi-api
description: API reference - three surfaces, key endpoints, session handling and conventions.
---

# API Uappi / wapstore

## Tres superficies

| Superficie | Base | Auth | Uso |
|---|---|---|---|
| **Storefront** | `/api/v2/front/*` | `App-Token` + `PHPSESSID` | Loja SSR consome |
| **Integracao/Admin** | `/api/v2/*` | `App-Token` + `Bearer` (JWT via `POST /v2/auth`) | Backoffice |
| **HUB Marketplaces** | `/api/v1/*` | `App-Token` + `Bearer` (via `POST /v1/auth`) | Integracao seller |

## Convencoes globais (storefront)

- **Header obrigatorio:** `App-Token: wapstore` (configurado no `nuxt.config.js` axios).
- **Sessao:** cookie `PHPSESSID`. O `plugins/axios.js` injeta `Session: <PHPSESSID>` e grava o cookie no response.
- **Formato:** JSON. Erros: `{ error: '<mensagem>' }`.
- **Debug:** `?debug` na rota exibe endpoint + status no erro.
- **Paginacao:** `offset`, `limit`, `order` (default `Popularidade`). Na rota do front: `pg`/`ipp` convertidos pelo `$requestDataListagem`.
- **Sempre usar caminho relativo** (`/v2/front/...`); a `baseUrl` resolve o host.

## Colecoes Postman oficiais

```bash
curl -s "https://www.<loja>.uappi.dev.br/api/v2/collection/front" -H "App-Token: wapstore"
curl -s "https://www.<loja>.uappi.dev.br/api/v2/collection/marketplace" -H "App-Token: wapstore"
curl -s "https://www.<loja>.uappi.dev.br/api/v2/collection/apiv2" -H "App-Token: wapstore"
```

## Endpoints principais

### Resolucao de paginas (`/v2/front/url/*`)

| Metodo | Endpoint | Params | Uso |
|---|---|---|---|
| GET | `/v2/front/url/verify` | `url` | Tipo da pagina (`nivel`) |
| GET | `/v2/front/url/home` | — | Dados da home |
| GET | `/v2/front/url/page` | `url` | Pagina institucional |
| GET | `/v2/front/url/product/detail` | `url` | Detalhe do produto |
| GET | `/v2/front/url/product/listing/category` | `url`, `offset`, `limit` | Listagem categoria |
| GET | `/v2/front/url/product/listing/landing-page` | `url`, `offset`, `limit` | Landing page (`/c/`) |
| GET | `/v2/front/url/product/listing/brand` | `url`, `offset`, `limit` | Listagem marca |
| GET | `/v2/front/url/product/listing/search` | `busca`, `offset`, `limit` | Busca (param e `busca`, nao `url`) |
| GET | `/v2/front/url/list/listing` | `url`, `offset`, `limit` | Listagem de listas |

### Configuracoes

| Metodo | Endpoint | Uso |
|---|---|---|
| GET | `/v2/front/settings` | Config da loja (carregada no boot) |

### Vitrines e banners (`/v2/front/showcase/*`)

| Metodo | Endpoint | Uso |
|---|---|---|
| GET | `/v2/front/showcase/banners/:slug` | Banners por area |
| GET | `/v2/front/showcase/products/:slug` | Vitrine de produtos |
| GET | `/v2/front/showcase/products/ultimos-vistos` | Ultimos vistos (`productId`, `seenProducts`, `limit`) |
| GET | `/v2/front/showcase/instagram` | Instashop |

### Estrutura (`/v2/front/struct/*`)

| Metodo | Endpoint | Uso |
|---|---|---|
| GET | `/v2/front/struct/menus/:slug` | Menus (header-menu, header-categories, pitchbar, bullets, etc) |
| GET | `/v2/front/struct/popup/:nivel` | Popups (home, detail, page) |

### Checkout e carrinho (`/v2/front/checkout/*`)

| Metodo | Endpoint | Uso |
|---|---|---|
| GET | `/v2/front/checkout/cart` | Buscar carrinho |
| POST | `/v2/front/checkout/cart` | Adicionar item |
| PUT | `/v2/front/checkout/cart` | Atualizar quantidade |
| DELETE | `/v2/front/checkout/cart` | Remover item |
| POST | `/v2/front/checkout/shop` | Comprar agora / kit |
| GET | `/v2/front/checkout/user` | Usuario logado |
| POST | `/v2/front/checkout/login` | Login |
| POST | `/v2/front/checkout/logout` | Logout |
| POST | `/v2/front/checkout/zipcode` | Define CEP da sessao |

### Frete, favoritos, produto

| Metodo | Endpoint | Uso |
|---|---|---|
| POST | `/v2/front/shipment/product` | Frete do produto |
| GET | `/v2/front/wishlist` | Lista favoritos |
| POST | `/v2/front/wishlist/add` | Adicionar favorito |
| POST | `/v2/front/wishlist/remove` | Remover favorito |
| POST | `/v2/front/product/combination` | Resolve SKU por atributos |
| POST | `/v2/front/product/solicitation` | Avise-me (volta ao estoque) |
| POST | `/v2/front/newsletter` | Newsletter |

### Marketplace (`/v2/front/marketplace/*`)

| Metodo | Endpoint | Uso |
|---|---|---|
| GET | `/v2/front/marketplace/product/:idProduto` | Ofertas por seller (buy box) — `sellerId`, `cep`, `offset`, `limit` |

> Slugs de showcase/struct sao **por loja** — configurados no painel. Confirme existencia antes de usar.
