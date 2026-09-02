# YardWise backup & restore

What is protected, where it lives, and exactly how to get it back.
Audience: Michael (or a future maintainer with cluster access) - restores are
NOT a family-side operation; the family's job is only to report "something's
wrong" (see HANDOVER.md).

## What gets backed up

| Data | Mechanism | Schedule | Where |
|---|---|---|---|
| Photos (`yardwise-media` PVC, prod) | Velero `daily-all`/`weekly-all`/`monthly-all` with fs-backup | daily 02:00 UTC (30d), weekly (90d), monthly (180d) | Garage `velero-backups` bucket |
| Database (logical) | `postgres-dumpall` CronJob in `infra`: `pg_dumpall \| gzip` | nightly 01:30 UTC, 30d retention | Garage `db-backups` bucket, `postgres/` prefix |
| Database (volume) | Velero fs-backup of the shared postgres PVC (crash-consistent only - the logical dump is the real DB backup) | with Velero schedules | Garage `velero-backups` |
| Config/manifests | git (`meklab/k8s`, `meklab/yardwise`) | every change | GitLab |
| Secrets | Vault (`secret/prod/yardwise`, `secret/infra/postgres`, `secret/infra/garage/db-backups/writer`) | Vault's own backup regime | see meklab backup architecture |

Garage content replicates offsite per the meklab backup architecture.

## Restore: database

1. Fetch the newest dump (any machine with cluster + Garage access):
   ```bash
   rclone lsl garage:db-backups/postgres/   # pick the newest dumpall-*.sql.gz
   rclone copy garage:db-backups/postgres/dumpall-<ts>.sql.gz /tmp/
   ```
2. Restore only the yardwise database into the shared instance
   (`pg_dumpall` output contains every database - extract just ours):
   ```bash
   gunzip -c /tmp/dumpall-<ts>.sql.gz \
     | sed -n '/^\\connect yardwise$/,/^\\connect /p' > /tmp/yardwise.sql
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

## Restore: photos (media PVC)

Velero restore of just the yardwise pieces from a chosen backup:

```bash
velero backup get                      # pick e.g. daily-all-20260902020000
velero restore create yardwise-media-restore \
  --from-backup daily-all-<ts> \
  --include-namespaces prod \
  --selector app=yardwise \
  --include-resources persistentvolumeclaims,persistentvolumes,pods
velero restore describe yardwise-media-restore
```

Restoring over a live PVC requires deleting the PVC first (scale the deploy to
0, delete PVC, run the restore, scale back up). For a rehearsal, restore into
a scratch namespace instead with `--namespace-mappings prod:yardwise-restore`.

## Restore drills

- DB dump path: verify with a manual job run + scratch-database restore once
  the dump CronJob lands (meklab/k8s MR 291) - record the date here.
  Re-verify after major postgres upgrades.
- Media PVC drill: scheduled as part of the Phase 5 dry run (#19), once real
  photos exist - an empty-volume restore proves nothing.
