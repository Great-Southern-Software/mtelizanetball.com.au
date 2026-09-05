# Working on this site

This is a Quarkus Roq static site for the Mt Eliza Netball Club. Keep it that way.

- Content lives in `content/` (front matter + Markdown or HTML), layouts and partials in
  `templates/`, styles in `public/css/`, images in `public/images/`, structured data in
  `data/`.
- Links between pages use `{=site.url('path')}`; images use `{=site.image('name.png')}`
  or `{=site.url('images/name.png')}`. Never hard-code the domain.
- `quarkus.qute.alt-expr-syntax=true` is on: Qute expressions are `{=expr}`. Wrap inline
  `<script>` and `<style>` bodies in `{| ... |}` so braces are left alone.
- Every page must render well at 360px wide. Tap targets at least 44px. Respect
  `prefers-reduced-motion`.
- Writing style: plain Australian English, no em or en dashes, no marketing filler, no
  exclamation marks, no emoji, nothing the club did not say. The elf hands you the full
  list as STYLE.md when it asks for work.
- Verify before you finish: `QUARKUS_HTTP_PORT=8765 QUARKUS_ROQ_GENERATOR_BATCH=true mvn -q -B package quarkus:run`
  must succeed and `target/roq/index.html` must exist.
- Do not add build tooling, server code, or third-party scripts beyond the embeds the site
  already relies on.

## News posts

This site's news collection is `news`, not `posts`: articles go in
`content/news/YYYY-MM-DD-slug.md` with front matter `title`, `description` and optionally
`image`; the layout `news-post` comes from `site.collections.news.layout` in
`config/application.properties`. The listing page already exists under `content/`; do not
create a second one. When a request talks about "posts" or a "blog", it means this news
collection.
