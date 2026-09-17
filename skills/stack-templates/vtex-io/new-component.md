---
name: new-component
description: Como criar um novo componente storefront em VTEX IO com tipagem, CSS Handles e i18n.
---

# Criar novo componente storefront em VTEX IO

Guia completo para criar um componente React no VTEX IO Store Framework, desde a estrutura de arquivos ate o registro no store.

## Quando usar

- Quando nenhum componente nativo ou de app existente resolve o requisito.
- Para blocos customizados que serao usados no store-theme.

## Steps

### 1. Estrutura de arquivos

```
my-app/
  manifest.json
  store/
    interfaces.json
  react/
    MyComponent.tsx
    typings/
      vtex.render-runtime.d.ts
  messages/
    pt.json
    en.json
    es.json
  styles/
    css/
      vtex.my-app.css
```

### 2. Declarar a interface em `store/interfaces.json`

```json
{
  "my-component": {
    "component": "MyComponent",
    "composition": "children",
    "allowed": ["image", "rich-text"],
    "content": {
      "properties": {
        "title": {
          "type": "string",
          "title": "admin/editor.my-component.title",
          "description": "admin/editor.my-component.title.description"
        },
        "showBorder": {
          "type": "boolean",
          "title": "admin/editor.my-component.showBorder",
          "default": false
        }
      }
    }
  }
}
```

### 3. Criar o componente React

```typescript
// react/MyComponent.tsx
import React from 'react'
import { useCssHandles } from 'vtex.css-handles'
import { useIntl, defineMessages } from 'react-intl'

const CSS_HANDLES = [
  'myComponentContainer',
  'myComponentTitle',
  'myComponentContent',
] as const

const messages = defineMessages({
  defaultTitle: {
    id: 'store/my-component.default-title',
    defaultMessage: 'Default Title',
  },
})

interface MyComponentProps {
  title?: string
  showBorder?: boolean
  children?: React.ReactNode
}

const MyComponent: React.FC<MyComponentProps> = ({
  title,
  showBorder = false,
  children,
}) => {
  const handles = useCssHandles(CSS_HANDLES)
  const intl = useIntl()

  const displayTitle = title || intl.formatMessage(messages.defaultTitle)

  return (
    <div className={`${handles.myComponentContainer} ${showBorder ? 'ba b--muted-3' : ''}`}>
      <h2 className={handles.myComponentTitle}>{displayTitle}</h2>
      <div className={handles.myComponentContent}>
        {children}
      </div>
    </div>
  )
}

MyComponent.schema = {
  title: 'admin/editor.my-component',
  type: 'object',
  properties: {
    title: {
      title: 'admin/editor.my-component.title',
      type: 'string',
    },
    showBorder: {
      title: 'admin/editor.my-component.showBorder',
      type: 'boolean',
      default: false,
    },
  },
}

export default MyComponent
```

### 4. Mensagens de i18n

```json
// messages/pt.json
{
  "store/my-component.default-title": "Titulo Padrao",
  "admin/editor.my-component": "Meu Componente",
  "admin/editor.my-component.title": "Titulo",
  "admin/editor.my-component.title.description": "Texto exibido como titulo",
  "admin/editor.my-component.showBorder": "Exibir borda"
}
```

```json
// messages/en.json
{
  "store/my-component.default-title": "Default Title",
  "admin/editor.my-component": "My Component",
  "admin/editor.my-component.title": "Title",
  "admin/editor.my-component.title.description": "Text displayed as title",
  "admin/editor.my-component.showBorder": "Show border"
}
```

### 5. Registrar no manifest.json

Garanta que o `manifest.json` tem as dependencias necessarias:

```json
{
  "dependencies": {
    "vtex.css-handles": "0.x",
    "vtex.render-runtime": "8.x"
  },
  "builders": {
    "react": "3.x",
    "store": "0.x",
    "messages": "1.x",
    "styles": "2.x"
  }
}
```

### 6. Usar no store-theme

```json
// store-theme/store/blocks/home.jsonc
{
  "store.home": {
    "blocks": ["my-component#home"]
  },
  "my-component#home": {
    "props": {
      "title": "Bem-vindo",
      "showBorder": true
    },
    "children": ["rich-text#welcome"]
  }
}
```

## Common mistakes

1. **Esquecer `interfaces.json`** — Sem interface, o bloco nao e reconhecido pelo Store Framework.
2. **Nome do componente diferente do arquivo** — O `"component"` em interfaces.json deve corresponder exatamente ao nome do arquivo em `react/` (sem extensao).
3. **Nao adicionar builder `messages`** — Sem o builder, as traducoes nao funcionam.
4. **Props sem tipagem** — Sempre tipar as props com interface TypeScript.
5. **Esquecer o schema** — Sem `MyComponent.schema`, o componente nao aparece no Site Editor.
6. **Prefixo errado em messages** — `store/` para mensagens visíveis na loja, `admin/` para labels do Site Editor.
7. **Nao declarar policies no manifest** — Se o componente faz requests HTTP, adicionar `outbound-access` em `policies`.
