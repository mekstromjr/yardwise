# YardWise maintainer manual

**For the owner:** this file is written for your AI assistant. Start a session
(Claude, ChatGPT, etc.), attach or paste this whole file, and say what you
want in plain words - "make the plant names bigger", "add a place to note
which nursery a plant came from", "walk me through getting set up". The
assistant does the technical work; you direct and approve. When it says
something "needs Michael", that's real - text him.

You need two things, once, from Michael or Dad:
1. **Tailscale** running on your computer (you already have it).
2. An **access token** - a long password that lets your assistant work with
   the YardWise code and nothing else. Keep it out of chat logs where you
   can; if it ever leaks, tell Michael and he'll issue a new one (that is the
   entire blast radius - the token can only touch this one project).

Everything below is for the assistant.

---

## Agent operating manual

You are maintaining **YardWise**, a garden journal for the owner, running at
https://yardwise.meklab.net on a private homelab. You have a **project access
token** (env var `YARDWISE_TOKEN` below) scoped to the single GitLab project
`meklab/yardwise` on `gitlab.meklab.net`. The user is non-technical: explain
what you're doing in plain language, ask before anything irreversible, and
never show her raw tokens or stack traces without a translation.

### Environment facts

- GitLab web + API: `https://gitlab.meklab.net` (project `meklab/yardwise`,
  id 16) - reachable only over Tailscale, like the app itself.
- Clone over HTTPS with the token (no SSH setup needed):
  ```bash
  export YARDWISE_TOKEN=<the token the owner gives you>
  git clone "https://token:${YARDWISE_TOKEN}@gitlab.meklab.net/meklab/yardwise.git"
  ```
- Stack: Django 5 + PostgreSQL, server-rendered templates + htmx, uv-managed
  Python, pytest (sqlite - zero setup), hand-written CSS
  (`static/css/yardwise.css`, design tokens at the top). No frontend build
  step - keep it that way.
- Reference docs in-repo: `docs/pdd.md` (the full product vision - deferred
  features live here), `docs/scope.md`, `docs/design/schema.md`,
  `docs/backups.md`.
- Local dev server (its own sqlite database; cannot touch production):
  ```bash
  uv sync && uv run python manage.py migrate
  uv run python manage.py createsuperuser   # local-only login
  uv run python manage.py runserver         # http://localhost:8000
  ```

### The release lifecycle (the only path to production)

1. Branch from fresh main: `git checkout main && git pull && git checkout -b <topic>`
2. Edit; run `uv run pytest` and `uv run ruff check .` - both must pass.
3. Commit, push the branch, open an MR and wait for the pipeline:
   ```bash
   git push -u origin <topic>
   curl -sf -H "PRIVATE-TOKEN: $YARDWISE_TOKEN" -X POST \
     "https://gitlab.meklab.net/api/v4/projects/16/merge_requests" \
     -d "source_branch=<topic>" -d "target_branch=main" -d "title=<title>"
   # poll until the MR reports: pipeline success + detailed_merge_status=mergeable
   curl -sf -H "PRIVATE-TOKEN: $YARDWISE_TOKEN" \
     "https://gitlab.meklab.net/api/v4/projects/16/merge_requests/<iid>"
   ```
4. Merge (allowed when green): `PUT .../merge_requests/<iid>/merge`
5. Release = a version tag on main. Look at existing tags, bump the patch:
   ```bash
   git checkout main && git pull
   git tag v0.2.7 && git push origin v0.2.7
   ```
6. Deployment is fully automatic and takes about ten minutes. Verify:
   `curl -skL https://yardwise.meklab.net/healthz` returns `ok`, and the
   change is visible in a browser. There are no other deploy steps -
   **never** write deploy scripts, Kubernetes files, or CI publish jobs.

A red pipeline means tests failed; production is untouched. Fix the branch
and push again. A merged-but-untagged change simply isn't live yet.

### Hard rules

- Never commit directly to `main` (the server enforces this; don't fight it).
- Never force-push, delete branches you didn't create, or rewrite history.
- Never put the token in a committed file, code, or example. `.env` files
  stay gitignored.
- Database changes go through Django migrations (`makemigrations`); never
  edit migration history that's already on main. Migrations run automatically
  on deploy.
- Keep the design system: tokens in `yardwise.css`, phone-first, no CSS or JS
  frameworks, no build tooling, vendored htmx as-is.
- Tests exist to stay green; add tests with behavior changes. Never weaken an
  assertion just to pass - if a test fights you, say so and show the user.
- The PDD (`docs/pdd.md`) is the roadmap for new features - check whether the
  thing the owner wants is already designed there before inventing a shape.

### Out of scope - stop and say "this needs Michael"

Server resources, domains/certificates, secrets and passwords, login/SSO
behavior (the auth.meklab.net screen), Kubernetes/infrastructure, backups and
restores, rolling back a bad release, and anything touching repositories
other than `meklab/yardwise`. The token physically can't reach those; if a
task seems to require them, finish the code part and tell the owner exactly what
to ask Michael for, in one sentence she can copy.

### If production looks broken

Tell the owner calmly: nothing is lost (nightly database + photo backups).
Collect the facts - last tag pushed, what looks wrong - into one short
message for Michael. He can roll back in minutes. Do not attempt heroics
through the token.

### Session starter for the owner (example prompts)

- "Set me up from scratch on this laptop." (clone, uv sync, local server)
- "Add a 'watered today' quick button on a plant page."
- "The photos page feels slow - can you look?"
- "Release everything we've merged this week."
- "What did we change last month?" (`git log`, MR list)
