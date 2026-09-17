# Tray — Convenções do Projeto

## Stack

- Renderização: HTML5 + CSS3 + JavaScript
- Pré-processador: SASS (compilação com Gulp)
- Tooling: tray-cli, Gulp
- TypeScript: obrigatório pra SDK/integrações

## Plugin IA disponível

### tray-api-ai-plugin
Plugin oficial com 150+ endpoints e 35 skills pra agentes IA.

```bash
npm install --save-dev github:tray-tecnologia/tray-api-ai-plugin
```

**Skills disponíveis (35):**
- Catálogo: produtos, variações, categorias, marcas, imagens, características
- Vendas: pedidos, status, faturas, cupons, carrinhos, B2B
- Clientes: profiles, endereços, histórico, pagamentos
- Operacional: armazéns, etiquetas, scripts externos
- Marketing: newsletters, parceiros, SEO, analytics
- Configuração: autenticação, webhooks, info da loja

**Validação local:**
```bash
node skills/<skill>/scripts/validate.mjs
```

## Estrutura de tema Tray

```
projeto/
├── .sass/           → Componentes SASS organizados
├── theme/           → HTML dos templates
├── extras/          → Assets adicionais (Figma, mockups)
├── gulpfile.js      → Build tasks (watch, minify, version)
├── .husky/          → Git hooks (commits semânticos)
└── package.json
```

## API REST Tray

### Autenticação
- OAuth2 com id_cliente + secret
- Tokens com expiração
- Sandbox: dev.tray.com.br

### Endpoints (150+)
| Área | Exemplos |
|------|----------|
| Catálogo | GET /products, POST /products, PUT /products/:id |
| Pedidos | GET /orders, PUT /orders/:id/status |
| Clientes | GET /customers, POST /customers |
| Webhooks | POST /webhooks (eventos de loja) |

### Variáveis de ambiente
```
TRAY_CLIENT_ID=<oauth_client_id>
TRAY_CLIENT_SECRET=<oauth_client_secret>
TRAY_API_URL=https://api.tray.com.br/v1
```

## Regras obrigatórias

### Temas
- SASS componentizado (evitar monolitos)
- HTML semântico
- JavaScript vanilla (sem framework obrigatório)
- Lazy load em imagens
- Minificação via Gulp antes de deploy
- Limpar cache pós-deploy

### Integrações/Backend
- TypeScript obrigatório
- Validação com Zod
- Async/await (Promises)
- ESLint + Prettier (git hooks via Husky)
- Commits semânticos
- Sem console.log em produção

### Deploy
- Usar tray-cli (não opencode-sdk que é deprecated)
- Compilar SASS com Gulp antes
- Minificar e versionar assets
- Testar em sandbox antes de produção

## Checklist antes de PR

- [ ] SASS compilando sem erros
- [ ] HTML semântico
- [ ] Imagens com lazy load
- [ ] Assets minificados (gulp build)
- [ ] Sem console.log
- [ ] TypeScript strict em integrações
- [ ] Validação de inputs com Zod
- [ ] Testado no sandbox

## Integrações comuns

- Sincronizar catálogo (produtos/variações)
- Automação de pedidos (status, faturas)
- Gestão de clientes e endereços
- B2B pricing lists
- Migração de plataformas (Shopify, WooCommerce, VTEX, Magento, Nuvemshop)

## Não faça

- Não use opencode-sdk (deprecated) — use tray-cli
- Não faça deploy sem compilar SASS
- Não esqueça de limpar cache após deploy
- Não hardcode tokens OAuth
- Não ignore o sandbox pra testes
