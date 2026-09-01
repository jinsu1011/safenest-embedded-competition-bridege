# Thermal source provenance

## Latest dedicated source

The active Thermal subsystem in `ondevice_ai/` was compared and synchronized
against the complete dedicated repository state below on 2026-08-16 (KST):

- Repository: `https://github.com/yuname121/safenest-thermal-ai`
- Dedicated `main` included by this synchronization:
  `db51112bfd02cdda2d41e99cf11acde75f771ecf`
- Merged Thermal PR #1 source head included by this synchronization:
  `71c6d08d8a443f6a50d860d27380ff40a87a860e`
- PR: `https://github.com/yuname121/safenest-thermal-ai/pull/1`

The exact synchronization source is the `yuname121` repository and SHA above.
It must not be replaced in provenance text by an earlier owner or upstream SHA.

This is a full Thermal-subsystem synchronization, not a copy of only the PR #1
diff. Files already identical to the dedicated source remain in place; newer
validators, collection tooling, tests, documents, and the XIAO capture firmware
are updated or added at the team repository's established component paths.

## Original upstream and earlier lineage

The synchronization source is forked from the original/upstream repository:

- Upstream repository: `https://github.com/rla1729/safenest-thermal-ai`
- Upstream `main` observed during synchronization:
  `294531a0c57c28fe1be88f95755f06851217ac80`

That upstream relationship is distinct from both the exact `yuname121` sync
commit and the destination team repository. The dedicated source also retains
older imported lineage records:

The dedicated repository records its earlier curated lineage as:

- `https://github.com/sheepmeat/test`, source commit
  `5000354536cf3fd2bdaea10a5db3ce2c6fe1f219`
- `https://github.com/jinsu1011/safenest-embedded-competition`, source commit
  `3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e` as an architecture reference

## Integration boundaries

- Work classification: `TEAM-THERMAL-INTEGRATION / PRE-T-C DEVICE-CAPTURE PREPARATION`.
- `T_C_EXECUTED = NO`; `T_C_DEVICE_CONTRACT_VERIFIED = NO`.

- Thermal dataset contracts, T-A0 through T-B5 scripts/tests/manifests, and
  associated reports live under `ondevice_ai/`.
- The canonical Thermal-90 SNTR UDP V2 capture firmware lives under
  `devices/thermal/xiao_esp32c6_thermal90_udp_capture/`.
- Existing team-specific integrated-node, TCP transport, LCD/web, risk/fusion,
  and historical runtime behavior is preserved and is not replaced by the
  standalone capture pilot.
- The selected T-B5 FULL_INT8 binary remains on the approved external artifact
  store. Raw captures, identifiable data, checkpoints, and Wi-Fi credentials
  are not added to Git.

This record is not a relicensing statement. Authorship, data consent, and
redistribution permission must still be confirmed with the original owners.
