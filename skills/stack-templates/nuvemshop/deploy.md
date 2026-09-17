---
name: nuvemshop-deploy
description: Processo de deploy em temas Nuvemshop — build local + FTP push, sem CI, sem server build.
---

# Deploy em temas Nuvemshop

## Regra fundamental

**A loja reflete o FTP, nao os arquivos locais.** Storefront e painel CMS renderizam o que esta no FTP. Editar/buildar local sem subir nao muda nada na loja.

## Comando de deploy

```bash
npm run builder:build && npm run theme:push
```

**Sempre build primeiro, push depois.** Sem isso, sobe CSS desatualizado.

## Scripts disponiveis

| Script | O que faz |
|---|---|
| `npm run builder:build` | Build unico — concatena SCSS modulares de `src/scss/` para `static/css/` |
| `npm run builder:watch` | Watch — rebuilda ao salvar arquivos em `src/scss/` |
| `npm run theme:push` | Envia todos os arquivos via FTP para a Nuvemshop |
| `npm run theme:pull` | Baixa arquivos do FTP para local |
| `npm run theme:watch` | Sobe arquivos automaticamente conforme voce edita |
| `npm run theme:login` | Configura credenciais FTP (grava em `.nube`) |

## Fluxo de desenvolvimento ativo

Duas opcoes:

**Opcao 1 — Manual (recomendado para mudancas pontuais):**
```bash
# Editar arquivos
npm run builder:build
npm run theme:push
```

**Opcao 2 — Watch (desenvolvimento continuo):**
```bash
# Em um terminal:
npm run builder:watch

# Em outro terminal:
npm run theme:watch --no-browser
```

Arquivos sobem automaticamente conforme voce salva.

## Caveats

- **Sem CI.** Nao ha pipeline antes do FTP push. Esquecer o build envia codigo desatualizado em producao.
- **Sem build no servidor.** A Nuvemshop processa `.tpl` e compila `.scss`, mas NAO roda npm/webpack/esbuild.
- **Push nao deleta arquivos remotos.** `theme:push` sobe um subconjunto por execucao e nunca deleta do FTP. Arquivo removido localmente continua no servidor.
- **Push nao reescreve estado do banco.** Ordem de secoes da home (`section_order`) persiste como item orfao mesmo apos remover do codigo.
- **Cache da plataforma.** Apos push, mudancas em snipplets cacheados podem demorar a aparecer. Testar em aba anonima.

## Troubleshooting

**Subi via FTP e o site continua igual:**
1. Verificar se rodou `builder:build` antes do push
2. Limpar cache do navegador / aba anonima
3. Cache da plataforma em snipplets — aguardar ou testar com `{% include %}` temporario

**CSS desatualizado no storefront:**
1. Builder nao rodou — `npm run builder:build`
2. Hash do CDN ainda e o antigo — aguardar propagacao

**Arquivo removido continua aparecendo:**
- `theme:push` nao deleta remoto. Remover manualmente via FTP client se necessario.

## Credenciais

Arquivo `.nube` na raiz contem credenciais FTP. Gerado pelo `theme:login`. Nao commitar credenciais sensiveis.
