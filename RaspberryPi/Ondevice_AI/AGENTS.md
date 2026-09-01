# SafeNest Active Workspace Instructions

## Canonical project root

- The directory containing this `AGENTS.md` file is the only active SafeNest development root.
- Active code, configuration, datasets, models, tests, manifests, and reports live directly under this root.
- Do not create or use `SafeNest_V4_*`, `SafeNest_V5_*`, `SafeNest_V6/`, or `ondevice_ai/` as alternate active roots.
- Version names belong in model metadata, release tags, reports, and archived snapshot names, not around the active source tree.

## Archive boundary

- `archive/version_snapshots/` contains read-only historical project snapshots.
- Never import code, auto-discover manifests, or resolve runtime models from `archive/`.
- Do not edit archived reports or snapshots to make them look current. Historical paths and claims are evidence of their original state.
- A historical model needed for an active comparison may remain under `models/` only when its lineage and role are explicit in `models/model_manifest.json`.

## Path and provenance rules

- Store repository-relative POSIX paths in JSON, YAML, manifests, metadata, and generated reports.
- Do not persist `/Users/...`, `file://...`, home-relative, drive-specific, or version-wrapper paths in active machine-readable artifacts.
- Runtime path resolution starts from the canonical root and must not fall back to a versioned sibling or archived snapshot.
- Every generated dataset sample must preserve source dataset, subject, session, recording, time/window, extraction profile, label mapping, split, and quality provenance when applicable.

## Multisensor phase workflow

- Follow `docs/20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md` as the active master roadmap.
- Use `docs/20260806_ChatGPT_SafeNest_mmWave_Execution_Sequence_01.md` and `docs/MMWAVE_PHASE_B_OVERVIEW.md` for inherited mmWave details.
- Run mmWave M-B, CO₂ C-A, Thermal T-A, and integration contract inventory I-0 in parallel when their files and evidence are independent; preserve the required phase order inside each sensor track.
- For each sensor track, complete and validate its A0 through A6 before starting that sensor's Phase B model selection.
- A4 voluntary breath-hold labels are derived SafeNest APNEA proxies and must never be described as clinical apnea.
- A5 uses subject-level grouping. All recordings and windows from one subject must remain in exactly one split.
- `AMBIGUOUS` A4 windows are excluded from pure-class training but retained for provenance and transition analysis.
- A6 must extend the approved pilot contracts to all 440 recordings and must report every failure, exclusion, and low-quality result.
- A6 annotation evidence must never fail open. An annotation read/parse failure blocks that recording and must appear in the exception registry; optional reference-sensor failures must be recorded as warnings.
- The A6 exit gate must validate semantic 1:1 correspondence among every window row, provenance row, and canonical numeric row, successful accounting for every A0 recording, and complete checksum coverage.
- Phase B must inherit the immutable A5 subject split, fit preprocessing statistics on TRAIN only, keep LOCKED_TEST unavailable to model selection, and run a near-duplicate diagnostic before comparative evaluation.

## Change and verification discipline

- Preserve user changes and existing A0-A4 artifacts.
- Generated artifacts must be deterministic for the same inputs and configuration; record checksums with repository-relative paths.
- Run the focused phase validator and upstream regression tests after each phase.
- Do not describe an A phase as complete solely because generation finished; the standalone phase validator must pass against the generated evidence.
- Mock success proves software wiring only unless the result is derived exclusively from the actual selected model prediction.
- Do not claim MR60 real-sensor validation, Raspberry Pi performance, or clinical performance without corresponding measurements.

## Team repository handoff contract

### Verified destination and ownership

- The integration target is the private repository `https://github.com/jinsu1011/safenest-embedded-competition`, whose default branch is `main`.
- The destination component is exactly `ondevice_ai/`. Do not create `embed2/`, `SafeNest_V6/`, or `ondevice_ai/ondevice_ai/` inside the team repository.
- Team CODEOWNERS assigns `/ondevice_ai/` to `@sheepmeat` and `@jinsu1011`; changes under `devices/mmwave/`, `shared/contracts/`, root `docs/`, or `.github/` additionally require the owners of those team-repository areas.
- The team repository root is the integration repository root, while `ondevice_ai/` is the canonical AI component root. Runtime model, dataset, config, and report paths inside the component remain relative to `ondevice_ai/` unless a team-wide contract explicitly requires repository-root-relative paths.

### Transfer scope

- Transfer from a clean, reviewed source commit, never from an arbitrary Finder copy or a dirty working directory. Record both the source commit SHA and the target repository base commit SHA in the integration PR.
- Export only Git-tracked active files. Never transfer the source repository's `.git/`, ignored raw archives, local thermal data, hardware bundles, release ZIPs, caches, virtual environments, or machine-specific files.
- Do not transfer the standalone root `.github/` directory into `ondevice_ai/.github/`. Adapt any required workflow at the team repository root in a separate CI commit reviewed by the root `.github/` owner.
- Do not copy standalone `archive/` into `ondevice_ai/archive/`. Historical material stays in the standalone source repository unless `@jinsu1011` approves a specific import into the team repository's root `archive/` area.
- `AGENTS.md` transfers to `ondevice_ai/AGENTS.md` so agents operating in that subtree use `ondevice_ai/` as their canonical root.

### Responsibility-boundary reconciliation

- The team repository already contains an older `ondevice_ai/` tree. Never bulk overwrite or bulk delete it. Inventory both trees, compare every colliding path, and classify each file as replace, merge, preserve, relocate, or retire before staging.
- Team-owned real sensor implementations live in `devices/<device>/src/`; public cross-domain sensor interfaces live in `shared/contracts/`; AI inference, preprocessing, model assets, risk logic, and orchestration live in `ondevice_ai/`.
- Standalone `sensors/co2/`, `sensors/pir/`, `sensors/mmwave/`, `sensors/thermal44/`, `sensors/base_sensor.py`, and overlapping `adapters/` must not be copied as duplicate team drivers. Reconcile their contracts and mocks with `devices/` and `shared/contracts/`, then update AI imports explicitly.
- Preserve fail-closed semantics during reconciliation: missing, invalid, stale, NaN, or unavailable device data must not become a synthetic normal value.
- Do not modify MR60 firmware, hardware logs, device calibration, or team sensor thresholds as part of an AI import unless that change has separate evidence and the corresponding device owner reviews it.

### Integration Git workflow

- Never push directly to the team `main`. Start from an updated `main` and use the team branch convention: `feature/`, `fix/`, `experiment/`, `refactor/`, or `docs/`.
- Do not use `git add .`. Stage an explicit reviewed path list, inspect `git diff --cached`, and verify that no raw data, nested repository, local absolute path, or unrelated team file is included.
- Prefer separate commits for: component file import, device/shared-contract reconciliation, path/import adaptation, generated artifact refresh, and documentation/ownership updates.
- Before the PR, run the standalone A0-A6 validators, the complete `ondevice_ai` test suite from the team repository root, affected `devices/<device>/tests`, import/compile checks, and `git diff --check`. Report the actual counts, skips, failures, and unverified hardware items.
- The PR must state source and target SHAs, collision decisions, files intentionally not transferred, model/dataset checksums, test evidence, hardware impact, remaining risks, rollback procedure, and reviewers. Do not claim that a source-repository test alone proves team-repository integration.
