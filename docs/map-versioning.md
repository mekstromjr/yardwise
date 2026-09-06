# Property map authority and versioning

## Current authoritative source

- **Name:** Master Property Map
- **Source file:** `garden/assets/master_maps/pnw-home-master-v1.png`
- **Natural size:** 1072 × 1244 pixels
- **SHA-256:** `1185a0e9fbacecd937bfc9ed96de0401532669e89fe5be9dc223028a7c438cab`
- The repository asset is a byte-for-byte copy of the approved source image.
  It must not be cropped, resized, recompressed, enhanced, or regenerated.

## Authority rules

1. The active master image is the clean property base layer.
2. Beds, paths, plants, irrigation, problems, tasks, and all other interactive
   information are separate database geometry. They are never burned into the
   master image.
3. Aerial and historical photographs are optional reference layers. Adding one
   never promotes it over an active master map and never changes coordinates.
4. AI may propose separate overlay geometry, but it must never modify a master
   image or overwrite confirmed user geometry automatically.

## Revision rules

1. A revised property drawing creates a new immutable `MapLayer` master
   version. Existing versions remain stored and selectable.
2. Each version records the original file checksum and natural dimensions.
   After creation, the source file, checksum, dimensions, version number, and
   revision lineage are locked.
3. The property's coordinate canvas is independent of every image version.
   Once any bed or plant geometry exists, adopting or switching master versions
   cannot resize that canvas or alter stored coordinates.
4. Each version has its own canvas placement. Realigning a revised image changes
   only that image's placement, not the beds, plants, or other overlays.
5. The user explicitly chooses the active version. There is no automatic or AI
   promotion of a revised master.

These rules implement PDD R-043/R-044 and AC-038: imagery can evolve without
losing or silently moving established property data.
