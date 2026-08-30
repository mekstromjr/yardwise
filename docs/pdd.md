**PNW Home YardWise**

**Programmer-Ready Product Design Document**

*Know your yard. Grow it wisely.*

Consolidated structure • canonical rules • duplication/conflict cleanup

# Table of Contents

1.  [1. Product Definition & Scope](#product-definition-scope)

2.  [2. Product Navigation & Daily Experience](#product-navigation-daily-experience)

3.  [3. Shared Domain Model & Cross-Cutting Rules](#shared-domain-model-cross-cutting-rules)

4.  [4. Property Map, Beds & Spatial Interaction](#property-map-beds-spatial-interaction)

5.  [5. Plant Inventory, Profiles, Photos & Journal](#plant-inventory-profiles-photos-journal)

6.  [6. Annuals, Vegetables, Seedlings & Harvests](#annuals-vegetables-seedlings-harvests)

7.  [7. Yard Problems: Weeds, Pests & Plant Health](#yard-problems-weeds-pests-plant-health)

8.  [8. Sprinkler & Irrigation System](#sprinkler-irrigation-system)

9.  [9. AI Assistance, Confidence & User Authority](#ai-assistance-confidence-user-authority)

10. [10. Notifications, Tasks, Calendar & Seasonal Guidance](#notifications-tasks-calendar-seasonal-guidance)

11. [11. Hosting, Security, Backup & Device Access](#hosting-security-backup-device-access)

12. [12. Canonical User Flows](#canonical-user-flows)

13. [13. Consolidated Functional Requirements & Acceptance Criteria](#consolidated-functional-requirements-acceptance-criteria)

14. [14. Implementation Notes & Resolved Conflicts](#implementation-notes-resolved-conflicts)

# 1. Product Definition & Scope

PNW Home YardWise is a privately hosted, responsive yard and plant management application designed for use from a phone, tablet, or laptop. It provides a single, long-term record of the plants, weeds, pests, diseases, maintenance activities, photographs, harvests, and observations associated with a residential property. The application is designed to be practical while standing in the yard: users can quickly identify or add a plant, photograph a problem, record work performed, check what needs attention, and review the history of a plant or area.

The product combines a photo-forward plant inventory with yard locations, customizable tags, maintenance scheduling, seasonal care windows, recurring tasks, garden journaling, harvest tracking, and a chronological activity history. Each plant has a living profile containing identification details, cultivar information, care requirements, location, photos, seasonal events, maintenance records, health history, and linked tasks.

PNW Home YardWise also includes a unified Yard Problems system for weeds, pests, and plant diseases. Weed records document identification, infestation locations, spread characteristics, the best time and method for control, treatment history, and required follow-up. Plant health records allow symptoms and photographs to be documented, possible diagnoses to be compared, diagnostic confidence to be recorded, and treatment plans to be scheduled and monitored over time. Disease and treatment history remains attached to the affected plant so recurring problems can be recognized across seasons.

AI-assisted features support plant and weed identification, plant-health assessment, natural-language questions, care recommendations, and analysis of historical garden records. AI suggestions are presented with appropriate uncertainty and require user confirmation before changing plant records, diagnoses, or treatment plans. The system can use the property's plant inventory, location, season, maintenance history, journal entries, photographs, and available weather context to make recommendations relevant to the actual yard.

The application is self-hosted on a privately controlled server. Garden records and photographs are private by default and are not dependent on a public consumer cloud service for core operation. The same responsive web application is accessible on the home network from a laptop or mobile device and can support secure remote access through an authenticated private connection. The deployment supports authentication, HTTPS, backups of both records and photographs, data export, and migration to another privately controlled server.

The finished product should feel like an intelligent digital garden notebook rather than administrative software: visual, calm, easy to navigate, forgiving of incomplete records, and fast enough for everyday use outdoors. Its purpose is not simply to catalog plants, but to preserve the accumulated knowledge of the yard and turn that history into useful guidance about what is growing, what is changing, what needs attention, and what has worked before.

## Product Vision

PNW Home YardWise is a mobile-friendly personal yard management application that gives a homeowner one place to identify, catalog, locate, maintain, photograph, and document the plants growing on their property. The application should be simple enough to use while standing in the yard with a phone, while preserving enough structured history to become more valuable every season.

### Primary goal

Answer three everyday questions quickly: What plants do I have? What needs my attention now? What have I done with this plant before?

### Design principles

- Photo-first and garden-friendly: large images, large tap targets, minimal typing.

- Progressive data entry: a plant can be saved with only a name, photo, and location; details can be added later.

- History matters: completed maintenance, observations, photos, and harvests remain attached to the plant.

- Flexible gardening time: support exact dates, recurring intervals, and seasonal windows such as “late winter.”

- User-controlled vocabulary: yard areas, tags, task categories, and plant types are editable in the app.

- AI enhances the garden record; it should not be required for the core application to work.

## Target User and Use Cases

The product is designed for a homeowner with a diverse established yard who wants a practical memory system rather than a professional horticulture database. No coding or technical knowledge should be required to use or maintain the application.

### Core use cases

- Walk through the yard and quickly add an existing plant.

- Look up a plant and see its photos, location, care information, and history.

- See which gardening jobs are due now or coming soon.

- Record that a plant was pruned, fertilized, watered, treated, transplanted, divided, or harvested.

- Add an observation or photograph to a garden journal.

- Filter plants by location, type, tag, bloom period, harvest period, or care need.

- Review prior-year activity to remember what worked and when events occurred.

## Builder Handoff Summary

Build PNW Home YardWise as a responsive, photo-forward personal garden management web application. The product must make it exceptionally easy to catalog plants, organize them by yard location, schedule flexible recurring maintenance, record completed garden work, and keep a photographic journal. Prioritize mobile usability and durable historical records. Do not overbuild the product with AI, weather integration, or an interactive property map. The data model and navigation should leave clear room for those integrated capabilities.

[Back to Table of Contents](#table-of-contents)

# 2. Product Navigation & Daily Experience

## Information Architecture

Primary navigation should remain visible at the bottom on phones and as a sidebar or bottom navigation on larger screens. PNW Home YardWise should use five destinations.

### Global actions

- Add Plant

- Add Task

- Add Journal Entry

- Record Activity

- Take/Add Photo

- Is this a weed?

## Screen-by-Screen Blueprint

### 1 Home / Today

The dashboard should prioritize action rather than statistics. The first screen should immediately show what is due, overdue, and approaching.

- Greeting/season header and current date

- Due today / overdue tasks

- This week’s tasks

- Coming soon / seasonal tasks

- Quick-action buttons: Add Plant, Add Task, Journal, Photo

- Optional summary cards: total plants, tasks completed this month, recent journal entries

- Recent plant activity/photos

Empty state: “Your garden is ready to grow. Add your first plant.” with a prominent Add Plant button.

### 2 Plants

- Search by common name, botanical name, cultivar, tag, or location

- Toggle between photo-card view and compact list view

- Filters for yard area, plant type, edible/ornamental, tag, and status

- Sort by name, recently added, recently updated, or location

- Floating/prominent Add Plant button

### 3 Add / Edit Plant

Use a short first step and optional expandable sections. Do not present a long intimidating form.

- Basics: common name, cultivar/variety, photo, plant type.

- Location: yard area, bed/location note.

- Details: botanical name, edible/ornamental, evergreen/deciduous, approximate age/date planted.

- Growing conditions: sun, water, soil notes, mature size.

- Seasonal information: bloom, harvest, prune, fertilize periods.

- Safety & notes: pet toxicity, general notes, source/nursery, optional purchase information.

- Tags: user-defined labels.

Minimum save requirement: a display name. Photo and location are strongly encouraged but not mandatory.

### 4 Plant Profile

- Hero photo, common name, cultivar, botanical name, and location

- Quick actions: Record Activity, Add Photo, Add Task, Journal Note

- Overview section

- Care section

- Upcoming Tasks section

- Activity History timeline

- Photo timeline

- Journal entries related to this plant

- Harvest history when applicable

- Edit and archive controls

Record Activity choices: Pruned, Fertilized, Harvested, Sprayed/Treated, Watered, Transplanted, Divided, Planted, Mulched, Pest/Disease Check, Other.

### 5 Tasks

- Views: Due, Upcoming, Completed, All

- Task can apply to one plant, multiple plants, a tag/group, or a yard area

- Timing: exact date, seasonal window, or interval

- Recurrence: none, yearly, monthly, every N weeks/months, or seasonal

- Priority and optional notes

- Completion records actual completion date and preserves history

- Recurring completion generates or calculates the next occurrence

### 6 Calendar

Calendar functionality can initially live inside Tasks as a month/list toggle to keep PNW Home YardWise simpler. It should show maintenance windows and exact-date tasks without pretending a seasonal job has a single precise date.

### 7 Journal

- Date/time automatically recorded

- Free-text entry optimized for voice dictation

- Attach one or more photos

- Optionally link to a plant, multiple plants, or yard area

- Optional tags such as weather, bloom, pest, harvest, project, observation

- Chronological feed with search and filters

### 8 Settings

- Home location / growing region

- Yard areas and beds

- Plant types

- Custom tags

- Task/activity categories

- Season definitions/preferences

- Notification preferences

- Data export/backup and restore strategy

## Daily Use, Field Capture & Decision Support

PNW Home YardWise should make a complex property-management database feel simple in daily use. The following capabilities are core product features intended to minimize navigation, support rapid outdoor data capture, and surface the most useful information at the moment it is needed.

### 1 Today - Daily Home Screen

- Today should be the default operational home screen and answer: What should I do in the yard today?

- Prioritize a short, manageable set of items rather than presenting every open record.

- Include planting windows, seed-starting and hardening reminders, likely harvests, irrigation issues, pest/disease follow-ups, overdue tasks, watched plants, and timely photo opportunities.

- Group lower-priority work under Coming Soon or Later This Season.

- Each item should link directly to the relevant plant, bed, map location, task, or problem record.

- Allow Complete, Snooze, Reschedule, Dismiss, and Not Applicable where appropriate.

### 2 Universal Quick-Add Action

- Provide one persistent + action optimized for phone use.

- Quick actions should include Identify/Add Plant, Is This a Weed?, What Is This Pest?, Plant Problem, Add Photo, Journal Note, Quick Harvest, and Add Task.

- Pre-fill current context when launched from a plant, bed, map location, or seasonal planting.

- Keep the first capture screen minimal; optional details can be added afterward.

### 3 What Is Here? Map Action

- Allow the user to tap/click a map location and ask What Is Here?

- Return the containing bed/area plus a concise summary of plants, trees, seasonal plantings, irrigation, weeds, pests, diseases, tasks, and other mapped items at or near that location.

- Use zoom and category filters to refine crowded results.

- Each result must link to its full record and highlight its exact mapped position.

### 4 QR and NFC Plant Labels

- Support optional weather-resistant QR codes and NFC tags linked to plant, bed, irrigation-component, or other records.

- Scanning a label should open the corresponding record directly on an authorized device.

- Provide printable label identifiers and allow replacement labels without losing record history.

- Labels must use non-sensitive opaque identifiers rather than exposing private database information in the code itself.

- QR/NFC use is optional; all records remain fully usable without physical labels.

### 5 Walk the Yard Mode

- Provide a phone-first field mode for rapidly recording observations while walking the property.

- Allow sequential capture of photos, plant observations, weeds, pests, disease symptoms, broken sprinklers, harvest observations, and maintenance needs without returning to the main navigation between entries.

- Use current map/bed context to reduce repetitive location entry.

- At the end of a walk, show a review summary and allow observations to be converted into tasks, problem cases, journal entries, or plant updates.

- Unfinished observations may be saved as an inbox for later review rather than forcing complete classification outdoors.

### 6 Voice Entry and Dictation

- Allow voice capture for journal notes, observations, harvest notes, maintenance findings, and Walk the Yard entries.

- AI may propose structured fields from dictated language, including plant, bed, problem type, date, quantity, or requested follow-up.

- Show the proposed structured entry for user approval before committing inferred changes.

- Preserve the original dictated/transcribed note when useful so structured interpretation can be corrected later.

### 7 Plant At-a-Glance Card

- Opening a plant should first show a concise At-a-Glance view rather than the full database record.

- Include primary photo, common/cultivar name, bed/location, current status, next recommended action, bloom/fruit/harvest status when applicable, active problems, watched status, and Show on Map.

- Provide clear routes to Care, Photos, Harvests, Problems, Journal/History, and full botanical details.

- Prioritize current actionable information while keeping detailed reference data one level deeper.

### 8 Favorites and Watch List

- Allow any plant, bed, seasonal planting, irrigation zone, or active problem to be marked Favorite or Watch.

- Watched records receive increased prominence on Today and can have enhanced follow-up reminders.

- Watching should not require creation of a formal task.

- Allow a short watch reason such as Newly planted, Ripening fruit, Recovering from disease, or Monitor irrigation.

- Provide one Watch List view and simple unwatch controls.

### 9 Weather-Aware Recommendations

- Optionally incorporate current and forecast local weather into gardening guidance while retaining climate/frost-date baselines.

- Examples include delaying irrigation after significant rain, frost cautions for transplants, heat/watering cautions, favorable planting windows, and weather-sensitive treatment or pruning reminders.

- Weather recommendations are advisory and must not silently alter user schedules or confirmed records.

- Clearly show when a recommendation is weather-dependent and when forecast uncertainty is relevant.

- Users can disable weather-based guidance independently of ordinary task reminders.

### 10 Seasonal Dashboard

- Provide a seasonal view organized around Now, Coming Soon, and Later This Season rather than relying only on exact calendar dates.

- Include planting, bloom, harvest, pruning/care, pest monitoring, irrigation, photo opportunities, and seasonal maintenance.

- Allow filtering by bed, plant type, edible/ornamental, problem category, or task type.

- Use this dashboard to complement, not duplicate, the more focused Today screen.

### 11 Before-and-After / Time Comparison

- Make photo comparison a first-class action from plant, bed, problem, treatment, and journal records.

- Support side-by-side comparisons such as Spring this year vs. Spring last year, before vs. after pruning, and disease discovery vs. post-treatment.

- Allow matching by season, year, photo category, or manually selected images.

- Preserve captions, dates, treatment/event links, and other context with each compared image.

- Allow comparisons to be referenced in journal entries and yearly reviews.

### 12 Cross-Cutting Clean-Interface Rules

- Use progressive disclosure throughout the application: show the minimum information needed for the current task and reveal deeper detail through selection, expansion, filtering, or zoom.

- Prefer context-aware actions over large permanent menus.

- Preserve the user's place, filters, zoom level, and selection when moving between map, bed, plant, and detail screens whenever practical.

- Use counts and summaries instead of rendering every marker or record at once.

- AI-generated suggestions must remain distinguishable from user-confirmed information and must respect all user overrides.

[Back to Table of Contents](#table-of-contents)

# 3. Shared Domain Model & Cross-Cutting Rules

## Canonical data rules

- Plant identity and plant placement are separate concepts: reusable species/cultivar facts belong to a Plant/Variety record; a specific specimen or seasonal planting owns location and history.

- Annual crops use a permanent variety record plus a year-specific Seasonal Planting record. Perennials/trees/shrubs use persistent Plant records with location history.

- User-entered or user-corrected values are authoritative. AI suggestions may fill missing data but never silently overwrite a user override.

- Unknown, Suspected, Likely, Confirmed, and Not Applicable are valid states where uncertainty matters; the UI must not coerce uncertain observations into confirmed facts.

- Photos are stored once and may be linked to multiple records (plant, journal, harvest, pest/disease case, treatment) rather than duplicated.

- Historical records are archived, not deleted, when beds are renamed/retired, plants are moved/removed, or seasonal plantings end.

## Data Model

The implementation may choose its own technical database structure, but the product must preserve the following logical entities and relationships.

## Gardening Time & Recurrence Rules

Gardening does not fit a conventional appointment calendar. The app must distinguish between a deadline and a horticultural window.

- Exact date: a specific due date such as March 15.

- Seasonal window: early/mid/late spring, summer, fall, winter, or a user-defined month range.

- Interval: every N days, weeks, or months after completion or from a fixed anchor.

- Annual recurring: repeats each year while retaining each completed instance.

- Completion should never erase the historical task occurrence.

## UX and Visual Design

- Overall feeling: warm, calm, photographic, natural, uncluttered.

- Use plant photography as the primary visual content; avoid decorative stock imagery.

- Favor cards, timelines, chips/tags, and large action buttons over dense tables.

- Responsive design must work well on a phone first and desktop second.

- Forms should save drafts/avoid accidental data loss where practical.

- Use readable contrast and do not rely on color alone to communicate task status.

- Destructive actions require confirmation; plants should preferably be archived rather than permanently deleted.

- Common actions should be reachable in one or two taps from a plant profile.

### Suggested visual language

Natural greens and warm neutral surfaces may be used as inspiration, but the design should remain restrained. Plant photographs should supply most of the color. Icons should be simple and universally recognizable.

[Back to Table of Contents](#table-of-contents)

# 4. Property Map, Beds & Spatial Interaction

## Canonical map rules

- The authoritative map is a structured vector/property model. Aerial images and the hand-drawn plan are reference layers only.

- The coordinate grid is a stable reference overlay, not the primary visual map. Garden beds are editable polygons with stable Bed IDs and unique display names.

- Exact mapped points/areas are authoritative for plant, weed, pest, irrigation, and problem locations; bed and grid references are derived from those positions when possible.

- The default map is intentionally clean. Detail is progressively disclosed by zoom, bed selection, filters, or item selection.

- Selection is bidirectional: list/record selection highlights map location(s), and map selection highlights/opens the matching record.

- Current and historical locations are distinct; moving a plant creates location history rather than replacing the old location.

## Property Grid & Garden Bed Mapping

PNW Home YardWise should include a structured property-mapping system designed for a yard containing many separate garden beds. The property should be represented on a configurable grid, and every garden bed should receive a unique identifying name and ID. This location system should become the common spatial reference used throughout the application.

### 1 Property Grid

- The property map should be overlaid with a configurable grid that can be scaled to match the approximate property dimensions.

- Grid cells should use stable coordinates such as columns A, B, C and rows 1, 2, 3, creating references such as A1, B4, or F7.

- The grid should support enough rows and columns to accommodate a large residential property with many garden areas.

- The user should be able to adjust grid density so cells are neither too large nor unnecessarily detailed.

- Grid coordinates must remain stable once assigned so historical plant and maintenance records do not lose their spatial reference.

- The map may begin as an approximate property layout and be refined over time without changing existing bed identifiers.

### 2 Unique Garden Bed Identification

Every garden bed or distinct managed growing area should have both a human-readable name and a unique system identifier.

- Unique Bed ID, such as BED-001, BED-002, or another stable internal identifier.

- User-defined garden name, such as 'Front Entry Bed', 'North Fence Perennial Bed', or 'Blueberry Bed'.

- Optional short code for compact display, such as FEB, NFP, or BB1.

- Primary grid location and, when a bed spans multiple cells, all grid cells occupied by that bed.

- Optional description and notes.

- Bed type, such as perennial, shrub, vegetable, herb, fruit, mixed border, woodland, raised bed, container area, or other.

- Approximate dimensions or area.

- Sun exposure, irrigation information, soil notes, and other bed-level characteristics.

- Photographs of the bed as a whole, including seasonal images.

### 3 Bed Naming Rules

- Garden names should be unique within the property.

- If the user enters a duplicate name, the application should prompt for a distinguishing name rather than silently creating ambiguity.

- System Bed IDs should never change even if the user later renames the garden.

- Renaming a bed should automatically update its display name everywhere while preserving all history and relationships.

- A retired or removed garden bed should be archived rather than deleted so historical records remain understandable.

### 4 Map Objects

The property map should support more than garden beds so the user can understand spatial relationships across the yard.

- House footprint.

- Driveway.

- Patio or deck.

- Walkways and paths.

- Lawn areas.

- Fence lines.

- Garden beds.

- Raised beds.

- Fruit-tree or orchard areas.

- Containers or grouped pots.

- Structures such as sheds, greenhouse, pergola, or trellis.

- Water features.

- Irrigation zones or water sources when useful.

- Other user-defined landscape features.

### 5 Plant Location Within a Garden Bed

Assigning a plant to a garden bed should not be the end of the location model. The app should also allow an approximate position inside that bed.

- Garden bed assignment.

- Grid coordinate or coordinates.

- Optional sub-position such as north edge, center, southwest corner, fence side, path side, or custom note.

- Optional visual point or marker placed inside the mapped garden bed.

- Ability to move a plant to another bed while preserving its previous-location history.

- Date the plant entered or left a location when known.

### 6 Location Integration Across PNW Home YardWise

The garden-bed and grid system should be used consistently throughout the application rather than existing as a separate decorative map.

- Plants link to a specific garden bed and optional grid position.

- Weed sightings/infestations link to one or more beds and grid cells.

- Pest and disease cases link to affected plants and/or garden beds.

- Tasks can apply to a plant, a garden bed, multiple beds, or a grid region.

- Journal entries can be associated with a garden bed.

- Harvest events inherit the plant's garden location while preserving historical context.

- Photos may be tagged with a garden bed or map location.

- Irrigation, soil amendments, mulching, and other area-wide activities can be recorded at the bed level.

### 7 Map Navigation and Search

- Tap a garden bed to open its bed profile.

- Search by garden name, Bed ID, short code, or grid coordinate.

- Select a grid cell to see all beds, plants, problems, and tasks associated with that cell.

- Filter the property map by plants, weeds, problems, tasks, harvests, irrigation, or other layers.

- Highlight all locations requiring attention today or this week.

- Allow zooming and panning on phone, tablet, and laptop.

- Provide a list view as an accessible alternative to interacting directly with the map.

### 8 Garden Bed Profile

- Garden name, Bed ID, short code, and grid location.

- Map outline and approximate dimensions.

- Bed photographs and seasonal views.

- Current plants growing in the bed.

- Historical plants previously grown there.

- Active weeds, pests, and diseases.

- Upcoming and completed tasks.

- Bed-level journal entries.

- Soil, irrigation, light, and amendment notes.

- Bed-level maintenance and treatment history.

- Harvest summary for edible plants in that bed.

### 9 AI-Assisted Mapping

AI may assist with naming, organizing, and populating garden-bed information, but the user remains authoritative. AI-generated bed names, classifications, location suggestions, or descriptions must always be editable and must never overwrite user-defined map information without approval.

- Suggest a concise unique name based on location or dominant plants.

- Suggest bed type based on existing plant inventory.

- Suggest likely sun exposure or maintenance grouping from user-supplied information.

- Detect plants or landscape features from user-provided property photographs when feasible.

- Never move plants, rename beds, or modify grid coordinates automatically after the user has confirmed them.

## Click-to-Place Property Location

The property map should function as an interactive location-entry tool. When adding or editing a plant, weed sighting, pest/disease case, task, or other yard record, the user should be able to click or tap the exact location on the property map rather than relying only on typed location descriptions.

### 1 Core Interaction

- From any location-aware record, provide a prominent 'Select on Map' action.

- Open the property grid/map centered on the property.

- Allow the user to click on a laptop or tap on a phone to place a location marker.

- Automatically determine the garden bed and grid cell associated with the selected point when the point falls within a mapped bed.

- Display the selected bed name, Bed ID, and grid coordinate before saving.

- Allow the user to drag or re-tap to reposition the marker before confirmation.

- Save the point as the record's precise property-map location.

- Retain the point even if the garden bed is later renamed.

### 2 Plant Placement

- When adding a plant, the user may choose a bed from a list or tap its location directly on the map.

- A map selection should populate the garden bed and grid coordinate automatically.

- Plants should display as selectable markers or symbols within the mapped bed.

- Multiple plants may occupy the same grid cell while retaining separate map points.

- Moving or transplanting a plant should create a new current location while preserving prior-location history.

### 3 Weed Placement

- The 'Is This a Weed?' workflow should include a 'Mark Location on Map' step.

- After identifying a weed, the user can tap the exact place where it was found.

- A single weed species may have multiple separate location markers or infestation areas.

- The user should be able to add additional sightings by tapping new locations without creating a duplicate weed species record.

- For larger patches, the interface should support marking an approximate area or multiple points rather than only a single marker.

### 4 Other Yard Problems and Activities

- Pest sightings may be placed on the map.

- Disease or plant-health observations may be linked to a plant and/or exact map point.

- Tasks may optionally reference a point, garden bed, or broader grid area.

- Journal entries may include an optional map location.

- Photos may inherit the current record's mapped location when appropriate.

### 5 Map Selection Feedback

- Highlight the selected grid cell.

- Highlight the garden bed boundary when the point falls inside a bed.

- Show a visible placement marker.

- Display a compact confirmation panel containing garden name, Bed ID, grid coordinate, and optional location note.

- If the selected point is not inside an existing bed, allow the user to save it as an unassigned property location or create/select a nearby bed.

- Make the interaction fully usable with touch on a phone and mouse/trackpad on a laptop.

### 6 Map-Based Identification

The interaction should also work in reverse: the user can click or tap an existing marker on the property map to identify what is located there.

- Tap a plant marker to open a compact identification card with plant name, photo, cultivar, and bed.

- Tap a weed marker to show weed name, status, treatment history, and next control action.

- Tap a problem marker to show active pest/disease information.

- When multiple records are close together, show a small selectable list rather than forcing one result.

- Allow the user to open the full plant, weed, or problem record directly from the map.

## Selected Plant Map Highlighting

Selecting a plant anywhere in PNW Home YardWise should make its mapped location immediately visible on the property map. The map should function as a spatial companion to the plant record, helping the user understand where the plant is currently located and, when relevant, where it has previously been located.

### 1 Current Location Highlight

- When a plant is selected from Plants, Search, Tasks, Journal, Harvests, or another linked view, provide a visible map panel or 'Show on Map' action.

- Opening the map should automatically center and zoom to the selected plant's current location.

- The selected plant's map marker should be visually emphasized so it is immediately distinguishable from nearby plants.

- The containing garden bed should also be highlighted.

- The corresponding grid cell or cells should be highlighted.

- A compact location summary should show garden name, Bed ID, grid coordinate, and optional sub-location note.

- If the plant has multiple current mapped points, all current points should be highlighted together.

### 2 Multiple Locations

Some plant records may represent multiple specimens of the same plant, a spreading plant, or a plant grouping. The application should support more than one active map location when appropriate.

- Highlight all active locations associated with the selected plant record.

- Show the number of mapped locations.

- Allow the user to tap each highlighted point to see its specific bed, grid cell, notes, and specimen/location details.

- Permit one location to be designated as the primary location when useful.

- Do not require duplicate plant-species information solely because the same plant record has multiple mapped placements.

### 3 Historical Locations

- If a plant has been transplanted or moved, preserve its previous map locations.

- Historical locations should be visually distinct from current locations.

- The user should be able to toggle historical locations on or off.

- Each historical location should show the date range during which the plant occupied that location when known.

- Selecting a historical point should allow access to related photos, journal entries, tasks, or health events from that period.

### 4 Map-to-Plant and Plant-to-Map Synchronization

Selection should work bidirectionally. Selecting a plant highlights its map location, while selecting its marker on the property map highlights or opens the corresponding plant record.

- Plant selected → map centers on and highlights the plant.

- Map marker selected → corresponding plant card/profile becomes the active record.

- Selection state should remain synchronized when switching between plant detail and map views.

- When several nearby plants overlap visually, selecting the plant first should still make its exact marker(s) unambiguous.

## Aerial-Based Property Map Setup & Editing

PNW Home YardWise should support creation of the property map from one or more user-supplied aerial photographs or satellite images. The aerial image serves as a reference/base layer for tracing the house, hardscape, garden beds, structures, and other landscape features. The resulting map should be an editable structured property plan rather than merely a photograph with pins.

### 1 Property Source Images

- Allow one or more aerial/property images to be imported during initial property setup.

- Support images from different dates, sources, crops, resolutions, and zoom levels.

- Allow the user to rotate, crop, scale, and position source images so north/orientation and property features align.

- Allow a preferred image to be selected as the primary aerial base layer.

- Retain additional aerial images as reference layers because different images may reveal garden boundaries hidden by trees or shadows in another image.

- Allow source images to be shown or hidden without affecting the structured map data drawn over them.

- Support importing a hand-drawn property/garden plan as an additional reference layer.

### 2 Structured Map Layers

The map should be constructed in layers so the user can turn information on and off depending on the task.

- Aerial / reference imagery.

- Property boundary.

- Coordinate grid.

- House and permanent structures.

- Driveway, deck, patios, paths, and other hardscape.

- Garden bed polygons.

- Lawn and open areas.

- Trees and large shrubs.

- Individual plant markers.

- Weed sightings and infestation areas.

- Pest sightings.

- Diseases / plant-health problems.

- Tasks and areas requiring attention.

- Irrigation zones and water sources.

- User-defined landscape features.

### 3 Trace-a-Garden-Bed Workflow

- Choose 'Add Garden Bed' from the map editor.

- Display the aerial image and coordinate grid.

- Click with a mouse or tap on a touch device around the visible perimeter of the garden bed.

- Connect the points to create an editable polygon matching the actual curved or irregular bed shape.

- Allow polygon points to be dragged later to refine the outline.

- Enter a unique user-facing garden name.

- Automatically assign a permanent Bed ID.

- Optionally enter a short code, bed type, dimensions, soil, sun, irrigation, and notes.

- Save the bed polygon and automatically determine which grid cells it intersects.

### 4 Other Property Features

The same tracing tools should be reusable for permanent landscape features so the map accurately represents the property.

- Polygon tools for the house, deck, patios, lawn, greenhouse, raised beds, and larger areas.

- Line tools for fences, paths, trellises, irrigation lines, and property edges.

- Point markers for individual trees, shrubs, containers, water sources, gates, and other discrete features.

- Feature names and notes where useful.

- Lock completed permanent features to prevent accidental movement while editing plants or beds.

### 5 Grid Overlay

- Display the stable alphanumeric property grid transparently over either the aerial image or clean property plan.

- Allow grid visibility and opacity to be adjusted.

- Grid coordinates remain stable after property setup.

- Garden beds automatically store all grid cells intersected by their polygon.

- Exact plant/weed points retain both map coordinates and their corresponding grid reference.

- The grid remains useful even if aerial imagery is later replaced with a newer image.

### 6 Clean Map and Aerial Views

After the property has been traced, the user should be able to switch between an aerial/reference view and a clean diagrammatic property map. Both views use the same underlying garden beds, markers, and coordinates.

- Aerial View — displays selected aerial imagery beneath map objects.

- Clean Map — hides the photograph and shows only the structured property plan.

- Hybrid View — displays the aerial image with bed outlines, grid, and selected data layers.

- Layer selections should persist according to user preference.

- Selecting a plant, weed, pest, disease, or task should produce the same location highlighting in all map views.

### 7 Image Alignment and Updating

- Newer aerial images may be added later without rebuilding the garden database.

- The user should be able to align a new image to known fixed features such as house corners, deck corners, driveway edges, or greenhouse corners.

- Replacing or realigning an aerial reference must not move established plant, bed, or problem records automatically.

- The user may manually refine mapped features after comparing them with newer imagery.

- Historical aerial images may be retained to document landscape changes over time.

### 8 AI-Assisted Initial Mapping

AI may assist with initial interpretation of aerial images by proposing likely outlines for buildings, paths, garden beds, trees, and other visible features. Because tree canopy, shadows, seasonal growth, and image distortion can obscure boundaries, all AI-generated map geometry must be treated as a suggestion until confirmed by the user.

- Suggest the house and major hardscape outlines.

- Suggest visible garden-bed boundaries.

- Suggest individual trees or major shrubs.

- Compare multiple aerial/reference images to help resolve partially obscured areas.

- Use the hand-drawn plan as supplemental context when available.

- Require user confirmation before proposed geometry becomes authoritative.

- Never overwrite a user-corrected bed boundary or map position automatically.

### 9 Initial Property Setup Workflow

- Create Property.

- Import one or more aerial/reference images.

- Set orientation and align the images.

- Define the approximate property boundary.

- Configure and lock the coordinate grid.

- Trace the house and major permanent features.

- Trace and uniquely name each garden bed.

- Review and correct bed boundaries using additional aerial images or the hand-drawn plan.

- Begin placing existing plants, weeds, and other records by clicking/tapping their locations.

- Save the structured map as the authoritative property-location system.

### 10 Project Source Material

The current PNW Home YardWise project includes multiple aerial views of the property and a hand-drawn garden plan. These materials should be treated as source references for creation of the initial property map. They provide complementary information: close aerial views show garden geometry and hardscape in detail, wider imagery provides property context, and the hand-drawn plan helps interpret garden areas that are partially obscured by mature tree canopy.

## Clean Map Navigation, Bed Drill-Down & Filtering

The property map should remain visually clean at normal viewing levels. Detailed plant, weed, sprinkler, pest, disease, and other infrastructure information should appear progressively as the user zooms in, selects a garden bed, or explicitly enables a category filter. The map should prioritize spatial orientation first and detailed records second.

### 1 Clean Default Property View

- The default property view should show only the information needed to understand the property layout.

- Show major property features, garden-bed outlines/names, and an optional subtle coordinate grid.

- Do not display every plant, sprinkler head, weed sighting, pest, disease, task, and other marker simultaneously by default.

- Use clustering, simplified symbols, or hidden detail at wider zoom levels to prevent visual clutter.

- Labels should appear only when there is adequate space and should not overlap unnecessarily.

- The user should be able to hide the aerial imagery and use the clean structured map as the normal working view.

- Aerial/reference imagery remains available as an optional layer.

### 2 Progressive Detail by Zoom

Map detail should increase progressively as the user zooms in. Zooming should reveal information rather than simply making the same crowded set of markers larger.

- Property level: house, hardscape, major landscape areas, garden-bed boundaries, and garden names.

- Garden level: selected bed boundary, neighboring beds, major trees/shrubs, and category summaries.

- Bed detail level: individual plant locations and enabled category markers.

- Close detail level: individual sprinklers/emitters, weed sightings, pest/disease markers, plant labels, and other fine-grained records when enabled.

- The application should automatically suppress labels and markers that are not useful at the current zoom level.

- Manual category filters always remain available so the user can intentionally display a detail layer.

### 3 Selecting a Garden Bed

Clicking or tapping a garden bed should place the map into Bed Focus mode. The selected bed becomes the primary context while unrelated property detail is visually de-emphasized.

- Highlight the selected garden-bed boundary.

- Center and zoom the map to fit the selected bed.

- Show the garden name, Bed ID, grid coordinates, and basic bed information.

- Open a Bed Contents panel/list without obscuring the useful map area.

- De-emphasize unrelated beds and markers while preserving enough surrounding context for orientation.

- Provide a clear Back to Property action.

### 4 Bed Category Filters

Within Bed Focus mode, the user should be able to choose which categories are displayed. Filters should affect both the map and the associated bed-content list.

- Plants.

- Trees / large shrubs.

- Annual / seasonal plantings.

- Sprinklers / irrigation.

- Weeds.

- Pests.

- Diseases / plant-health cases.

- Tasks.

- Harvest-related records when useful.

- Garden infrastructure / features.

- All categories or a user-selected combination.

### 5 Bed Contents List

Every garden bed should provide a list-based view of its contents. This is important both for usability and as an alternative to finding a small marker visually on the map.

- List all current plants in the bed by default.

- Show plant name, cultivar when relevant, small thumbnail, and optional brief status.

- Allow sorting alphabetically, by plant type, map position, recently updated, or other useful criteria.

- Allow searching within the selected bed.

- Apply the same category filters to the list when the user switches from Plants to Trees, Sprinklers, Weeds, or other categories.

- Show counts by category, such as Plants 24, Trees 3, Sprinklers 8, Weeds 2.

- Historical/archived contents should be available through a separate toggle rather than cluttering the current list.

### 6 List Selection → Map Location

Selecting an item from the Bed Contents list should immediately identify its exact position within the selected garden bed.

- Selecting a plant in the list highlights its marker on the bed map.

- Automatically pan/zoom as needed so the selected marker is clearly visible.

- Keep the selected garden-bed boundary visible.

- If a plant has multiple locations within the bed, highlight all current locations.

- If the selected item is a sprinkler, weed, pest, disease case, or other mapped record, highlight its corresponding point(s) or area.

- Use a persistent selection state so the highlight remains until another item is selected or the selection is cleared.

### 7 Map Selection → List Item

The relationship should work in both directions. Selecting an object on the bed map should locate and highlight the corresponding entry in the Bed Contents list.

- Tap/click a plant marker to select the corresponding plant in the list.

- Scroll the list to the selected item when necessary.

- Show a compact identification card containing the name, thumbnail, and key status information.

- When markers overlap, provide a short selectable list of the records at that location.

- The user should never need to guess which list record corresponds to a map marker.

### 8 Link to Full Plant Information

- Every plant in the Bed Contents list must provide a direct link/action to open its full Plant Profile.

- The compact map identification card should also provide an Open Plant action.

- Opening the Plant Profile should preserve the user's bed/map context so Back returns to the same bed, zoom level, filters, and selected item.

- The Plant Profile should retain its existing Show on Map action, returning to the exact highlighted location.

- The same pattern should apply to weeds, irrigation components, pests, and disease cases: list/map selection leads directly to the appropriate full record.

### 9 Phone and Laptop Behavior

- Laptop: map and Bed Contents panel may appear side-by-side when space permits.

- Phone: prioritize the map with a collapsible or bottom-sheet-style contents panel that can be expanded when needed.

- The contents panel must not permanently cover most of the map on a phone.

- Filters should use compact, touch-friendly controls and remain easy to change.

- Zoom, pan, marker selection, bed selection, and list selection must all work by touch without requiring hover.

### 10 Map Performance and Clutter Rules

- Do not render unnecessary fine-detail markers at wide property zoom levels.

- Load/render detailed bed records when the selected bed or zoom level requires them.

- Prefer one clear selected highlight over multiple competing visual emphasis states.

- Avoid permanent text labels for every plant; show names through selection, sufficient zoom, or an enabled label option.

- Keep category symbols visually distinct but restrained.

- The clean-map principle takes precedence over showing all available information at once.

[Back to Table of Contents](#table-of-contents)

# 5. Plant Inventory, Profiles, Photos & Journal

## Journal Plant Wish List

The Journal should include a Plant Wish List for plants the user is considering adding to the yard. Wish-list plants are not part of the active plant inventory until the user chooses to add or plant them. This allows PNW Home YardWise to serve as a planning notebook as well as a record of what is already growing on the property.

### 1 Wish List Plant Record

- Common name and botanical name.

- Cultivar or variety when known.

- Photo or reference image.

- Plant type: annual, biennial, perennial, bulb/corm/tuber, shrub, tree, vine, herb, vegetable, fruit, groundcover, or other.

- Edible, ornamental, or both.

- Recommended hardiness zone or zone range.

- Best planting time or planting window for the user’s climate.

- Sun requirements.

- Water requirements.

- Expected mature height and width.

- Bloom period and flower color when relevant.

- Harvest period when edible.

- Time to harvest or years to bearing when useful.

- Pollination requirements or recommended pollinator partners when relevant.

- Soil preferences and drainage needs.

- Pet toxicity or other important safety notes when relevant.

- Reason the user wants the plant or notes about where it might fit in the yard.

- Potential yard area or planting location.

- Source, nursery, seed company, or purchase link/reference when the user wants to save it.

- Priority or interest status such as Someday, Considering, Want Soon, or Purchased.

### 2 Wish List Views and Filters

- Browse wish-list plants as photo cards or a compact list.

- Filter by annual/perennial, plant type, edible/ornamental, hardiness zone, sun requirement, mature size, bloom season, harvest season, and priority.

- Sort by name, date added, planting season, bloom period, harvest period, or priority.

- Show a seasonal planning view such as “Plants I can plant this fall” or “Wish-list plants that bloom in spring.”

- Allow tags such as pollinator plant, shade garden, fragrant, native, deer resistant, fruit, cut flower, or screening plant.

### 3 From Wish List to Yard

- Add to Yard - convert the wish-list entry into a normal plant inventory record while retaining the original research information.

- Mark Purchased - record purchase date, source, quantity, and optional cost without yet adding the plant to the yard.

- Create Planting Task - schedule planting for the recommended or selected planting window.

- Assign Planned Location - associate the plant with a yard area before it is planted.

- Remove from Wish List - archive plants the user no longer wants without losing historical notes if desired.

### 4 Journal Integration

Wish-list entries should be accessible from the Journal because they represent garden ideas and future plans. A journal entry may link to one or more wish-list plants, allowing the user to save observations such as seeing a plant in another garden, comparing cultivars, recording nursery availability, or noting a possible location in the yard.

### 5 AI-Assisted Wish List Research

When AI and reliable horticultural reference data are available, PNW Home YardWise may help populate basic wish-list information from a plant name or photograph. The user should be able to review and edit the information before saving it. Regional recommendations should use the user’s growing region rather than generic national guidance.

- “Would this plant grow well in my yard?”

- “When should I plant this?”

- “How large will this get?”

- “When will it bloom?”

- “Is this hardy in my zone?”

- “When could I expect to harvest it?”

- “Show me wish-list plants that would fit a 4-foot-wide bed.”

- “Which plants on my wish list would give me flowers in August?”

## Plant Photo Library & Seasonal Visual Record

Every plant record should support a rich library of multiple photographs rather than a single profile image. Photos should document identifying features, growth, flowering, fruiting, seasonal appearance, health changes, and the plant's development over multiple years.

### 1 Multiple Photos per Plant

- Unlimited or practically high number of photos per plant record.

- One user-selected primary/profile photo, with the ability to change it at any time.

- Photo date captured automatically when available and editable by the user.

- Optional caption and notes for every photo.

- Optional year and season classification.

- Ability to browse all photos chronologically or by photo category.

- Photos remain linked to the plant even when they are also used in journal, harvest, pest, disease, or treatment records.

### 2 Photo Categories

Each photograph may be assigned one or more categories so the user can quickly compare specific plant features.

- Whole plant / overall form.

- Leaves / foliage.

- Flowers / blossoms.

- Fruit.

- Seeds / seed heads.

- Bark / trunk.

- Branches / stems / canes / vines.

- Buds / new growth.

- Roots / crown when relevant.

- Harvest.

- Pest or disease symptom.

- Damage / stress.

- Pruning or maintenance.

- Before treatment / after treatment.

- Other.

### 3 Seasonal Photo Record

Plant profiles should provide a seasonal visual record showing what the actual plant looks like throughout the year. Photos may be categorized as Winter, Spring, Summer, or Fall and should retain the year so changes can be compared across seasons and across years.

- Winter appearance, including dormant form when applicable.

- Spring emergence, budding, flowering, and early foliage.

- Summer foliage, mature form, flowers, and developing fruit.

- Fall fruit, foliage color, seed heads, dieback, or dormancy transition.

- Allow multiple photos within the same season rather than limiting each season to one image.

- Show missing seasonal views so the user can intentionally photograph the plant later.

### 4 Plant Photo Views

- Gallery View — all photographs for the plant.

- Timeline View — photographs arranged chronologically.

- Season View — Winter, Spring, Summer, and Fall groups.

- Feature View — leaves, flowers, fruit, bark, whole plant, and other categories.

- Year View — all photographs from a selected growing year.

- Then & Now — select two photographs for side-by-side comparison.

- Season-to-Season — compare the same plant across seasons.

- Year-to-Year — compare the same season or feature across different years.

### 5 Photo Capture Workflow

- From a plant profile, tap Add Photo.

- Take a new photo from the phone or choose an existing image.

- Default the date to the image date or current date.

- Suggest the season from the date while allowing the user to override it.

- Select or confirm one or more photo categories such as Leaf, Flower, Fruit, or Whole Plant.

- Optionally add a caption or observation.

- Save the photo to the plant's visual history.

### 6 AI-Assisted Photo Classification

AI may assist by suggesting what a photograph depicts, such as leaf, flower, fruit, bark, whole plant, disease symptom, or seasonal appearance. AI-generated classifications and captions must remain editable. User changes take precedence and must not be overwritten automatically by later AI enrichment.

- Suggest photo category or categories.

- Suggest season when metadata is missing.

- Recognize flowers, fruit, leaves, bark, buds, and other useful identifying features.

- Associate disease/pest symptom photos with an active Yard Problems case when the user approves.

- Suggest whether a photograph may be useful as the plant's primary identification photo.

- Never delete, relabel, or move a user-classified photograph without user approval.

### 7 Photo Integration with Harvests and Plant Health

A single photograph may participate in several parts of the plant record without requiring duplicate uploads. For example, a fruit photograph can appear in the plant gallery and a Harvest Event, while a diseased leaf photograph can appear in the plant gallery and the corresponding Plant Health Case.

[Back to Table of Contents](#table-of-contents)

# 6. Annuals, Vegetables, Seedlings & Harvests

## Annuals, Vegetable Garden Planning & Planting Notifications

PNW Home YardWise should manage annual vegetables, herbs, and flowers as seasonal plantings while preserving a permanent variety record. It should also provide a dedicated Vegetable Garden Planner for each upcoming growing year and generate timely planting reminders based on the property's climate profile, including hardiness zone, expected frost dates, crop requirements, and the user's chosen growing method.

### 1 Permanent Variety Record vs. Seasonal Planting

Annual crops should use a two-level model. A permanent variety record stores reusable information about the crop or cultivar, while each year's planting is a separate seasonal record.

- Permanent variety record: common name, botanical name, cultivar, annual/biennial/perennial status, days to maturity, seed-starting needs, transplanting guidance, spacing, mature size, sun/water needs, bloom period, harvest window, pollination information, photos, and accumulated notes.

- Seasonal planting record: growing year, garden bed and exact map location, planned quantity, actual quantity, seed source, seed-start date, sowing date, transplant date, first bloom, first harvest, last harvest, treatments, photos, harvests, and end-of-season outcome.

- The permanent variety record remains available for reuse in future years even after a seasonal planting is closed.

- Seasonal planting history must allow comparison of performance by year and garden location.

### 2 Vegetable Garden Planner

The application should provide a planning workspace for the upcoming growing season before crops are actually planted. The planner should use the same mapped garden beds and property grid as the rest of PNW Home YardWise.

- Create a garden plan for a selected growing year.

- Choose one or more vegetable/annual garden beds from the property map.

- Place planned crops directly into a bed or exact map location.

- Select crops from existing variety records or the Plant Wish List, or add a new crop.

- Record planned quantity, spacing, row/area, planting method, and target planting window.

- Support spring, summer, fall, overwintering, and succession plantings in the same bed.

- Show planned crops and active crops as visually distinct map layers.

- Allow planned plantings to be moved between beds before they are planted.

- Allow a planned crop to be converted to an active seasonal planting with a single 'Mark as Planted' action.

- Preserve previous yearly garden plans for comparison.

### 3 Bed Planning and Crop Rotation

- Display what was grown in each vegetable bed in prior years.

- Support crop-family information such as nightshades, brassicas, legumes, cucurbits, alliums, roots, and other groups.

- Warn when a planned crop repeats a crop family in the same bed sooner than the user's chosen rotation interval.

- Show prior pest and disease problems associated with a bed or crop family.

- Allow the user to override rotation suggestions when desired.

- Support mixed plantings and interplanting rather than assuming one crop per bed.

- Support cover crops and fallow periods.

### 4 Succession and Multiple Plantings

- Allow several planned sowing dates for the same crop.

- Support recurring succession intervals such as sow lettuce every 14 days.

- Display overlapping planting and harvest windows.

- Generate individual reminders for each succession planting.

- Allow the user to skip, postpone, or cancel a planned succession without altering the permanent crop record.

### 5 Property Climate Profile

Planting recommendations should be calculated from a property-level climate profile rather than from hardiness zone alone. Hardiness zone is useful for perennial cold tolerance, while annual planting dates depend heavily on local frost timing and crop temperature requirements.

- USDA hardiness zone or equivalent regional zone.

- Expected average last spring frost date.

- Expected average first fall frost date.

- Approximate frost-free growing season.

- User-adjusted local microclimate notes.

- Optional bed-level microclimate differences such as warmer south-facing beds or frost pockets.

- User ability to override any automatically supplied climate value.

- Optional use of current and forecast weather to refine timing while retaining the climate-based baseline.

### 6 Planting Timeline Engine

For each planned annual crop, PNW Home YardWise should calculate a sequence of relevant milestones rather than providing only one generic planting date.

- Order or purchase seed.

- Start seed indoors.

- Pot up seedlings when applicable.

- Begin hardening off.

- Transplant outdoors.

- Direct sow outdoors.

- Purchase nursery starts if the user plans to buy starts instead of growing from seed.

- Plant purchased starts outdoors.

- Install supports or trellising when useful.

- Expected bloom or fruit-set period.

- Expected first harvest and harvest window.

- Potential fall planting or second-crop window.

- End-of-season or frost-protection milestone when relevant.

### 7 Growing Method

The user should be able to choose how they intend to grow each crop because notification timing differs substantially by method.

- Start from seed indoors.

- Purchase nursery starts/transplants.

- Use saved seed.

- Overwinter an existing plant when applicable.

- Undecided - show the main options and their corresponding timelines.

### 8 Push Notifications and In-App Alerts

PNW Home YardWise should support opt-in push notifications on compatible phones and computers, plus an in-app notification center. Because the application is privately hosted, remote browser push should use standards-based secure web/PWA notification mechanisms and require user permission. Notifications should remain useful even when the user is not actively viewing the application.

- “If starting tomatoes from seed, plant them indoors now.”

- “Time to begin hardening off your tomato seedlings.”

- “Conditions are approaching your tomato transplant window.”

- “Time to purchase tomato starts for outdoor planting.”

- “Direct-sow peas this week.”

- “Your second lettuce succession is due to be sown.”

- “First fall carrot planting window begins soon.”

### 9 Notification Controls

- Notifications must be opt-in.

- Allow push notifications, in-app notifications, or both.

- Allow the user to choose reminder lead time, such as same day, 3 days, 1 week, or custom.

- Allow crop-specific notification preferences.

- Allow a notification to be completed, snoozed, rescheduled, or dismissed.

- Allow the user to mark a milestone Not Applicable.

- Avoid duplicate alerts when the corresponding task or planting milestone has already been completed.

- Provide a quiet-hours setting for push notifications.

- Allow a yearly review of notification preferences before the new growing season.

### 10 Smart Notification Logic

Notifications should be contextual. The system should know whether the user plans to start seed, direct sow, or purchase starts and should not send conflicting instructions.

- If the user selected Start Indoors, generate seed-start, pot-up/hardening, and transplant milestones.

- If the user selected Purchase Starts, omit indoor seed-start reminders and instead notify when to purchase and plant starts.

- If the user selected Direct Sow, generate outdoor sowing milestones appropriate to the crop.

- If no growing method has been chosen, notify early enough to let the user choose between seed-starting and purchasing starts.

- Recalculate future milestones when the user changes the planned planting date or method.

- Allow weather-based caution such as delaying transplanting when a frost risk is expected, without automatically overriding the user's plan.

- User-entered dates and overrides remain authoritative.

### 11 Annual Photo Milestones

Annual crops should use growth-stage photo prompts rather than requiring the four-season photo set used for many permanent plants.

- Seedling.

- Young plant or transplant.

- Established vegetative growth.

- Bloom/flowering when applicable.

- Developing fruit or edible portion.

- Ripe/harvest-ready stage.

- Representative harvest.

- End-of-season condition when useful.

- AI may suggest which milestones apply to a crop; the user can override or mark any milestone Not Applicable.

### 12 Annual Harvest Integration

- Every harvest event links to the specific seasonal planting, not only the permanent crop variety.

- Quick Harvest should allow rapid entry of date, quantity/unit, quality, and optional photo/note.

- Repeatedly harvested crops such as tomatoes, beans, zucchini, cucumbers, herbs, and berries should support many harvest events.

- The application should summarize total yield, first harvest, last harvest, peak harvest period, and quality for that season.

- Year-to-year comparisons should show differences among varieties, beds, planting dates, and growing methods.

### 13 End-of-Season Review

- Prompt the user to close a seasonal planting after the crop is finished.

- Summarize actual planting dates, harvest totals, pests/diseases, treatments, and photos.

- Allow a simple Grow Again rating and notes for next year.

- Record whether seed was saved.

- Optionally add the crop automatically to the next year's planning shortlist.

- Retain the closed seasonal planting on historical property maps and bed histories.

### 14 AI Planning Assistance

AI may help populate crop requirements, suggest planting windows, organize a yearly vegetable plan, and identify scheduling conflicts. AI-generated dates should be traceable to the property's climate assumptions and remain fully editable.

- Fill missing crop details such as days to maturity, spacing, mature size, bloom/harvest timing, and common planting methods.

- Suggest seed-start and transplant windows from the property's climate profile.

- Suggest succession schedules.

- Suggest bed placement based on sun, space, irrigation, crop history, and rotation considerations.

- Identify likely overcrowding or timing conflicts in a planned bed.

- Offer alternatives when a crop's desired timing is poorly matched to the local growing season.

- Never overwrite user-selected planting dates, crop locations, or growing methods without approval.

## Seedling Identification & Early Growth Guidance

PNW Home YardWise should help the user recognize seedlings from plants started indoors or direct-sown outdoors so desirable seedlings are not accidentally removed as weeds. Seedling identification should be integrated with annual crop planning, seasonal planting records, the photo library, and the 'Is This a Weed?' workflow.

### 1 Seedling Reference Information

- Expected appearance at emergence.

- Cotyledon (seed leaf) shape and appearance.

- First true leaf shape and texture.

- Typical early stem color, thickness, and growth habit.

- Typical seedling color and distinguishing markings.

- Approximate size at key early growth stages.

- Expected emergence time after sowing under normal conditions.

- Common look-alike weeds or volunteer plants when known.

- Multiple reference photos showing the seedling at different early stages.

- Indoor-grown and direct-sown seedling examples when appearance may differ.

### 2 Seedling Photo Milestones

For crops started from seed, the photo checklist should include early-growth milestones before the normal annual crop photo sequence.

- Just emerged.

- Cotyledons fully open.

- First true leaves.

- Several true leaves / established seedling.

- Ready to thin when direct-sown.

- Ready to pot up when started indoors.

- Ready to begin hardening off.

- Ready for transplant.

- The user may mark any milestone Not Applicable.

### 3 Direct-Sown Crop Identification

- When a direct-sown crop is recorded, PNW Home YardWise should remember the exact bed, map area, row, or point where seed was planted.

- The map should visually mark the expected emergence area.

- During the expected emergence window, the app should offer a 'What Should Be Coming Up Here?' view.

- That view should show reference photos of the expected crop seedlings together with the sowing date and expected emergence window.

- If multiple crops were direct-sown in the same bed, each planned row or area should display its own expected seedling identification.

- The user should be able to photograph an emerging plant directly from that bed and compare it with the expected crop.

### 4 Indoor Seed-Starting Identification

- Seed-starting records should include tray/container identification and variety.

- The app should show expected seedling appearance before or around the predicted germination date.

- The user can add actual photos as seedlings emerge.

- AI may compare the user's seedling photo with the expected crop and flag possible mismatches.

- Seedling photos remain attached to that seasonal planting after transplant so the complete growth history is preserved.

### 5 Integration with “Is This a Weed?”

When 'Is This a Weed?' is used inside or near a recently sown garden bed, PNW Home YardWise should first consider whether the photographed plant could be one of the expected seedlings in that location.

- Check active and planned seasonal plantings associated with the selected map location.

- Compare the photographed plant with expected crop seedling characteristics.

- Return results such as 'Likely tomato seedling', 'Possible carrot seedling', 'Likely weed', or 'Uncertain'.

- Show side-by-side reference images or identifying features when possible.

- Do not recommend pulling an uncertain seedling when it reasonably matches a recently sown crop.

- Allow the user to mark the plant as Keep / Expected Seedling, Weed, Volunteer Plant, or Unsure.

### 6 Seedling Alerts

- Notify the user when a direct-sown crop is entering its expected emergence window.

- Example: 'Your carrot seedlings should begin appearing in Bed BED-021 this week. See what they should look like.'

- Example: 'Bean seedlings may be emerging now. Avoid weeding this row until you confirm them.'

- Prompt for an emergence photo when useful.

- Allow the user to snooze or dismiss seedling-identification reminders.

- Stop emergence reminders once the user confirms seedlings are established.

### 7 AI-Assisted Seedling Recognition

AI may assist with seedling recognition by combining the photograph with contextual information such as what was planted, where it was planted, sowing date, expected germination timing, and known crop characteristics. Context should be used to improve identification rather than relying on image recognition alone.

- Suggest likely crop identity.

- Compare cotyledon and true-leaf features with expected seedlings.

- Identify common weed look-alikes.

- Estimate whether the seedling's developmental stage is consistent with the sowing date.

- Allow the user to correct any AI classification.

- A user-confirmed seedling identity must not be overwritten automatically by later AI analysis.

## Harvest Tracking for Edible and Fruit-Producing Plants

Every edible or fruit-producing plant should support detailed harvest records. Harvest data should be stored as individual events linked to the plant so the user can see not only when a crop is normally harvested, but what was actually harvested from that specific plant each season.

### 1 Harvest Event Data

- Plant and cultivar/variety.

- Harvest date and optional start/end time.

- Quantity harvested.

- Unit selected by the user, such as individual fruit, pounds, ounces, baskets, cups, bunches, handfuls, or custom unit.

- Optional count plus weight when both are useful.

- Ripeness or maturity stage.

- Quality rating, such as poor, fair, good, excellent, or a user-defined score.

- Flavor/texture notes.

- Size notes, including unusually large or small fruit.

- Condition of harvest, including damage, splitting, pest injury, disease, sunscald, or other defects.

- Photo(s) of the harvest.

- Intended use, such as fresh eating, preserving, freezing, drying, baking, gifting, or other.

- Optional destination or storage notes.

- Weather or environmental notes when the user wants to record them.

- General harvest notes.

### 2 Harvest Season Summary

- Total quantity harvested from each plant for the season.

- Number of separate harvest events.

- First and last harvest dates.

- Peak harvest period.

- Average or typical quality across the season.

- Comparison with prior years.

- Notes about yield changes, alternate bearing, late frost effects, pests, disease, pruning, irrigation, or other factors that may have affected production.

- Ability to compare cultivars or multiple plants of the same crop.

### 3 Quick Harvest Workflow

- Open an edible plant profile and tap “Record Harvest.”

- Date defaults to today.

- Enter quantity and unit; all other fields are optional.

- Optionally add quality, notes, use, and photos.

- Save the harvest event to the plant history.

- Immediately update that plant’s seasonal harvest total.

### 4 Harvest History and Analytics

- Display harvest events chronologically on the plant profile.

- Show annual totals and first/last harvest dates by year.

- Show yield trends across multiple years when sufficient data exists.

- Allow filtering by plant, crop type, cultivar, year, or yard area.

- Allow the user to view all edible harvests for a selected day, month, or season.

- Preserve harvest history even if the plant is later removed or archived.

- Permit manual correction of any harvest entry.

### 5 AI-Assisted Harvest Insights

AI may use the user’s actual harvest history together with plant records and garden observations to summarize patterns and suggest likely harvest windows. AI-derived insights must remain advisory and must never alter recorded harvest quantities or dates.

- Estimate an upcoming harvest window from prior-year records and current season information.

- Identify whether production is trending up or down over several seasons.

- Highlight unusually early or late harvests.

- Summarize which cultivars produced the most or had the best recorded quality.

- Identify possible relationships between recorded maintenance, weather stress, disease, and yield for the user to consider.

- Answer natural-language questions such as “How many pounds of pears did I harvest last year?” or “Which blueberry variety produced the most?”

[Back to Table of Contents](#table-of-contents)

# 7. Yard Problems: Weeds, Pests & Plant Health

## Canonical Yard Problems model

- Weeds, pests, and diseases/plant-health cases share a common Observation/Problem framework for location, photos, severity, status, treatments, tasks, and follow-up, while retaining category-specific fields.

- “Is This a Weed?” and “What Is This Pest?” are global capture workflows, not separate data stores; accepted results create/link canonical Weed or Pest records and sightings.

- AI identification is advisory. Destructive treatment must never be initiated solely from an uncertain AI identification.

- Control guidance follows integrated pest/weed/plant-health management principles and records timing, treatment, result, and recurrence.

## Weed Identification & Management

PNW Home YardWise should treat weeds as a dedicated management category rather than mixing them into the normal ornamental and edible plant inventory. The feature should help the user identify weeds, document where they occur, understand the best timing and method for control, record treatments, and schedule follow-up.

### 1 Weed Species Records

- Identification photos and distinguishing characteristics.

- Annual, biennial, or perennial growth habit.

- Native, introduced, invasive, or legally designated noxious status when applicable.

- How the weed spreads: seed, runners, rhizomes, roots, bulbs, fragments, or other mechanisms.

- Typical emergence, flowering, and seed-production periods.

- Best control window, including the time of year or growth stage when control is most effective.

- Recommended control methods: hand pulling, digging, cutting/mowing, smothering/mulching, or other appropriate methods.

- Chemical-control information when appropriate, presented as an optional method rather than the default.

- Important removal details, such as whether the crown, taproot, rhizomes, or other underground structures must be removed.

- Whether plant material can safely be composted or should be disposed of another way.

- A prominent 'Do not let it go to seed' period when relevant.

- Expected persistence or seed-bank considerations when useful.

- Pet/child and desirable-plant precautions.

- Notes and reference information.

### 2 Weed Sightings / Infestations

A weed species may occur in several places. The app should therefore separate the species record from individual sightings or infestations.

- Linked weed species.

- Yard area and specific location note.

- Date first observed and date last observed.

- Photos of the infestation.

- Approximate severity or extent: isolated, small patch, moderate patch, widespread.

- Current status: active, treated, monitoring, controlled, or resolved.

- Treatment history and notes.

- Next follow-up date.

### 3 Weed Control Calendar

The Home and Tasks areas should surface weed work according to the most useful control window, not simply the date the weed was identified. Examples include removing annual weeds before seed set, treating perennial weeds during an effective growth stage, and scheduling repeated follow-up for species that regrow.

- Show weeds that should be controlled now.

- Flag weeds approaching flowering or seed production.

- Show treated infestations that are due for reinspection.

- Generate recurring monitoring tasks for persistent perennial or invasive weeds.

- Allow control tasks to apply to a specific infestation, all occurrences of a weed species, or an entire yard area.

- Preserve every treatment and follow-up as historical activity.

### 4 Weed Control Activity

- Pulled/dug.

- Cut or mowed.

- Smothered/mulched.

- Treated.

- Seed heads removed.

- Area replanted or covered after removal.

- Inspected/no regrowth found.

- Regrowth found.

### 5 AI Weed Identification

A future photo-identification workflow may suggest that an unknown plant is a weed. The app should display the likely identification and confidence, but require the user to confirm it before creating a weed record or control plan. Once confirmed, the app may suggest appropriate control timing and follow-up tasks for user approval.

- Natural-language question: "Which weeds should I deal with this weekend?"

- Natural-language question: "Which weeds are about to go to seed?"

- Natural-language question: "Show me weeds I treated but have not rechecked."

- Natural-language question: "What should I pull now versus treat later in the season?"

### 6 Yard Problems Framework

The architecture should leave room for a broader Yard Problems area containing three related categories: Weeds, Pests, and Diseases. PNW Home YardWise may implement Weeds first, while using a structure that can later support pest sightings, disease observations, treatments, photographs, and follow-up.

## Global Action: “Is This a Weed?”

“Is This a Weed?” is a persistent global action available from anywhere in PNW Home YardWise, with especially prominent access on the phone interface. Its purpose is to let the user photograph an unfamiliar plant in the yard and immediately determine what it is, whether it is likely to be undesirable in that location, and what action—if any—should be taken.

### 1 User Flow

- Tap “Is This a Weed?” from the global action menu.

- Take a new photograph or select an existing photograph.

- Optionally add the yard area/location and a brief note.

- Analyze the image and return the most likely plant identification, reasonable alternatives when uncertain, and an identification confidence level.

- Explain whether the plant is commonly considered a weed, invasive plant, noxious weed, volunteer desirable plant, or ordinary garden plant.

- Present the recommended action and best timing when control is appropriate.

- Let the user choose what to do with the result.

### 2 Result Screen

- Likely common and botanical name.

- Identification confidence and alternative possibilities when relevant.

- Clear answer to “Is this a weed?” with context: weed status can depend on location, user intent, and local invasive/noxious designation.

- Key visual characteristics supporting the identification.

- How the plant spreads.

- Whether it is invasive or legally designated noxious in the user's region when reliable information is available.

- Recommended control method when control is appropriate.

- Best time or growth stage for control.

- Urgency, including a prominent warning when the plant should be removed before flowering or seed production.

- Important disposal, pet, child, pollinator, edible-garden, or desirable-plant precautions when applicable.

### 3 Result Actions

- Add to Weeds — create or link the weed species record and create a sighting/infestation at the current yard location.

- Add as Plant — add the identified plant to the normal plant inventory when it is desirable or intentionally retained.

- Create Control Task — schedule the recommended control action at the appropriate time.

- Record Treatment — document control that has already been performed.

- Monitor — create a follow-up reminder without treating the plant yet.

- Not Sure — save the observation and photographs for later identification or expert review.

- Dismiss — do not add the identification to the garden record.

### 4 Identification Safety and Confidence

The app must not treat image recognition as infallible. A low-confidence identification should remain an observation rather than automatically becoming a weed record. When visually similar species have substantially different control implications, the app should show the alternatives and recommend additional photographs or expert confirmation before destructive treatment.

### 5 Context-Aware Weed Status

“Weed” is not purely a botanical classification. PNW Home YardWise should distinguish between an identified species and the user's decision about whether that plant is wanted in a particular location. A volunteer herb, native wildflower, seedling tree, groundcover, or spreading ornamental may be desirable in one area and treated as a weed in another. The result should therefore explain both the plant's identity and its regional invasive/noxious status, then allow the user to decide whether to keep, monitor, relocate, or control it.

## Pest Identification, Monitoring & Control

Pest Control is a full component of the PNW Home YardWise Yard Problems system alongside Weeds and Diseases/Plant Health. The feature should help the user identify pests and beneficial organisms, document where they occur and what plants they affect, assess damage and severity, determine whether control is warranted, choose appropriate control methods and timing, and track results over time.

### 1 Pest Records

- Common and scientific name when known.

- Pest category such as mite, aphid, slug/snail, scale, thrips, caterpillar, beetle, borer, leaf miner, whitefly, fungus gnat, rodent, or custom category.

- Identification photographs and distinguishing characteristics.

- Common look-alikes.

- Typical host plants.

- Damage and symptoms caused.

- Life cycle and overwintering information when relevant.

- Season or conditions when the pest is most active.

- How the pest spreads or moves through the yard.

- Monitoring methods and signs that intervention is warranted.

- Best time or life stage for control.

- Prevention and cultural-control information.

- Mechanical/physical, biological, and chemical control options as appropriate.

### 2 Pest Sightings / Infestations

- Affected plant or plants.

- Garden bed, grid cell, and exact click/tap map location.

- Date first observed and subsequent observation dates.

- Photographs of the pest and/or damage.

- Severity or approximate population level.

- Affected plant parts.

- Observed damage.

- Current status: monitoring, active, treating, improving, controlled, or resolved.

- Treatment and follow-up history.

### 3 Integrated Pest Management (IPM)

PNW Home YardWise should use an integrated pest management approach rather than assuming every pest sighting requires treatment. The app should help determine whether intervention is necessary and favor the least disruptive effective approach.

- Monitor and correctly identify the organism first.

- Assess damage, population, plant health, and whether intervention is actually necessary.

- Use cultural prevention and environmental correction where appropriate.

- Use physical or mechanical controls when practical.

- Consider biological controls and preservation of natural predators.

- Use chemical controls when appropriate, with product-label and safety reminders.

- Schedule follow-up monitoring to determine whether the intervention worked.

### 4 Global Action: “What Is This Pest?”

A persistent global action should allow the user to photograph an insect, mite, slug, snail, damage pattern, or other suspected pest directly from a phone.

- Take or select a photograph.

- Optionally select the affected plant and/or tap the location on the property map.

- AI suggests the most likely identification, confidence, and reasonable look-alikes.

- The result explains whether the organism is harmful, beneficial, neutral, or uncertain.

- If harmful, show typical damage, whether treatment is warranted, control options, and best timing.

- User actions: Add Pest Sighting, Create Treatment Task, Record Treatment, Monitor, Save for Later Identification, or Dismiss.

- AI identification remains a suggestion until accepted by the user.

### 5 Beneficial Organisms

The pest-identification system must recognize that many organisms found in the garden are beneficial or harmless. PNW Home YardWise should avoid recommending unnecessary control of pollinators, predators, and other useful organisms.

- Lady beetles and larvae.

- Lacewings and larvae.

- Predatory mites.

- Predatory beetles and true bugs.

- Spiders.

- Pollinators such as bees and butterflies.

- Parasitoid wasps and other beneficial insects.

- Other locally beneficial or neutral organisms.

### 6 Treatment Records

- Treatment date.

- Target pest and affected plant(s)/area.

- Control method.

- Product used when applicable.

- Treatment notes.

- Weather/environmental notes when useful.

- Follow-up date.

- Observed effectiveness.

- Impact on plant health.

- Whether additional treatment is needed.

### 7 Pest Map Integration

- Every pest sighting may be assigned by tapping/clicking its exact location on the property map.

- Selecting a pest species should highlight all current known locations on the property map.

- Selecting an affected plant should allow its associated pest sightings to be displayed.

- Selecting a garden bed should show active pest issues in that bed.

- Historical pest locations may be toggled on to identify recurring problem areas.

- Map layers should allow pests to be shown independently from plants, weeds, and diseases.

### 8 Pest Calendar and Alerts

- Show pests that should be monitored during the current season.

- Surface follow-up inspections after treatment.

- Identify recurring seasonal pest patterns from prior-year records.

- Show treatment windows when timing is important to effectiveness.

- Allow recurring monitoring tasks for plants or beds with repeated pest problems.

### 9 AI Enrichment and User Authority

AI may populate missing pest information, suggest likely identification, host plants, lifecycle, control timing, and treatment options. All AI-generated entries must be visibly editable. User-entered or user-corrected information is authoritative and must not be automatically overwritten by later AI enrichment.

### 10 Yard Problems Structure

The finished Yard Problems area should present three primary categories: Weeds, Pests, and Diseases & Plant Health. All three share location mapping, photographs, observations, treatments, tasks, follow-up, history, AI assistance, and user override behavior while retaining category-specific information.

## Plant Disease Diagnosis & Treatment

PNW Home YardWise should include plant disease and health-problem management as a core Yard Problems capability. The feature should help the user document symptoms, investigate likely causes, record a diagnosis with an appropriate confidence level, understand treatment options and timing, track interventions, and determine whether the plant improves or the problem returns.

### 1 Disease / Health Problem Records

- Problem or disease name, including common and scientific/pathogen name when known.

- Problem category: fungal, bacterial, viral, oomycete, nematode, physiological/environmental, nutrient-related, unknown, or other.

- Host plant species commonly affected.

- Typical symptoms and distinguishing characteristics.

- Parts of the plant affected: leaves, stems, bark, flowers, fruit, roots, crown, or whole plant.

- Conditions that favor the disease or problem, such as prolonged leaf wetness, poor drainage, heat, cold injury, drought stress, or nutrient imbalance.

- Typical season or environmental conditions when symptoms appear.

- How the disease spreads when applicable.

- Whether affected material should be removed and how it should be disposed of.

- Sanitation and prevention recommendations.

- Treatment options and the best timing for treatment.

- Expected prognosis and likelihood of recurrence.

- Whether the condition may threaten nearby plants.

- Reference notes and diagnostic resources.

### 2 Plant Health Observations / Cases

A disease record describes a condition generally; a Plant Health Case documents a specific problem occurring on a specific plant or group of plants.

- Date symptoms were first noticed.

- Yard location.

- Detailed symptom description.

- Photos, including the ability to add follow-up photos over time.

- Severity: mild, moderate, severe, or declining.

- Recent environmental or care factors such as irrigation changes, pruning, transplanting, frost, heat, or fertilizer application.

- Suspected diagnosis or diagnoses.

- Diagnostic confidence: possible, likely, confirmed, or unknown.

- How the diagnosis was confirmed, if applicable: visual identification, laboratory test, extension service, arborist/horticulturist, or other expert.

- Current status: investigating, monitoring, treating, improving, stable, worsening, resolved, or plant lost.

### 3 Diagnosis Workflow

The app should avoid presenting an uncertain visual diagnosis as a confirmed fact. Diagnosis should be a guided process that records symptoms and possible causes and clearly communicates uncertainty.

- Select an affected plant or create a health observation from the plant profile.

- Photograph the whole plant and affected areas.

- Record symptoms, affected plant parts, timing, recent care, and environmental conditions.

- Compare symptoms against likely diseases, pests, nutrient problems, and environmental causes.

- Display one or more possible diagnoses when certainty is limited.

- Allow the user to mark a diagnosis as possible, likely, or confirmed.

- Recommend professional or laboratory confirmation when visual symptoms are insufficient or when the consequences of a wrong diagnosis are significant.

### 4 Treatment Plans

Once a diagnosis or working diagnosis exists, PNW Home YardWise should provide a treatment plan that favors practical cultural and sanitation measures first and clearly identifies timing and follow-up.

- Immediate actions, such as removing affected material, correcting watering, improving drainage or airflow, or isolating affected material.

- Cultural controls and environmental corrections.

- Pruning or sanitation instructions, including tool-cleaning recommendations when relevant.

- Biological controls when appropriate.

- Chemical treatment options when appropriate, without making chemical treatment the automatic default.

- Best treatment timing or plant growth stage.

- Number/frequency of treatments when appropriate.

- Follow-up inspection schedule.

- Signs that treatment is working or failing.

- Prevention steps for the next season.

- Ability to convert recommended actions into scheduled tasks.

### 5 Treatment Safety

- Treatment information should distinguish general horticultural guidance from product-specific pesticide directions.

- When a pesticide or fungicide is considered, the app should remind the user to verify that the product label permits use on the target plant and disease and to follow the current label directions.

- The app should support recording the product used, date, target problem, and treatment notes.

- Safety information should account for edible plants, harvest timing, pets, children, pollinators, and nearby desirable plants when relevant.

- The app should not invent pesticide rates or application instructions when reliable product-specific information is unavailable.

### 6 Disease & Treatment History

- Maintain a chronological timeline of symptoms, diagnoses, treatments, and follow-up observations.

- Allow repeat photographs from approximately the same view to document progression or recovery.

- Record whether a problem recurs in subsequent years.

- Link treatment activities to the corresponding health case.

- Allow a resolved case to be reopened if symptoms return.

- Preserve historical cases even if the affected plant is later removed or dies.

### 7 AI-Assisted Diagnosis

AI functionality may analyze plant photographs and recorded symptoms to suggest likely diseases, pests, nutrient deficiencies, or environmental stress. AI results must be framed as diagnostic possibilities rather than guaranteed diagnoses and should explain the observations supporting each possibility.

- “What is wrong with this plant?”

- “Compare today’s photo with the one I took two weeks ago.”

- “Which plants have had the same disease more than once?”

- “Could this be a watering problem rather than a disease?”

- “What treatments are due this week?”

- “Which unresolved plant problems are getting worse?”

### 8 Yard Problems Integration

Yard Problems should now be designed around three primary categories: Weeds, Pests, and Diseases/Plant Health. A problem can be linked to one or more plants, a yard area, photographs, tasks, treatments, and journal entries. This shared structure should make it possible to view all active problems affecting a particular plant or area of the yard.

[Back to Table of Contents](#table-of-contents)

# 8. Sprinkler & Irrigation System

PNW Home YardWise should include a dedicated Sprinkler & Irrigation section because the irrigation system is part of the property's long-term infrastructure and may initially be only partially understood. The feature must support discovery and documentation over time rather than requiring the user to know the complete system before entering it. Unknown zones, uncertain pipe routes, unidentified valves, and partially mapped sprinkler coverage are valid records that can be refined as the system is investigated.

### 1 Irrigation System Overview

- System/controller name and location.

- Controller manufacturer, model, photographs, and notes when known.

- Water source and shutoff location when known.

- Backflow device location and information when known.

- Master valve or pump information when applicable.

- Number of controller stations versus number of confirmed irrigation zones.

- Known and unknown valves.

- General system notes, repair history, and documentation.

- Ability to explicitly mark information as Unknown, Suspected, or Confirmed.

### 2 Zone Discovery & Identification

The app should provide a workflow specifically for figuring out an existing sprinkler system one zone at a time.

- Create temporary records such as 'Unknown Zone 1' or 'Controller Station 4' before the served area is understood.

- Run or manually activate a controller station and record what turns on.

- Walk the property and tap each active sprinkler, drip area, or watered garden bed on the map.

- Take photographs of active heads, valves, emitters, and coverage patterns.

- Record observations such as weak pressure, broken head, overspray, dry area, or unknown endpoint.

- Rename the zone once its purpose is understood without changing its permanent system ID.

- Track investigation status: Unknown, Partially Mapped, Mapped, Verified.

- Record the date a zone was last physically verified.

### 3 Irrigation Zone Records

- Permanent Zone ID.

- Controller station number when known.

- User-facing zone name.

- Zone type: spray, rotor, drip, bubbler, micro-irrigation, hose/manual, or mixed/unknown.

- Garden beds, lawn areas, trees, containers, or other areas served.

- Mapped coverage area.

- Valve associated with the zone when known.

- Sprinkler heads/emitters associated with the zone.

- Typical runtime and schedule.

- Seasonal schedule changes.

- Flow/pressure notes when known.

- Current status: active, disabled, needs repair, unknown, or seasonal.

- Photos, notes, repairs, and verification history.

### 4 Interactive Irrigation Mapping

- Provide an Irrigation layer on the existing property map.

- Allow the user to tap/click exact sprinkler-head, emitter, valve, controller, shutoff, and backflow-device locations.

- Allow irrigation coverage to be drawn as approximate areas or polygons.

- Allow suspected underground pipe routes to be drawn as dashed/uncertain lines and later changed to confirmed routes.

- Selecting a zone should highlight every known head/emitter and the approximate area served.

- Selecting a garden bed should show which irrigation zone or zones serve it.

- Selecting an individual sprinkler head should show its zone, type, notes, photos, and maintenance history.

- Allow overlapping irrigation zones to be displayed independently.

### 5 Sprinkler Heads, Emitters & Valves

- Unique component ID.

- Component type.

- Exact map location.

- Associated irrigation zone when known.

- Manufacturer/model/nozzle information when known.

- Photograph.

- Coverage direction or radius when useful.

- Condition: good, needs adjustment, leaking, clogged, broken, buried/missing, or unknown.

- Installation/replacement date when known.

- Maintenance and repair history.

- Free-text notes.

### 6 Irrigation Investigation Mode

Because an inherited or undocumented sprinkler system may need to be reverse-engineered, PNW Home YardWise should provide an Investigation Mode optimized for phone use while walking the property.

- Select the controller station being tested.

- Start an observation session.

- Tap the map wherever water is observed.

- Add a head/emitter with one tap and optionally photograph it.

- Mark dry spots or areas unexpectedly receiving water.

- Mark suspected valves or pipe routes.

- Add voice-dictated notes.

- End the session and review the collected observations.

- Update the zone's confidence/status from Unknown toward Verified as evidence accumulates.

### 7 Irrigation Coverage & Garden Relationships

- Each garden bed may link to one or more irrigation zones.

- A bed should indicate whether irrigation coverage is Confirmed, Partial, Suspected, None, or Unknown.

- Plants may inherit the irrigation information of their bed while allowing plant-specific exceptions.

- The map should help reveal garden areas with no known irrigation coverage.

- Coverage notes should support overspray, blocked spray, excessive watering, insufficient watering, and seasonal changes.

- Drip lines serving multiple plants should be represented as zone/area infrastructure rather than requiring a separate irrigation record for every plant.

### 8 Scheduling & Watering History

- Store the programmed watering schedule for each zone.

- Support different seasonal schedules.

- Record manual watering or manual zone runs when desired.

- Record temporary schedule changes.

- Allow maintenance tasks such as spring startup, head adjustment, filter cleaning, winterization, and leak inspection.

- Maintain historical schedule information so watering changes can be compared with plant-health observations.

### 9 Repairs & Maintenance

- Record leaks, broken heads, clogged emitters, valve failures, controller problems, pressure issues, and other faults.

- Attach a repair to the affected zone/component and exact map location.

- Add before/after photographs.

- Record repair date, work performed, replacement part, cost if desired, and notes.

- Create follow-up inspection tasks.

- Maintain a permanent repair history for the irrigation system.

### 10 AI Assistance

AI may help organize irrigation observations and infer possible relationships, but uncertain infrastructure must remain clearly labeled. User-confirmed zone assignments, component locations, and pipe routes are authoritative.

- Suggest zone names based on the mapped area served.

- Group sprinkler observations that appear to belong to the same controller station.

- Identify likely sprinkler-head or irrigation-component types from photographs.

- Suggest possible coverage gaps or overlap based on mapped observations.

- Help summarize what remains unknown about the system.

- Never convert a suspected underground route or zone relationship to Confirmed without user approval.

[Back to Table of Contents](#table-of-contents)

# 9. AI Assistance, Confidence & User Authority

## Canonical AI behavior

- AI is available throughout the finished product; it is not a separate future phase.

- AI output must expose confidence/uncertainty where relevant and distinguish suggestion from confirmed user data.

- User overrides are field-level and persistent. Refreshing AI enrichment may propose alternatives but cannot replace locked/user-confirmed values.

- AI may use property location, plant identity, season, weather context, history, photos, and current tasks as context, subject to privacy settings.

- AI actions that would change authoritative records require user confirmation.

## AI Capabilities

- Plant identification from a photograph, requiring user confirmation before adding to inventory.

- Natural-language questions such as “What should I do in the yard this weekend?” or “What can I prune now?”

- Use plant inventory, task history, journal, season, location, and weather as context for recommendations.

- Surface patterns such as repeated heat stress or approximate annual bloom/harvest timing.

- Suggest missing care tasks, with the user deciding whether to add them.

## AI-Assisted Record Enrichment and User Override

PNW Home YardWise should use AI to help complete and maintain structured information for existing plants, Plant Wish List entries, and identified weeds. The purpose of AI enrichment is to reduce manual data entry while keeping the user in control of the authoritative garden record. AI-generated values are suggestions, not locked facts, and every AI-populated field must remain editable by the user.

### 1 Existing Plant Enrichment

- When a plant is identified or its common/botanical name is entered, AI may propose missing profile details.

- Suggested details may include botanical name, cultivar characteristics when known, annual/perennial status, plant type, evergreen/deciduous status, mature height and width, hardiness zones, sun exposure, water needs, soil preferences, bloom period, pruning period, fertilizing period, harvest period, pollination information, toxicity considerations, and general care notes.

- AI should use existing user-entered information, photographs, geographic region, and other relevant record context when generating suggestions.

- AI must not silently replace a user-entered cultivar, location, observation, date planted, treatment history, or other user-authored fact.

### 2 Plant Wish List Enrichment

- Entering only a plant name should be sufficient to request AI completion of the basic Wish List profile.

- AI may fill annual/perennial status, plant type, mature height and width, preferred hardiness zones, best planting period, sun and water requirements, bloom period, bloom characteristics, harvest period for edible plants, time to maturity or bearing when useful, and pollination requirements.

- AI may flag whether the plant appears suitable for the user's growing region and provide contextual notes, while leaving the user free to keep any plant on the Wish List.

- When a Wish List item is moved into the planted inventory, accepted AI-enriched information should carry forward with the record.

### 3 Weed Record Enrichment

- After a weed is identified or manually named, AI may populate the weed species profile.

- Suggested details may include botanical name, annual/biennial/perennial status, native/introduced/invasive status, regional noxious-weed status when reliably known, growth habit, spread mechanisms, emergence and flowering periods, seed-production timing, best control window, preferred control methods, removal details, disposal guidance, persistence/seed-bank information, and follow-up recommendations.

- Control recommendations should be relevant to the user's region and should clearly distinguish identification confidence from confirmed local regulatory status.

- AI-generated control information must remain editable and should not automatically create or execute treatment actions without user approval.

### 4 Field-Level Source and Override Behavior

- Each enrichable field should track whether its current value is User Entered, AI Suggested/Accepted, or Imported/Reference Data when applicable.

- AI-generated values should be visually distinguishable during review, for example with a small “AI” indicator or source label.

- The user can edit any AI-generated field directly. Once the user changes that field, the user-entered value becomes authoritative.

- A user override must not be automatically replaced during later AI refreshes or re-analysis.

- If AI later finds conflicting information for a user-overridden field, it may show a non-destructive suggestion such as “Alternative information available,” but must require explicit user action to replace the saved value.

- The user should be able to accept all AI suggestions, accept selected fields, reject selected fields, or dismiss the enrichment without changing the record.

- Where helpful, the app should offer “Restore AI suggestion” or “Recheck with AI” without deleting the user's current value until the user confirms the replacement.

### 5 AI Enrichment User Experience

- Provide a clear action such as “Fill Details with AI” on Plant, Wish List, and Weed profiles.

- When many fields are empty, show a review screen comparing Current Value and AI Suggestion before saving.

- For an existing record, populate only missing fields by default; do not overwrite populated fields.

- Allow the user to request a full recheck when desired, while preserving overrides.

- Show confidence or uncertainty when AI is not confident about a cultivar, identification, regional status, or care recommendation.

- Record the date of the last AI enrichment so the user can tell when reference information was last reviewed.

### 6 AI Data Governance

- The user's saved record is the source of truth for PNW Home YardWise.

- AI is an assistant for filling gaps and proposing updates, not an autonomous editor of the garden database.

- User-authored notes, observations, dates, treatments, and overrides must always take precedence over generated content.

- AI re-analysis should preserve historical values and should not retroactively rewrite activity, disease, treatment, harvest, or journal history.

- The app should make it possible to see which information was generated by AI when provenance matters.

[Back to Table of Contents](#table-of-contents)

# 10. Notifications, Tasks, Calendar & Seasonal Guidance

## Canonical notification rules

- Tasks are durable work records; notifications are delivery mechanisms for tasks, horticultural windows, monitoring prompts, and photo opportunities.

- Planting guidance uses property climate/frost dates and crop requirements; hardiness zone alone is insufficient for annual planting dates.

- Weather may refine or warn about timing but must not silently reschedule user-entered dates or change irrigation schedules.

- Notifications are opt-in, deduplicated against completed actions, and support complete, snooze, reschedule, dismiss, and Not Applicable where relevant.

- Photo prompts are context-aware: perennial seasonal-photo needs differ from annual growth-stage milestones.

## Tasks and horticultural timing

- Support exact dates, seasonal windows, intervals, yearly recurrence, and one-time tasks.

- Completing a recurring task preserves the completed occurrence and calculates/schedules the next occurrence.

- Home/Today distinguishes overdue, due now, and upcoming work and keeps the list intentionally short.

- Calendar provides a chronological planning view; Today provides the operational priority view.

## Planting, monitoring and photo notifications

- Seed-start, hardening-off, transplant, direct-sow, purchase-start, succession, harvest-window, pest-monitoring, treatment-follow-up, and seasonal-photo reminders are generated from the relevant domain records.

- The user chooses growing method so the system does not send conflicting seed-start versus purchase-start instructions.

- Missing-photo prompts appear only when the photo is seasonally or developmentally appropriate.

# 11. Hosting, Security, Backup & Device Access

## Hosting, Access & Deployment Model

PNW Home YardWise should be designed as a privately hosted web application rather than a public cloud-hosted consumer app. The application should run on a server controlled by the user and be accessible from both laptop and phone through a web browser.

### 1 Private Hosting Requirements

- Application and database hosted on a privately controlled server or home server/NAS environment.

- No public access by default.

- User data, plant photos, journal entries, and maintenance history remain under the user's control.

- The application should support encrypted HTTPS access.

- Authentication is required before viewing or editing garden data.

- Backups should be stored independently from the primary application server.

- The deployment should be portable so it can be moved to another private server later without rebuilding the application.

### 2 Device Access

PNW Home YardWise should use a responsive web interface so the same application can be opened from a laptop, tablet, or phone without requiring separate desktop and mobile applications.

- Laptop/desktop: full-width interface suitable for reviewing records, editing detailed plant information, and managing tasks.

- Phone: touch-friendly layout optimized for adding plants, taking/uploading photos, recording activities, checking tasks, and entering journal notes while outdoors.

- Tablet: responsive intermediate layout.

- The phone experience is a core requirement, not a secondary adaptation.

### 3 Network Access Options

The preferred architecture should support local-network access at home and secure remote access when away from home. Remote access should not require exposing the application directly to the public internet if a safer private-access method is available.

- Local access over the home network.

- Secure remote access through a private VPN, mesh VPN, or equivalent authenticated tunnel.

- Avoid direct public port exposure where practical.

- Use a stable private hostname or local DNS name so the user does not need to remember an IP address.

- Support installation behind a reverse proxy if desired.

### 4 Recommended Technical Direction

The PDD does not require a specific programming framework, but the deployment model should favor technologies that are easy to self-host and maintain. A containerized deployment is preferred because it simplifies installation, upgrades, backup, and migration.

- Responsive web application.

- Self-hosted application service.

- Privately hosted relational database.

- Local/private object or file storage for plant and journal photos.

- Container-based deployment such as Docker or an equivalent approach.

- Environment-based configuration so credentials and server-specific settings are not hard-coded.

- Export capability for plant data and media metadata.

### 5 Privacy and Security Requirements

- Garden records must be private by default.

- All authenticated sessions should use secure cookies or equivalent secure session handling.

- Passwords must never be stored in plain text.

- HTTPS should be used for remote access.

- Photo files should not be publicly enumerable or accessible without authorization.

- Administrative settings should be restricted to the owner account.

- Backups should include both database records and uploaded images.

- The app should provide a clear logout function on shared devices.

## Non-Functional Requirements

- No coding knowledge should be needed for normal use.

- Common screens should feel responsive on a modern phone connection.

- Images should be optimized so a growing photo library does not make the app unusably slow.

- User data must not be publicly visible by default.

- The design should accommodate hundreds of plant records and years of history.

- Data relationships must support AI features without requiring a redesign of the core records.

- The app should handle missing information gracefully; incomplete plant records are valid.

[Back to Table of Contents](#table-of-contents)

# 12. Canonical User Flows

### Add an existing plant while outside

Plants → Add Plant → take/select photo → enter “Fuyu Persimmon” → choose Backyard → add location note → Save → optionally add care details later.

### Record pruning

Open plant → Record Activity → Pruned → date defaults to today → optional note/photo → Save. Activity immediately appears in the plant timeline.

### Create annual maintenance

Open plant → Add Task → “Prune” → seasonal window “Late winter” → repeat yearly → Save. When completed, the occurrence remains in history and the next annual occurrence is available.

### Capture an observation

Journal → New Entry → dictate observation → attach photo → link plant → Save. The entry appears both in the journal and on that plant’s history/profile.

[Back to Table of Contents](#table-of-contents)

# 13. Consolidated Functional Requirements & Acceptance Criteria

This section is the canonical implementation checklist. Feature chapters describe behavior; this list is the deduplicated cross-document requirement set. If wording elsewhere conflicts, this section and the canonical rules at the start of each module govern.

## 13.1 Functional requirements

- R-001: Provide a prioritized Today home screen with direct links to relevant records and actions.

- R-002: Provide a persistent universal quick-add action for common outdoor workflows.

- R-003: Provide a What Is Here? map action that summarizes records at a selected location.

- R-004: Support optional QR and NFC deep links to authorized YardWise records.

- R-005: Provide a phone-first Walk the Yard rapid-capture workflow with end-of-walk review.

- R-006: Support voice entry with user approval of AI-extracted structured data.

- R-007: Provide a concise Plant At-a-Glance view with direct access to deeper plant information.

- R-008: Support Favorite and Watch status with Today/Watch List integration.

- R-009: Support optional weather-aware recommendations without silently changing user schedules.

- R-010: Provide a Now / Coming Soon / Later This Season dashboard.

- R-011: Provide first-class before-and-after and year/season photo comparison workflows.

- R-012: Apply progressive disclosure and context preservation across primary navigation and map interactions.

- R-013: The property must support a configurable coordinate grid.

- R-014: Every garden bed must have a stable unique system ID and a unique user-facing name.

- R-015: Garden beds may occupy one or multiple grid cells.

- R-016: Plants, weeds, pest/disease cases, tasks, journal entries, and photos must support garden-bed location links.

- R-017: The map must allow selection of a bed to view its plants, problems, tasks, and history.

- R-018: Garden beds must remain historically identifiable after renaming, redesign, or retirement.

- R-019: The user must be able to search by bed name, Bed ID, short code, and grid coordinate.

- R-020: The interface must support both visual map navigation and non-map list navigation.

- R-021: User-defined location information must override AI-generated location suggestions.

- R-022: Users must be able to assign a location by clicking or tapping the property map.

- R-023: Map selection must automatically associate the point with the containing bed and grid coordinate when applicable.

- R-024: Users must be able to reposition a location before saving.

- R-025: Plants and weed sightings must support individual map points.

- R-026: Weed infestations must support multiple points and/or approximate mapped areas.

- R-027: Existing markers must be selectable from the map to identify the associated plant, weed, or yard problem.

- R-028: The same interaction must work on laptop and phone.

- R-029: Exact map locations must remain historically stable when garden display names change.

- R-030: Selecting a plant must provide a direct way to display its location on the property map.

- R-031: The map must automatically center on and highlight the selected plant's current location.

- R-032: All active locations for a multi-location plant record must be highlightable together.

- R-033: Historical locations must be preserved and optionally displayable.

- R-034: Current and historical plant locations must be visually distinguishable.

- R-035: The containing garden bed and grid coordinate must be identifiable when a plant is highlighted.

- R-036: Plant selection and map-marker selection must work bidirectionally.

- R-037: Users must be able to import one or more aerial/property images as map reference layers.

- R-038: Users must be able to import a hand-drawn property plan as a reference layer.

- R-039: Reference images must support rotation, scaling, positioning, and visibility controls.

- R-040: Garden beds must be traceable as editable polygons over aerial imagery.

- R-041: The map must support polygon, line, and point landscape features.

- R-042: Users must be able to switch between aerial, clean-map, and hybrid views.

- R-043: Replacing or adding aerial imagery must not automatically alter confirmed map geometry or record locations.

- R-044: AI may suggest map features but user-confirmed geometry must remain authoritative.

- R-045: The structured map must remain fully integrated with plant, weed, pest, disease, task, journal, and harvest records.

- R-046: The default property map must suppress unnecessary fine-detail markers and labels.

- R-047: Map detail must increase progressively with zoom and explicit user selection.

- R-048: Selecting a garden bed must open a focused bed view with category filters and a contents list.

- R-049: Bed filters must include Plants, Trees/Large Shrubs, Annuals, Sprinklers/Irrigation, Weeds, Pests, Diseases/Plant Health, Tasks, and infrastructure.

- R-050: The Bed Contents view must list all current plants in the selected bed.

- R-051: Selecting a plant from the bed list must highlight its exact mapped location(s).

- R-052: Selecting a map marker must select/highlight the corresponding list record.

- R-053: Every listed plant must provide direct access to its full Plant Profile.

- R-054: Returning from a Plant Profile must preserve the prior bed, map zoom, filters, and selection when practical.

- R-055: Bed Focus mode must work effectively on both laptop and phone.

- R-056: The Journal must include a Plant Wish List for plants not yet in the active yard inventory.

- R-057: Wish-list records must support plant lifecycle, planting time, mature size, bloom period, hardiness zone, and harvest information.

- R-058: Wish-list plants must be searchable, sortable, filterable, and taggable.

- R-059: A wish-list plant can be converted into an active plant record without re-entering its saved information.

- R-060: The user can create planting tasks and planned yard locations directly from wish-list records.

- R-061: Journal entries can link to wish-list plants.

- R-062: Edible wish-list plants can store expected harvest timing and time-to-bearing information when applicable.

- R-063: Plant records must support multiple photographs.

- R-064: Photos must support categories including whole plant, leaves, flowers, fruit, and seasonal appearance.

- R-065: Photos must retain date, season, year, caption, and category metadata when supplied.

- R-066: The user must be able to browse photos by chronology, season, year, and plant feature.

- R-067: The user must be able to select and change a plant's primary photo.

- R-068: Photos may be linked to harvest, journal, weed, pest, disease, treatment, or maintenance records without duplicate image storage.

- R-069: AI may suggest photo metadata, but the user must be able to override all AI-generated photo classifications and captions.

- R-070: The application should support side-by-side comparison of selected plant photographs.

- R-071: Annual crops must support a permanent variety record and separate seasonal planting records.

- R-072: PNW Home YardWise must provide a yearly Vegetable Garden Planner integrated with mapped garden beds.

- R-073: Planned annual crops must support exact map placement and conversion to active seasonal plantings.

- R-074: The planner must preserve prior-year plans and planting history.

- R-075: The system must calculate planting milestones using the property's climate profile, crop requirements, and chosen growing method.

- R-076: The system must support distinct workflows for indoor seed starting, direct sowing, and purchased starts.

- R-077: Compatible devices must support opt-in push notifications plus in-app alerts for planting milestones.

- R-078: Notifications must support snooze, reschedule, dismiss, completion, and Not Applicable actions.

- R-079: The system must support succession planting and multiple sowing/transplant dates for one crop.

- R-080: Crop rotation/history must be visible by garden bed and growing year.

- R-081: Annual photo prompts must be growth-stage aware rather than requiring irrelevant seasonal photos.

- R-082: Harvest events must link to the specific seasonal planting.

- R-083: User-selected planting dates and climate overrides must take precedence over AI-generated recommendations.

- R-084: Seed-started and direct-sown crops must support seedling reference information and early-growth photographs.

- R-085: Direct-sown seasonal plantings must retain the exact mapped area where seed was placed.

- R-086: The app must provide reference images and identifying characteristics during the expected emergence period.

- R-087: 'Is This a Weed?' must consider expected seedlings at the selected property location before recommending removal.

- R-088: AI seedling identification must incorporate crop, location, and sowing-date context when available.

- R-089: Users must be able to classify an emerging plant as Expected Seedling, Weed, Volunteer, or Unsure.

- R-090: Seedling identification reminders must be dismissible and stop after establishment is confirmed.

- R-091: User-confirmed seedling identifications must override AI-generated classifications.

- R-092: Every edible or fruit-producing plant can store multiple individual harvest events.

- R-093: Each harvest event stores at minimum a date and may optionally store quantity, unit, quality, photos, use, and notes.

- R-094: The app calculates seasonal harvest totals when compatible quantities are available.

- R-095: Users can review harvest history by plant and by year.

- R-096: Users can edit or correct prior harvest records.

- R-097: Harvest history is preserved when a plant is archived or removed.

- R-098: AI insights may analyze harvest history but may not change user-recorded harvest data.

- R-099: Create, edit, search, and view weed species records.

- R-100: Record multiple weed sightings/infestations and associate each with a yard location.

- R-101: Store recommended control methods and best control timing for each identified weed.

- R-102: Create weed-control and follow-up tasks from an infestation record.

- R-103: Record treatment history and monitor recurrence or resolution.

- R-104: Surface time-sensitive weed-control priorities on the Home/Tasks views.

- R-105: “Is This a Weed?” must be available as a global action throughout the application.

- R-106: The workflow must support taking a photograph directly from a phone.

- R-107: Identification results must include confidence and alternatives when appropriate.

- R-108: The result must connect directly to weed sightings, plant inventory, control tasks, treatment records, or monitoring.

- R-109: The app must not automatically initiate or record destructive control solely from an AI identification.

- R-110: When available, weed status and control recommendations should be relevant to the user's geographic region.

- R-111: Create and maintain pest species records and individual pest sightings.

- R-112: Pest sightings must link to plants, beds, grid cells, and exact map locations.

- R-113: Provide a global 'What Is This Pest?' photo-identification workflow.

- R-114: Pest identification must distinguish harmful pests from beneficial or neutral organisms when possible.

- R-115: Pest records must include monitoring, control options, and best treatment timing.

- R-116: Treatments and follow-up observations must remain in historical records.

- R-117: Selecting a pest must be able to highlight its known locations on the property map.

- R-118: AI-generated pest information must remain editable and subordinate to user corrections.

- R-119: Create and maintain plant health/disease cases linked to individual plants.

- R-120: Record symptoms, severity, photographs, suspected diagnoses, and diagnostic confidence.

- R-121: Store disease information including treatment options and best treatment timing.

- R-122: Create treatment and follow-up tasks from a plant health case.

- R-123: Record treatment history and subsequent improvement, worsening, recurrence, or resolution.

- R-124: Support multiple possible diagnoses when the cause is uncertain.

- R-125: Surface active and worsening plant health problems on Home and plant profiles.

- R-126: Preserve disease and treatment history across growing seasons.

- R-127: PNW Home YardWise must provide a dedicated Sprinkler & Irrigation section.

- R-128: Irrigation records must support Unknown, Suspected, Partially Mapped, Mapped, and Verified information.

- R-129: Controller stations and irrigation zones must be representable even before their served areas are understood.

- R-130: Sprinkler heads, emitters, valves, controller, shutoff, and backflow components must support exact map locations.

- R-131: Selecting an irrigation zone must highlight its known components and coverage on the property map.

- R-132: Garden beds must be able to show which irrigation zone or zones serve them.

- R-133: The app must support an on-site Investigation Mode for mapping zones while testing the system.

- R-134: Suspected and confirmed pipe routes must be visually distinguishable.

- R-135: Irrigation repairs, schedule changes, and maintenance must retain historical records.

- R-136: User-confirmed irrigation information must override AI-generated suggestions.

- R-137: AI can propose missing structured details for existing plant records.

- R-138: AI can propose structured details for Plant Wish List records.

- R-139: AI can populate and update structured weed-species information.

- R-140: Every AI-generated field must be editable by the user.

- R-141: User-overridden values must not be overwritten by later automated AI enrichment.

- R-142: Users can accept, reject, or selectively apply AI suggestions.

- R-143: The interface should identify AI-generated information and preserve useful provenance.

- R-144: AI enrichment of existing records should fill missing fields by default rather than replacing populated fields.

- R-145: NFR-01: The application must function from modern browsers on laptop and phone.

- R-146: NFR-02: The application must support private self-hosting.

- R-147: NFR-03: Core functionality must not depend on a third-party cloud platform remaining available.

- R-148: NFR-04: The deployment must support secure authenticated remote access.

- R-149: NFR-05: The application and user data must be backupable and restorable by the owner.

- R-150: NFR-06: The system should be maintainable without requiring professional server administration for routine use.

## 13.2 Acceptance criteria

- AC-001: The user can open YardWise and understand the most important yard actions for today without reviewing multiple modules.

- AC-002: The user can capture a common outdoor observation in a few taps from the universal + action.

- AC-003: Tapping a map location can answer what is planted, installed, or currently problematic there.

- AC-004: A QR/NFC label can open the intended authorized record without embedding private record content in the label.

- AC-005: A yard walk can capture multiple mixed observations and summarize them for review at the end.

- AC-006: Voice notes can be converted into proposed structured entries without bypassing user confirmation.

- AC-007: A plant profile opens with a concise actionable summary and retains access to complete historical/reference information.

- AC-008: Watched plants or problems can be surfaced prominently without requiring formal tasks.

- AC-009: Weather guidance can modify recommendations while leaving user-entered schedules authoritative.

- AC-010: The seasonal dashboard distinguishes immediate work from upcoming and later-season activities.

- AC-011: The user can easily compare plant/bed/problem photos across time or before/after an intervention.

- AC-012: The interface remains clean as the database grows because detail is revealed progressively.

- AC-013: The user can create a property grid and assign stable coordinates.

- AC-014: The user can create many garden beds without naming conflicts.

- AC-015: Each garden bed has both a stable internal ID and a user-friendly unique name.

- AC-016: A plant can be assigned to a specific bed and approximate location within it.

- AC-017: Tapping or selecting a bed shows everything associated with that bed.

- AC-018: Renaming a garden does not break plant, task, journal, weed, disease, or harvest history.

- AC-019: The map remains usable from both phone and laptop.

- AC-020: The grid and garden-bed system functions as the authoritative location model across the application.

- AC-021: A user adding a plant can tap its physical location on the property map and save it without typing a bed name.

- AC-022: The app automatically shows the correct bed and grid cell for a point inside a mapped garden.

- AC-023: A user identifying a weed can place the sighting directly on the property map.

- AC-024: A user can tap an existing map marker and immediately see what plant or weed is located there.

- AC-025: Multiple nearby plants or weeds can be individually selected.

- AC-026: The click/tap workflow is comfortable and accurate on both phone and laptop.

- AC-027: Selecting a plant and choosing Show on Map centers the property map on that plant.

- AC-028: The plant's marker is clearly highlighted even when other markers are nearby.

- AC-029: The garden bed and grid coordinate are visible with the highlighted plant.

- AC-030: A plant with multiple mapped locations highlights all current locations.

- AC-031: A transplanted plant can display both its current location and prior locations.

- AC-032: Selecting a highlighted map marker opens or activates the corresponding plant record.

- AC-033: The user can import an aerial image and trace an irregular curved garden bed over it.

- AC-034: The traced bed receives a permanent Bed ID and unique user-facing name.

- AC-035: Multiple aerial images can be retained and shown or hidden as references.

- AC-036: The hand-drawn garden plan can be used as an additional reference.

- AC-037: The coordinate grid overlays both aerial and clean-map views.

- AC-038: A newer aerial image can be added without losing existing bed, plant, or problem locations.

- AC-039: The user can switch off the aerial image and continue using a clean structured property map.

- AC-040: All click-to-place and selected-item highlighting behavior works consistently across map views.

- AC-041: At the full-property view, the map remains readable even when the database contains many plants, sprinklers, and problem records.

- AC-042: Zooming into a bed reveals additional useful detail without requiring all details to be visible at property level.

- AC-043: Selecting a bed opens a list of the plants currently growing there.

- AC-044: The user can filter the selected bed to show only plants, trees, sprinklers, weeds, pests, diseases, tasks, or selected combinations.

- AC-045: Selecting a plant from the list visibly highlights its location within the bed.

- AC-046: The selected plant provides a direct route to its full Plant Profile.

- AC-047: Selecting a marker on the map highlights the matching list item.

- AC-048: The user can return from the Plant Profile to the same bed view without losing their place.

- AC-049: The user can save a desired plant without adding it to the current yard inventory.

- AC-050: A wish-list record clearly shows whether the plant is annual or perennial and when it should be planted.

- AC-051: The user can see expected mature size, bloom timing, suitable hardiness zone, and harvest timing when applicable.

- AC-052: The user can filter the wish list to find plants suitable for a particular season or yard need.

- AC-053: When the user acquires or plants a wish-list plant, it can be moved into the active inventory while preserving its notes and research.

- AC-054: A plant can have multiple photographs of leaves, flowers, fruit, and the whole plant.

- AC-055: The same plant can have multiple photographs from each season and multiple years.

- AC-056: The user can quickly view what a plant looked like in Winter, Spring, Summer, and Fall.

- AC-057: A user can compare two photographs from different dates or years.

- AC-058: Photo metadata can be edited after upload.

- AC-059: AI-suggested categories never override a user-corrected value automatically.

- AC-060: Plant photos remain part of the permanent historical record.

- AC-061: The user can create a vegetable-garden plan for an upcoming year before planting anything.

- AC-062: The user can place planned tomatoes, lettuce, peas, or other annuals directly into mapped garden beds.

- AC-063: For a tomato marked Start Indoors, the app can generate separate seed-start, hardening-off, and outdoor-transplant reminders.

- AC-064: For the same tomato marked Purchase Starts, the app omits seed-start reminders and provides timely purchase and transplant reminders.

- AC-065: A user can receive an opt-in push notification on a compatible phone when a planting milestone is due.

- AC-066: The user can snooze or override a planting recommendation without the AI reverting the change.

- AC-067: A seasonal vegetable planting can accumulate photos, pest/disease records, maintenance, and multiple harvests.

- AC-068: At the end of the season, the planting can be closed while its history remains associated with the bed and permanent variety record.

- AC-069: The following year's planner can use prior crop placement, outcomes, and harvest history to support planning.

- AC-070: A user who direct-sows carrots can open the planting record and see what carrot seedlings should look like before weeding.

- AC-071: The property map can show the exact area where a crop is expected to emerge.

- AC-072: During the expected emergence period, the user can receive a reminder with seedling-identification guidance.

- AC-073: Using 'Is This a Weed?' in a recently seeded bed checks the expected crop before suggesting that the plant is a weed.

- AC-074: The user can photograph an emerging seedling and compare it with crop reference images.

- AC-075: Confirmed seedlings remain part of the seasonal planting's photo history.

- AC-076: A user can record a harvest from a phone in a few taps.

- AC-077: Multiple harvests can be recorded for the same plant during one season.

- AC-078: The plant profile shows all recorded harvests and the current season total.

- AC-079: The user can compare harvest totals and harvest dates across years.

- AC-080: Historical harvest records remain editable and are never overwritten by AI enrichment.

- AC-081: Edible plants can retain both general expected harvest timing and actual harvest-event history.

- AC-082: The user can identify or manually add a weed and record where it is growing.

- AC-083: The weed profile clearly states how and when the weed should be controlled.

- AC-084: The same weed can have multiple separate infestation locations.

- AC-085: A treatment can be recorded without marking the infestation permanently resolved.

- AC-086: The app can schedule follow-up inspections and retain the treatment history.

- AC-087: Time-sensitive weeds, especially those nearing seed production, can be surfaced as priorities.

- AC-088: The user can photograph a suspected pest and receive an AI-assisted identification with confidence and alternatives.

- AC-089: The user can record leaf mites, slugs, aphids, or other pests and associate them with exact plants and map locations.

- AC-090: The system can identify a beneficial organism and advise that treatment may not be necessary.

- AC-091: The user can see how and when to control an identified pest.

- AC-092: Treatments can be scheduled, recorded, and evaluated at follow-up.

- AC-093: Selecting a pest highlights all active mapped sightings.

- AC-094: Recurring pest problems can be recognized across seasons and years.

- AC-095: The user can open a plant profile and start a health/disease case.

- AC-096: The user can document symptoms with text and multiple photographs.

- AC-097: The app can record a suspected diagnosis without incorrectly treating it as confirmed.

- AC-098: A disease record clearly describes recommended treatment and when treatment is most effective.

- AC-099: Treatment recommendations can be converted into tasks and follow-up inspections.

- AC-100: The user can record treatment results and compare the plant over time.

- AC-101: Recurring disease problems remain visible in the plant's long-term history.

- AC-102: Weeds, pests, and diseases can ultimately be managed through a unified Yard Problems area.

- AC-103: The user can begin documenting the sprinkler system without knowing how all zones are configured.

- AC-104: A controller station can be created as Unknown and progressively mapped as the user investigates it.

- AC-105: While testing a zone, the user can walk the yard with a phone and tap each sprinkler or watered area on the property map.

- AC-106: Selecting a completed zone highlights its known heads, emitters, beds, and coverage area.

- AC-107: A garden bed can show whether and how it is irrigated.

- AC-108: Unknown valves and suspected underground pipe routes can be recorded without presenting them as confirmed facts.

- AC-109: Repairs and changes remain part of the permanent irrigation history.

- AC-110: The irrigation map integrates with the same property grid and garden-bed system used by plants, weeds, pests, and diseases.

- AC-111: A user can enter a plant or weed name and ask PNW Home YardWise to fill missing descriptive and care/control fields.

- AC-112: A Wish List entry can be created with only a name and enriched with useful planting, size, bloom, zone, and harvest information.

- AC-113: The user can modify any AI-populated value and save the change.

- AC-114: A subsequent AI refresh does not overwrite a user-modified field without explicit approval.

- AC-115: The user can selectively accept some AI suggestions while rejecting others.

- AC-116: AI-generated information is distinguishable from user-entered information when reviewing a record.

- AC-117: Core historical records remain unchanged by enrichment operations.

- AC-118: The user can open PNW Home YardWise from a laptop browser on the home network.

- AC-119: The user can open the same PNW Home YardWise instance from a phone browser.

- AC-120: The interface adapts cleanly to both screen sizes.

- AC-121: Garden data remains on the privately hosted server.

- AC-122: Remote access can be enabled securely without making the application publicly browsable.

- AC-123: A documented backup and restore process exists for both records and photos.

- AC-124: A new user can add a plant from a phone in under one minute using only a name and optional photo/location.

- AC-125: The user can open any plant and see its upcoming tasks and chronological activity history.

- AC-126: Completing a recurring task preserves the completed occurrence and schedules/calculates the next one.

- AC-127: The Home screen clearly distinguishes overdue, due, and upcoming work.

- AC-128: The user can record an activity directly from a plant profile without creating a task first.

- AC-129: Journal entries can include photos and can be linked to plants.

- AC-130: Plant search and filtering work across a realistically sized collection.

- AC-131: The application is comfortable to operate on a phone and remains useful on desktop.

- AC-132: Core features function without AI services.

[Back to Table of Contents](#table-of-contents)

# 14. Implementation Notes & Resolved Conflicts

## Map architecture

Merged the former Property Grid, Click-to-Place, Selected Plant Highlighting, Aerial Map Setup, and Clean Map Navigation sections into one canonical spatial module. The structured vector map is authoritative; aerial imagery is reference-only; the grid is a stable overlay.

## AI staging

Removed the earlier statement that AI should be introduced only after the database is dependable because the final product definition explicitly includes AI as an integrated capability. AI remains advisory and user-confirmed.

## Plant versus variety versus seasonal planting

Clarified that reusable species/cultivar facts are not the same record as a physical perennial specimen or an annual seasonal planting. This prevents conflicting location and harvest histories.

## Yard Problems

Unified weeds, pests, and diseases under a shared problem/observation framework while preserving category-specific fields. Global identification actions create/link records rather than creating parallel data models.

## Notifications versus tasks

Clarified that tasks are persistent work items and notifications are delivery/reminder mechanisms. Weather and AI can suggest timing changes but do not silently modify authoritative schedules.

## Photos

Clarified that photos are reusable linked assets. Seasonal photo prompts and annual seedling/growth-stage prompts are different checklists and should not conflict.

## History preservation

Renaming beds, moving plants, ending seasonal crops, or resolving problems must preserve history; records are archived/dated rather than destructively replaced.

## Requirement numbering

Replaced fragmented FR numbering with a single deduplicated R-### implementation checklist and AC-### acceptance checklist to avoid gaps and collisions from iterative drafting.

[Back to Table of Contents](#table-of-contents)
