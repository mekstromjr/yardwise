# YardWise scope: MVP and deferred modules

The [PDD](pdd.md) describes the complete product. This document records which
parts are in the MVP and which are deferred, and the reasoning. The cut follows
the PDD's own Builder Handoff Summary (section 1):

> Build PNW Home YardWise as a responsive, photo-forward personal garden
> management web application. [...] Do not overbuild the product with AI,
> weather integration, or an interactive property map. The data model and
> navigation should leave clear room for those integrated capabilities.

## In the MVP (milestone `yardwise: MVP`)

- **Plants**: inventory with search, filter, photo-card and list views;
  progressive-entry add/edit (a name is enough to save)
- **Plant Profile**: photos (categories, seasons, primary photo), activity
  history timeline, upcoming tasks, harvest history, archive-not-delete
- **Tasks**: exact date, seasonal window, and interval timing; yearly and
  interval recurrence; completion preserves history and schedules the next
  occurrence
- **Journal**: free-text entries, photo attachments, plant/bed links,
  chronological feed with filters
- **Harvests**: quick-entry harvest events on edible plants, season totals
- **Today**: dashboard of overdue / due / upcoming, quick actions
- **Beds & areas**: a simple named list with stable IDs (`BED-001` style) and
  archive semantics — no map geometry yet, but every location reference is
  designed so the future map module attaches without a schema rewrite
- **Auth**: Authentik OIDC SSO
- **Ops**: CI pipeline, container image, Flux-managed deployment, backups of
  database and photos

## Deferred (each has a milestone and a backlog issue)

| Module | Milestone | PDD section |
|---|---|---|
| Interactive property map (aerial tracing, grid, polygons) | `yardwise: Property Map` | 4 |
| Weeds, pests, diseases (Yard Problems) | `yardwise: Yard Problems` | 7 |
| AI identification, enrichment, natural-language questions | `yardwise: AI Assistance` | 9 |
| Vegetable planner, seasonal plantings, seedlings, climate profile | `yardwise: Garden Planner` | 6 |
| Sprinkler & irrigation discovery | `yardwise: Irrigation` | 8 |
| Push notifications, seasonal dashboard, weather guidance | `yardwise: Notifications` | 10 |

## Data-model rules honored now, even for deferred features

From PDD section 3 ("Canonical data rules") — deferring a feature is cheap,
retrofitting a data model is not:

1. **Photos are shared assets**: stored once, linkable from plant, journal,
   harvest (and later problem/treatment) records. Never duplicated per record.
2. **Archive, never delete**: plants, beds, and tasks are archived with their
   history intact.
3. **Stable IDs**: beds get permanent system IDs independent of display names;
   renames touch only the display name.
4. **Plant identity vs. placement**: reusable species/cultivar facts are kept
   separable from the specimen record so the variety/seasonal-planting split
   (PDD section 6) can be introduced later without migration pain.
5. **Uncertainty is a valid state**: fields that will later interact with AI
   enrichment avoid coercing unknown to a fake default.

## Stack rationale

Django + PostgreSQL, server-rendered templates with htmx, one container.

The deciding constraint is **who maintains this after handover**: a
non-programmer working with an AI assistant. That favors the most
conventional, most documented, least tooling-heavy stack available —
batteries-included framework (auth, ORM, migrations, admin), no frontend
build pipeline, one deployable unit. Image versions are pinned; upgrades are
deliberate acts, not side effects.
