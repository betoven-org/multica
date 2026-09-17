---
name: uappi-deploy
description: Deploy Uappi storefronts - build, Docker setup, environment variables and production config.
---

# Deploy Uappi

## Build de producao

```bash
npm run build      # nuxt build
npm run start      # sobe o servidor
```

## Variaveis de ambiente (`src/.env`)

```env
SITE_URL=https://www.<loja>.uappi.dev.br/
SUB_DOMAIN_URL=https://www.<loja>.uappi.dev.br/
WAP_API_URL=https://www.<loja>.uappi.dev.br/api/
```

Carregadas via `@nuxtjs/dotenv`. Acesso: `process.env.SITE_URL`.

> A `baseUrl` do axios e o endpoint de settings no `nuxt.config.js` tambem estao hardcoded. Ao trocar de loja, ajustar os dois lugares.

## Dockerfile

```dockerfile
FROM node:16

ENV NODE_TLS_REJECT_UNAUTHORIZED=0
ENV HOST=0
ENV PORT=80

# Registry privado @wapstore
ARG npm_token_deploy
RUN echo "//registry.npmjs.org/:_authToken=${npm_token_deploy}" > .npmrc \
    && echo "@wapstore:registry=https://registry.npmjs.org/" >> .npmrc \
    && echo "always-auth=true" >> .npmrc

COPY . .
RUN npm ci
RUN rm -f .npmrc

RUN node --max-old-space-size=1536 node_modules/.bin/nuxt build --standalone

ENTRYPOINT ["npm", "start"]
```

Pontos criticos:
- `node:16` — versao fixa.
- `npm_token_deploy` como build-arg — segredo, nunca expor.
- `.npmrc` removido apos `npm ci`.
- `--max-old-space-size=1536` para o build.
- `--standalone` para bundle autocontido.

## docker-compose.yml

```yaml
version: '3'
services:
  webserver:
    build:
      context: .
      args:
        npm_token_deploy: <TOKEN_AQUI>
    container_name: <loja>-deploy
    ports:
      - "81:80"
    restart: always
    mem_limit: 1g
    environment:
      - TZ=America/Sao_Paulo
    extra_hosts:
      - "www.<loja>.uappi.dev.br:<IP_SERVIDOR>"
```

Ao trocar de loja, atualizar:
- `container_name`
- `extra_hosts` (dominio + IP)
- `npm_token_deploy`
- Porta exposta (`81:80` ou conforme infra)

## Checklist de deploy

- [ ] `src/.env` com URLs corretas da loja.
- [ ] `nuxt.config.js` baseUrl alinhada com as envs.
- [ ] `docker-compose.yml` com `container_name`, `extra_hosts` e token corretos.
- [ ] `.npmrc` com token valido para `@wapstore` (so no build, removido depois).
- [ ] `npm run build` sem erros.
- [ ] Testar SSR: `curl -s http://localhost:81 | head` retorna HTML renderizado.
- [ ] Verificar `PHPSESSID` funcionando (carrinho persiste entre paginas).
- [ ] Verificar settings carregadas (`window.config` no HTML).

## Segredos

| Segredo | Local | Cuidado |
|---|---|---|
| npm token | `.npmrc` / `docker-compose.yml` arg | Nunca commitar; removido no build |
| API URL | `src/.env` | Gitignore esta comentado por padrao — cuidado |
| `extra_hosts` IP | `docker-compose.yml` | IP do servidor de producao |
