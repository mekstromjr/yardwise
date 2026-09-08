# PNW Home YardWise

> **Read-only mirror.** This project is developed on a self-hosted GitLab instance and
> mirrored to GitHub for visibility. Issues and pull requests are not accepted here;
> the mirror is overwritten on every push. Contact: see the profile of [@mekstromjr](https://github.com/mekstromjr).

*Know your yard. Grow it wisely.*

A self-hosted, phone-first yard and plant management application: a photo-forward
plant inventory with yard locations, flexible maintenance scheduling, garden
journaling, harvest tracking, and a durable long-term record of everything that
happens in the yard.

Runs at `yardwise.meklab.net` (Tailscale-gated, Authentik SSO).

## Documents

| Document | Purpose |
|---|---|
| [docs/pdd.md](docs/pdd.md) | The Product Design Document — authoritative product spec (all features, including post-MVP) |
| [docs/scope.md](docs/scope.md) | What is in the MVP vs. deferred, and why |
| [HANDOVER.md](HANDOVER.md) | Plain-English guide for maintaining this app: how to make a change, how a push becomes a deploy, what to ask Michael for |

## Status

MVP live at yardwise.meklab.net; releases deploy automatically from version
tags (see HANDOVER.md). Work is tracked in this project's
[issues](https://gitlab.meklab.net/meklab/yardwise/-/issues) and
[milestones](https://gitlab.meklab.net/meklab/yardwise/-/milestones);

## Stack (decided, see docs/scope.md for rationale)

- Django + PostgreSQL, server-rendered templates + htmx
- Photos on local volume storage (Longhorn PVC)
- Container image built by GitLab CI to `registry.meklab.net/meklab/yardwise`
- Deployed by Flux from `meklab/k8s`; releases promoted automatically by
  Flux image automation watching semver tags

Maintained with love by the Ekstrom family.
