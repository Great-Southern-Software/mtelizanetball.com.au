# Mt Eliza Netball Club Website

Static site for [mtelizanetball.com.au](https://www.mtelizanetball.com.au), built with
[Quarkus Roq](https://iamroq.dev/) and deployed to GitHub Pages.

## Local development

Requires Java 21+.

```bash
./mvnw quarkus:dev        # live-reload dev server on http://localhost:8080
```

Or with the [Roq CLI](https://iamroq.dev/docs/getting-started/): `roq start`.

## Generate the static site

```bash
QUARKUS_ROQ_GENERATOR_BATCH=true ./mvnw -B package quarkus:run
```

Output lands in `target/roq/`.

## Editing content

| What | Where |
| --- | --- |
| Pages | `content/*.md` (frontmatter + Markdown) |
| News posts | `content/news/YYYY-MM-DD-slug.md` |
| Layouts & partials | `templates/` |
| Styles | `public/css/main.css` |
| Images / PDFs | `public/images/`, `public/docs/` |
| Site config | `config/application.properties` |

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`, which builds the site with the
Roq GitHub Action and publishes it to GitHub Pages. One-time setup in the GitHub repo:
**Settings → Pages → Build and deployment → Source: GitHub Actions**.

The workflow also runs daily at 05:00 UTC so future-dated news posts publish automatically.
