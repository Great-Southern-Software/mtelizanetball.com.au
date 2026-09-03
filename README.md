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
| Fixtures data | `data/fixtures.json` (generated, see below) |

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`, which builds the site with the
Roq GitHub Action and publishes it to GitHub Pages. One-time setup in the GitHub repo:
**Settings → Pages → Build and deployment → Source: GitHub Actions**.

The workflow also runs daily at 05:00 UTC so future-dated news posts publish automatically
and the fixtures page picks up the latest results.

## Fixtures & results

`content/fixtures.html` renders `data/fixtures.json`, which `scripts/fetch_fixtures.py`
pulls from NetballConnect (the FDNA draw, our results and the division ladders). The deploy
workflow runs the script before every build; it is best effort, so if NetballConnect is
unreachable the last committed JSON is used. To refresh locally:

```bash
python3 scripts/fetch_fixtures.py   # Python 3.9+, standard library only
```

The script picks the current year's FDNA competition whose name contains "Saturday" and
the teams whose names start with `MENC`. Override with `FIXTURES_COMPETITION_KEY`,
`FIXTURES_COMPETITION_MATCH`, `FIXTURES_TEAM_PREFIX` or `FIXTURES_YEAR` if that changes.
NetballConnect has no official API: the script uses the same public endpoints and public
token as its own draw pages, so it may need attention if NetballConnect changes.
