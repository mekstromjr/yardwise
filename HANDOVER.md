# YardWise: the maintainer's guide

For Mom and Dad. No jargon where plain words work; where a technical term is
unavoidable, it's explained the first time. You'll usually be working with an
AI assistant (Claude, ChatGPT) - this document is written so you can paste
sections of it to your assistant as context.

## The one-paragraph version

YardWise is a website that runs on Michael's home servers. Its code lives in a
GitLab "repository" (a shared folder with perfect memory of every change).
When you change the code and publish a new version, robots take over: they
build it, test it, and put it live at https://yardwise.meklab.net within about
ten minutes. You never touch the servers. If something goes wrong, the old
version keeps running and you tell Michael.

## What you need (one-time setup, Michael does this with you)

- A **GitLab account** at https://gitlab.meklab.net with access to the
  `meklab/yardwise` project - this is where the code lives.
- **Tailscale** on your computer (you already have it) - the site and GitLab
  are only reachable through it.
- A copy of the code on your computer ("clone"), which your AI assistant can
  help you get:
  ```bash
  git clone ssh://git@gitlab-ssh.meklab.net:2222/meklab/yardwise.git
  ```
- To run the app on your own computer while trying changes: install `uv`
  (ask your assistant: "install uv, the Python package manager"), then in the
  yardwise folder run:
  ```bash
  uv sync
  uv run python manage.py migrate
  uv run python manage.py createsuperuser   # makes your local login
  uv run python manage.py runserver
  ```
  and open http://localhost:8000. This local copy has its own separate
  database - nothing you do here touches the real site.

## How to make a change

Tell your AI assistant what you want ("make the plant names bigger", "add a
field for where I bought the plant"). Then this is the rhythm - your
assistant can run these commands, you supervise:

1. **Make a branch** (a scratch copy of the code):
   ```bash
   git checkout main && git pull
   git checkout -b my-change
   ```
2. **Let the assistant edit the code.** Check the result on your local
   server (step above). The tests must pass:
   ```bash
   uv run pytest
   ```
3. **Publish the branch and open a "merge request"** (a proposal to adopt
   your change):
   ```bash
   git add -A && git commit -m "describe the change"
   git push -u origin my-change
   ```
   Then open the link GitLab prints, click through to create the merge
   request, wait for the green pipeline (the robots running the tests), and
   press **Merge**.
4. **Release it.** Merging updates the code but does not change the live
   site. To release, publish a version tag - bump the last number:
   ```bash
   git checkout main && git pull
   git tag v0.2.4        # one higher than the last tag; `git tag` lists them
   git push origin v0.2.4
   ```
5. **Wait about ten minutes**, then check https://yardwise.meklab.net. That's
   it - no further steps exist.

If the pipeline turns red, the tests failed: your change has a problem. Paste
the pipeline's error text to your assistant and fix the branch - the live site
is unaffected until you merge and tag.

## What you can change freely

Everything in this repository: how screens look (`templates/`, `static/`),
what the app does (`garden/`), the database structure (your assistant will
create "migrations" for that - they apply automatically on release), tests,
and docs. Be bold. The worst realistic outcome is a red pipeline or a broken
version that Michael rolls back.

## What needs Michael (by design)

These aren't in this repository, and your accounts can't touch them - that's
deliberate, so a mistake here can never break the rest of the household's
systems:

- **Server settings**: memory/storage limits, the web address, certificates.
- **Secrets**: passwords and keys the app uses.
- **Logins**: adding a user or changing sign-in behavior (that's the
  auth.meklab.net screen you use to sign in).
- **Rollbacks and restores**: putting back an old version or recovering data.

If a change you want needs any of those, finish the code part, then tell
Michael what you need. "The app now sends email, it needs a mail password" is
a perfect message.

## If something looks wrong on the live site

1. Don't panic - the garden data is backed up nightly, and photos too.
2. Note what you did last (usually: which version tag you pushed).
3. Tell Michael: what you expected, what you see, and that version number.
   He can put the previous version back in a couple of minutes.

## Words you'll meet (cheat sheet for you and your assistant)

| Word | Meaning here |
|---|---|
| repository / repo | The project's folder in GitLab, with full history |
| branch | A scratch copy of the code to try a change on |
| commit | A saved snapshot of your edits with a note |
| merge request (MR) | "Please adopt my branch" - merging puts it on `main` |
| pipeline | Robots that test (and build) your code; green = good |
| tag / release | A published version number (`v0.2.4`); pushing one deploys |
| migration | A scripted database change; created by tooling, runs on release |
| deploy | The new version going live - automatic after a tag |

## For your AI assistant (paste this paragraph into it)

> You are helping maintain YardWise, a Django 5 + PostgreSQL app, server-side
> templates with htmx, packaged with uv, tests via pytest (`uv run pytest`,
> sqlite, zero setup). Design doc: docs/pdd.md; scope: docs/scope.md; schema:
> docs/design/schema.md. Style: no frontend build step, hand-written CSS with
> tokens in static/css/yardwise.css, phone-first. Rules: never commit to main
> (branch -> merge request); a release is a `vX.Y.Z` git tag on main;
> deployment is automatic after tagging - do not add deploy scripts, CI
> changes beyond .gitlab-ci.yml testing steps, Dockerfile changes are fine.
> Anything involving servers, secrets, or logins is out of scope - stop and
> say "this needs Michael".
