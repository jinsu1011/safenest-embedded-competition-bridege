# SafeNest mmWave M-C0 audit run log

```text
python3 scripts/mmwave_m_c0_correspondence_audit.py --root . --evidence-root devices/mmwave/firmware --pilot-evidence-root <read-only-pr18-worktree>/devices/mmwave/device_measurements
```

- Evidence-root used: `devices/mmwave/firmware`
- Regular files opened read-only: `224`
- PR18 evidence files opened read-only: `35`
- Expected input files SHA-256 hashed: `12`
- Expected evidence items: `12`
- Expected evidence present: `12`
- Known but not provided: `0`
- PRE_PR18_LEGACY_LOGS sessions analyzed: `10`
- PR18_PILOT_CAPTURE sessions analyzed: `2`
- Reconstructed historical 620-window count: `620`
- Derived input-forensics artifact: `datasets/mmwave/manifests/M-C0_correspondence_audit/620_window_input_forensics.json`
- Long-log expected SHA-256: `7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34`
- Raw JSONL/CSV copied into repository: `false`
- Raw JSONL/CSV modified: `false`
- Output-inside-evidence-root assertion: `passed`
- Inference/model scoring: `not executed`
