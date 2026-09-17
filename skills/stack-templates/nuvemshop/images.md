---
name: nuvemshop-images
description: Tratamento de imagens em temas Nuvemshop — variants, srcset, lazy loading, LCP, placeholders.
---

# Imagens em temas Nuvemshop

## Variants da plataforma

Quando voce usa `settings_image_url('variant')`, a Nuvemshop devolve uma versao pre-renderizada, nao a imagem original.

| Variant | Largura |
|---|---|
| `tiny` | 50px |
| `thumb` | 100px |
| `small` | 240px |
| `medium` | 320px |
| `large` | 480px |
| `huge` | 640px |
| `original` | **1024px** (NAO e a imagem do upload) |
| `1080p` | 1920px (maior disponivel) |

**Causa #1 de imagem borrada:** usar `original` achando que e tamanho cheio. Para banner full-bleed, usar `1080p` (1920px).

Aplica-se a `| settings_image_url`, `| product_image_url`, `| category_image_url`.

## Receita: srcset de banner full-bleed

```twig
<img srcset="{{ 'hero.jpg' | static_url | settings_image_url('huge')     }} 640w,
             {{ 'hero.jpg' | static_url | settings_image_url('original') }} 1024w,
             {{ 'hero.jpg' | static_url | settings_image_url('1080p')    }} 1920w"
     sizes="100vw"
     src="{{ 'hero.jpg' | static_url | settings_image_url('1080p') }}"
     alt="{{ settings.hero_alt | default(store.name) }}"
     width="1920" height="900"
     fetchpriority="high">
```

**NAO declare `original 3840w`** — o variant entrega 1024, browser estica, resultado borrado.

## Receita: srcset de slot menor (card 1/3)

```twig
<img srcset="{{ x | settings_image_url('medium') }} 320w,
             {{ x | settings_image_url('large')  }} 480w,
             {{ x | settings_image_url('huge')   }} 640w"
     sizes="(min-width: 1250px) 390px,
            (min-width: 770px) calc((100vw - 80px) / 3),
            calc(100vw - 40px)"
     alt="..." width="780" height="780">
```

## `alt` e obrigatorio (WCAG 1.1.1)

Toda `<img>` precisa de `alt`. Fontes em ordem de preferencia:
1. Setting dedicada no `settings.txt` (tipo `text`)
2. Fallback derivado (`store.name`, titulo da secao)
3. Generico com indice (`"Banner {{ loop.index }}"`) — ultimo recurso

Imagem decorativa: `alt=""` explicito.

## Carregamento — `fetchpriority` e `loading`

- **LCP (primeiro banner above-the-fold):** `fetchpriority="high"`, sem `loading="lazy"`
- **Todas as outras:** `loading="lazy"` + `decoding="async"`

`fetchpriority="high"` em mais de uma imagem polui o critical path.

## Deteccao de LCP na home

A primeira imagem da primeira secao (`settings.home_order_position_1`) e o LCP:

```twig
{% if template == 'home' and settings.home_order_position_1 == 'slider' %}
  <link rel="preload" fetchpriority="high" as="image" href="..." imagesrcset="...">
{% endif %}
```

## Aspect-ratio diferente desktop vs mobile

Usar `<picture>` com duas settings separadas. NAO usar `object-fit: cover` (crop arbitrario corta conteudo):

```twig
<picture>
  <source media="(max-width: 575px)"
          srcset="{{ 'hero_mobile' | settings_image_url('medium') }} 320w,
                  {{ 'hero_mobile' | settings_image_url('large')  }} 480w">
  <img src="{{ 'hero' | settings_image_url('1080p') }}"
       srcset="..." alt="..." width="1920" height="900">
</picture>
```

## Placeholder via `placehold.co`

Settings de imagem nao aceitam default em `defaults.txt`. Usar placeholder quando `has_custom_image == false`:

```twig
{% if has_custom_image %}
  <img src="{{ 'hero' | settings_image_url('1080p') }}" ...>
{% else %}
  <img src="https://placehold.co/1920x900" alt="" width="1920" height="900">
{% endif %}
```

URL minima: so `placehold.co/{W}x{H}`. Sem cores customizadas, sem `?text=`. O servico imprime as dimensoes nativamente.

## Hint no settings.txt

```
[image]
  name = hero
  title = Imagem do hero
  width = 1920
  height = 900
  description = Tamanho recomendado: 1920x900
```

Dimensoes na medida CSS de renderizacao (1x), nao retina.
