# SafeNest version snapshots

This directory contains immutable historical project trees that were removed from
the active workspace root on 2026-08-08. The active project is the repository
root containing `AGENTS.md`.

| Snapshot | Files excluding `.DS_Store` | Pre/post move tree checksum | Status |
|---|---:|---|---|
| `SafeNest_v4.0_20260808/` | 31 | `00b9d112b8a2ccae6965698e8a9edac7c1cc711cc106f1add684cc527a2bef8f` | `ARCHIVED_READ_ONLY` |
| `SafeNest_v5.0_20260808/` | 122 | `73d16f4105d3142c92a6815c94d14218e17b92ce139d25f63d71ed42e3d54312` | `ARCHIVED_READ_ONLY` |
| `SafeNest_v6_pre_flatten_20260808/` | 3 | `6aca2d846385069b0aaaf40e6cf9f5f427cdbf803204c5dca709521545713b0e` | `ARCHIVED_READ_ONLY` |
| `legacy_version_archives_20260808/` | historical nested snapshots | preserved as-is | `ARCHIVED_READ_ONLY` |

The checksum is SHA-256 over the sorted list of each file's SHA-256 plus its
original snapshot-relative path. Moving the three named snapshots did not alter
their file contents.

Archived code must not be imported or selected by the active runtime. Restore a
whole snapshot to a separate workspace if historical reproduction is required.
