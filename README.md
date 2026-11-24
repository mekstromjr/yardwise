# YardWise

A self-hosted, phone-first garden journal for one household: plant inventory with photos, a
traced property map, recurring yard tasks, a journal, and an optional AI assistant, built with
Django and htmx.

![YardWise Today screen: a sidebar with Today, Plants, Tasks, Journal, Beds, Map, Assistant and Alerts; a "Due now" card reading "Nothing due today"; an "Ask the garden" question box with a link to identify a plant, weed, or bug from a photo; and shortcut tiles for Assistant, Map, Problems, Planner and Irrigation](docs/screenshots/yardwise-today.webp)

**Status:** in use by its non-technical owner, deployed privately at `yardwise.meklab.net`
(Tailscale plus SSO). Development started in August 2026; 37 tagged releases so far, latest
`v0.9.17`.

Developed on a self-hosted GitLab; this GitHub repo is a read-only mirror. Issues and pull
requests are not accepted here.

## What it does

- **Today**: overdue, due and upcoming tasks plus planner milestones, with quick actions and an
  "Ask the garden" box.
- **Plants**: inventory with search and filters, photo galleries (primary photo, categories,
  seasons), activity history, harvest log, archive instead of delete. A name is enough to save.
- **Tasks**: exact-date, seasonal-window and interval schedules; completing one keeps history and
  schedules the next occurrence.
- **Journal**: free-text entries with photos, linked to plants and beds.
- **Property map**: a Leaflet map traced over an aerial image, with bed polygons, plant points and
  an A1/B4-style grid overlay.
- **Planner, Problems, Irrigation**: seasonal vegetable plantings driven by a climate profile; a
  weed/pest/disease case log; sprinkler zones and components that start as "Unknown" and are
  verified over time.
- **Notifications**: in-app alerts for due and overdue work, with snooze.
- **AI assistant (optional)**: identify a plant from a photo, look up a plant, fill in missing
  fields on a plant record, ask free-form questions with cited sources, and suggest a bed outline
  on the map. Runs through OpenRouter; with no API key the features are hidden.
- **Shared gardens**: each user owns a garden and can invite another user by username to tend it;
  members switch between gardens from their account page.

## Engineering decisions

- **Built for an AI-assisted, non-technical maintainer.** The repo ships
  [docs/HANDOVER.md](docs/HANDOVER.md), a maintainer manual written for an AI assistant: the owner
  pastes it into a chat session, asks for a change in plain words, and the assistant follows the
  documented branch, merge request, pipeline and tag workflow using a token scoped to this one
  project. Everything outside the app code (infrastructure, secrets, backups, rollback) is
  explicitly out of scope and routed back to the maintainer. The stack choice follows from this:
  [docs/scope.md](docs/scope.md) picks the most conventional, best-documented option with no
  frontend build step.
- **The pipeline is the gate.** CI runs secret detection, `ruff` and `pytest` on every branch and
  tag; nothing reaches production without a green pipeline and a merge to `main`.
- **A release is a git tag.** Pushing `vX.Y.Z` builds an image tagged with the version (Kaniko,
  see [.gitlab-ci.yml](.gitlab-ci.yml)), and Flux image automation in the cluster repo promotes
  the new semver tag. Migrations run on container start, so a release needs no manual step.
- **Tests need zero setup.** The suite runs on SQLite with in-memory file storage
  (`config/settings_test.py`), so `uv run pytest` works on a fresh laptop. Production uses
  PostgreSQL.
- **Stateless pod.** Photos go to S3-compatible object storage (Garage) when `YARDWISE_S3_BUCKET`
  is set, falling back to the local filesystem otherwise, so the pod holds no data.
- **No scheduler.** Notifications are materialized at request time and made idempotent by a
  unique `dedupe_key` ([garden/notify.py](garden/notify.py)). Planner milestones and map grid
  cells are derived on read, never stored, so editing the climate profile or grid reflows them.
- **AI output is a suggestion.** Nothing from the model writes to garden records until the user
  accepts it, and enrichment only proposes values for empty fields. The client is stdlib `urllib`
  rather than another dependency ([garden/ai.py](garden/ai.py)).
- **SSO via forward-auth, behind a flag.** In the cluster, Authentik at the ingress injects the
  username header and Django trusts it only when `AUTH_TRUST_PROXY_HEADER` is set; locally the app
  uses Django's own session login.
- **No frontend toolchain.** Server-rendered templates, hand-written CSS with design tokens, and
  vendored htmx and Leaflet.

## Run it locally

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). With no `POSTGRES_HOST` set the app
uses a local SQLite file, so this is all you need:

```bash
git clone https://github.com/mekstromjr/yardwise.git
cd yardwise
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
DJANGO_DEBUG=true uv run python manage.py runserver
```

Open http://localhost:8000 and sign in with the superuser. `DJANGO_DEBUG=true` is required for
local runs: the default is production mode (secure cookies, a collectstatic manifest).

To develop against PostgreSQL instead, start the compose database and point Django at it. Django
does not read `.env`; only compose does, so export the variables in your shell (do not source
`.env.example` wholesale, its host and debug values are for production):

```bash
echo "POSTGRES_PASSWORD=localdev" > .env
docker compose up -d db
export POSTGRES_HOST=localhost POSTGRES_PASSWORD=localdev
uv run python manage.py migrate
DJANGO_DEBUG=true uv run python manage.py runserver
```

AI features appear when `OPENROUTER_API_KEY` is set. See [.env.example](.env.example) for the
other settings.

## Tests and CI

```bash
uv run pytest -q      # 220 tests, SQLite, no services needed
uv run ruff check .
```

The GitLab pipeline ([.gitlab-ci.yml](.gitlab-ci.yml)) runs secret detection, `ruff` and
`pytest`, then builds the container image on `main` and on semver tags.

## Documents

| Document | Purpose |
|---|---|
| [docs/pdd.md](docs/pdd.md) | Product design document: the full product spec, including features not built yet |
| [docs/scope.md](docs/scope.md) | What was in the MVP, what was deferred, and the stack rationale |
| [docs/design/schema.md](docs/design/schema.md) | Data model |
| [docs/map-versioning.md](docs/map-versioning.md) | Rules for the authoritative property map image |
| [docs/backups.md](docs/backups.md) | What is backed up and how to restore it |
| [docs/HANDOVER.md](docs/HANDOVER.md) | Maintainer manual for the owner's AI assistant |

## License

[MIT](LICENSE)
