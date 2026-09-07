# YardWise backup & restore

What is protected, where it lives, and exactly how to get it back.
Audience: Michael (or a future maintainer with cluster access) - restores are
NOT a family-side operation; the family's job is only to report "something's
wrong" (see HANDOVER.md).

## What gets backed up

| Data | Mechanism | Schedule | Where |
|---|---|---|---|
| Photos + map layers (Garage bucket `yardwise-media`) | Offsite Garage mirror: `rclone copy` from the offsite LXC (`misc/offsite-sync/garage-backup-sync.sh` in `meklab/home`), additive, never pruned | weekly + monthly timers in CT 201 | Offsite Garage (Dad's Mac Mini), same bucket name |
| Database (logical) | `postgres-dumpall` CronJob in `infra`: `pg_dumpall \| gzip` | nightly 01:30 UTC, 30d retention | Garage `db-backups` bucket, `postgres/` prefix |
| Database (volume) | Velero fs-backup of the shared postgres PVC (crash-consistent only - the logical dump is the real DB backup) | with Velero schedules | Garage `velero-backups` |
| Config/manifests | git (`meklab/k8s`, `meklab/yardwise`) | every change | GitLab |
| Secrets | Vault (`secret/prod/yardwise`, `secret/infra/postgres`, `secret/infra/garage/db-backups/writer`) | Vault's own backup regime | see meklab backup architecture |

Photos are NOT on a PVC any more (#28): the pod is stateless and Django writes
straight to the `yardwise-media` bucket via `config/media_storage.py`. Velero
therefore no longer sees them - the offsite Garage mirror is the ONLY copy.
Home Garage runs a single replica (rf=1), so a lost home cluster means a
restore from offsite, not a rebuild from a second replica.

Keep in mind when reasoning about a restore: the database row (`garden_photo`)
and the object in the bucket are backed up on different schedules. A DB
restore older than the bucket leaves orphan objects (harmless); a bucket
restore older than the DB leaves rows whose file is missing - the gated
`/media/<name>` route returns 404 for those, the app does not crash.

## Restore: database

1. Fetch the newest dump (any machine with cluster + Garage access):
   ```bash
   rclone lsl garage:db-backups/postgres/   # pick the newest dumpall-*.sql.gz
   rclone copy garage:db-backups/postgres/dumpall-<ts>.sql.gz /tmp/
   ```
2. Restore only the yardwise database into the shared instance
   (`pg_dumpall` output contains every database - extract just ours):
   ```bash
   # DANGER: the raw section starts with \connect yardwise, which would steer
   # psql at the LIVE database - strip the redirection meta-commands (but keep
   # the \. COPY terminators, which also start with a backslash):
   gunzip -c /tmp/dumpall-<ts>.sql.gz \
     | sed -n '/^\\connect yardwise$/,/^\\connect /p' \
     | sed '/^\\connect /d; /^\\restrict /d; /^\\unrestrict /d' > /tmp/yardwise.sql
   kubectl -n infra exec -i postgres-0 -- psql -U postgres -c \
     "DROP DATABASE IF EXISTS yardwise_restore; CREATE DATABASE yardwise_restore OWNER yardwise;"
   kubectl -n infra exec -i postgres-0 -- psql -U postgres -d yardwise_restore < /tmp/yardwise.sql
   ```
3. Sanity-check `yardwise_restore` (row counts on garden_plant etc.), then either
   point the app at it or rename databases during a brief scale-down:
   ```bash
   kubectl -n prod scale deploy yardwise --replicas=0
   kubectl -n infra exec postgres-0 -- psql -U postgres -c \
     "ALTER DATABASE yardwise RENAME TO yardwise_broken; ALTER DATABASE yardwise_restore RENAME TO yardwise;"
   kubectl -n prod scale deploy yardwise --replicas=1
   ```

## Restore: photos (media bucket)

Objects live at `yardwise-media/<name>` where `<name>` is exactly the value of
`garden_photo.file` / `file_web` / `file_thumb` (and `garden_maplayer.image`).
Restore is a bucket-to-bucket copy from the offsite Garage; no app change.

```bash
# from any machine with rclone remotes for both clusters (offsite LXC has them)
rclone lsd offsite-garage:yardwise-media           # confirm the mirror is populated
rclone copy --progress offsite-garage:yardwise-media home-garage:yardwise-media
```

- `rclone copy` is additive: it never deletes objects that only exist at home,
  so it is safe to run against a live bucket to fill gaps.
- Single lost/corrupted object: copy just that key
  (`rclone copyto offsite-garage:yardwise-media/<name> home-garage:yardwise-media/<name>`).
- Whole home cluster lost: recreate the bucket + scoped key
  (`k8s/apps/garage/buckets/bootstrap.sh` conventions), write the new key to
  Vault `secret/prod/yardwise` (`YARDWISE_S3_ACCESS_KEY`/`SECRET_KEY`), then
  run the copy above BEFORE scaling the app up, so no request 404s on a
  missing derivative.
- Derivatives (`file_web`, `file_thumb`) are regenerable from the original:
  if only derivatives are missing, `Photo.save()` rebuilds them. The
  originals are the irreplaceable part.

The old PVC-era procedure (Velero restore of `persistentvolumeclaims` with
`--selector app=yardwise`) is gone with the PVC; do not follow it.

## Restore drills

- DB dump path: VERIFIED 2026-09-02 - manual CronJob run, dump landed in
  Garage, fetched via the external endpoint, restored into a scratch database
  with zero errors and correct row counts. (The drill also caught and fixed a
  live-fire hazard in this document: the un-stripped \connect line.)
  Re-verify after major postgres upgrades.
- Media bucket drill: NOT YET RUN. First real photos landed 2026-09-06
  (~270 objects). Once the offsite mirror includes `yardwise-media`, verify
  by copying one object offsite -> home under a scratch key and comparing
  checksums (`rclone check`).
