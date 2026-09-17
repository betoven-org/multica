---
name: css-handles
description: Como usar CSS Handles corretamente em componentes VTEX IO Store Framework.
---

# CSS Handles em VTEX IO

CSS Handles sao o mecanismo oficial de estilizacao em VTEX IO Store Framework. Eles geram classes CSS unicas por componente, permitindo customizacao sem conflitos de escopo.

## Quando usar

- Sempre que criar um componente React em VTEX IO que renderiza HTML visivel.
- Para expor pontos de customizacao ao lojista/agencia.
- Em vez de inline styles, classes globais ou CSS Modules.

## Steps

### 1. Declarar os handles

Crie uma constante com todos os handles do componente:

```typescript
// react/components/ProductCard.tsx
import { useCssHandles, CssHandlesTypes } from 'vtex.css-handles'

const CSS_HANDLES = [
  'productCard',
  'productCard--highlighted',
  'productCardImage',
  'productCardTitle',
  'productCardPrice',
  'productCardPriceOld',
] as const
```

### 2. Usar o hook useCssHandles

```typescript
const ProductCard: React.FC<Props> = ({ product, highlighted }) => {
  const handles = useCssHandles(CSS_HANDLES)

  return (
    <div className={`${handles.productCard} ${highlighted ? handles['productCard--highlighted'] : ''}`}>
      <img
        className={handles.productCardImage}
        src={product.imageUrl}
        alt={product.name}
        width={300}
        height={300}
      />
      <h3 className={handles.productCardTitle}>{product.name}</h3>
      <div className={handles.productCardPrice}>
        {product.oldPrice && (
          <span className={handles.productCardPriceOld}>
            {product.oldPrice}
          </span>
        )}
        <span>{product.price}</span>
      </div>
    </div>
  )
}
```

### 3. Tipar handles quando passados como prop

```typescript
type CssHandles = CssHandlesTypes.CssHandlesBag<typeof CSS_HANDLES>

interface Props {
  handles?: CssHandles
}
```

## Convencao de nomenclatura

- **camelCase** sempre: `productCard`, nao `product-card`.
- Prefixo com nome do componente: `productCard`, `productCardImage`.
- Modificadores com `--`: `productCard--highlighted`, `productCard--outOfStock`.
- Hierarquia: `container` > `wrapper` > `item` > elementos especificos.

## Common mistakes

1. **Usar inline styles** — Nunca. Inline styles nao podem ser sobrescritos pelo lojista. Sempre use handles.
2. **Nao exportar handles suficientes** — Cada elemento visivel deve ter um handle. O lojista precisa poder customizar qualquer parte.
3. **Nomes genericos** — `container`, `wrapper` sem prefixo causam conflito. Sempre prefixe com o nome do componente.
4. **Esquecer `as const`** — Sem `as const`, o TypeScript infere `string[]` e perde autocomplete.
5. **Usar className hardcoded** — Nunca use classes CSS diretas. Sempre passe pelo handles.
6. **CSS Modules** — Nao use CSS Modules em VTEX IO. O padrao e CSS Handles.

## Exemplo de estilizacao pelo lojista

O lojista customiza via `styles.json` ou CSS override no tema:

```css
/* styles/css/vtex.app-name.css */
.productCard {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 16px;
}

.productCard--highlighted {
  border-color: #ff0000;
}

.productCardPriceOld {
  text-decoration: line-through;
  color: #999;
}
```
