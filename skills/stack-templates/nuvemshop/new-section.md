---
name: nuvemshop-new-section
description: Criando novas secoes em tema classico Nuvemshop — config CMS, template, reuso, design system.
---

# Criando novas secoes em tema Nuvemshop (classico)

## Abordagem: reuso primeiro

Antes de criar uma secao nova, verificar se ja existe um snipplet reutilizavel que atende. Temas classicos tem componentes em `snipplets/` que podem ser combinados.

## Estrutura de uma secao

### 1. Configuracao no CMS (`config/settings.txt`)

Cada secao precisa de settings no admin para o lojista controlar conteudo. Exemplo:

```
[collapse]
  title = Nova secao

  [checkbox]
    name = show_nova_secao
    title = Mostrar secao
    default = true

  [text]
    name = nova_secao_title
    title = Titulo da secao

  [image]
    name = nova_secao_image
    title = Imagem da secao
    width = 1920
    height = 600
    description = Tamanho recomendado: 1920x600

  [text]
    name = nova_secao_image_alt
    title = Texto alternativo da imagem
    description = Descreva o que aparece na imagem para acessibilidade
```

### 2. Default values (`config/defaults.txt`)

```
show_nova_secao = true
nova_secao_title = Titulo padrao
```

Nota: settings de tipo `image` NAO aceitam default em `defaults.txt`.

### 3. Template (`snipplets/home/nova-secao.tpl`)

```twig
{% if settings.show_nova_secao or params.preview %}
<section class="nova-secao">
  <div class="container">
    {% if settings.nova_secao_title %}
      <h2 class="nova-secao__title">{{ settings.nova_secao_title }}</h2>
    {% endif %}

    {% set has_custom_image = 'nova_secao_image.jpg' | has_custom_image %}
    {% if has_custom_image %}
      <img src="{{ 'nova_secao_image.jpg' | static_url | settings_image_url('1080p') }}"
           srcset="{{ 'nova_secao_image.jpg' | static_url | settings_image_url('huge') }} 640w,
                   {{ 'nova_secao_image.jpg' | static_url | settings_image_url('original') }} 1024w,
                   {{ 'nova_secao_image.jpg' | static_url | settings_image_url('1080p') }} 1920w"
           sizes="100vw"
           alt="{{ settings.nova_secao_image_alt | default(store.name) }}"
           width="1920" height="600"
           loading="lazy" decoding="async">
    {% elseif params.preview %}
      <img src="https://placehold.co/1920x600" alt="" width="1920" height="600">
    {% endif %}
  </div>
</section>
{% endif %}
```

Pontos criticos:
- `or params.preview` — garante que aparece no editor do admin para o lojista configurar
- Placeholder so no preview (`params.preview`), nao no storefront
- `loading="lazy"` + `decoding="async"` (nao e LCP)
- `alt` com fallback para `store.name`

### 4. Incluir na home (`templates/home.tpl`)

```twig
{% snipplet "home/nova-secao.tpl" %}
```

### 5. CSS (`src/scss/`)

Adicionar estilos no arquivo SCSS adequado (critical ou async conforme necessidade). Usar BEM com contexto quando precisar vencer Bootstrap:

```scss
.nova-secao {
  .nova-secao__title {
    // estilos
  }
  .nova-secao__image {
    width: 100%;
    height: auto;
  }
}
```

### 6. Home order (se aplicavel)

Se a secao participa do sistema de ordenacao da home (`settings.home_order_position_N`), adicionar no branching do `templates/home.tpl`:

```twig
{% if position == 'nova_secao' %}
  {% snipplet "home/nova-secao.tpl" %}
{% endif %}
```

## Checklist

- [ ] Settings no `config/settings.txt`
- [ ] Defaults no `config/defaults.txt` (para tipos que aceitam)
- [ ] Template em `snipplets/`
- [ ] `or params.preview` em condicoes de visibilidade
- [ ] Imagens com `alt`, `width`, `height`
- [ ] Placeholder via `placehold.co` no preview
- [ ] CSS no arquivo SCSS correto (nao no output)
- [ ] Incluido no template pai (`home.tpl`, `page.tpl`, etc.)
- [ ] Build: `npm run builder:build`
- [ ] Deploy: `npm run theme:push`
