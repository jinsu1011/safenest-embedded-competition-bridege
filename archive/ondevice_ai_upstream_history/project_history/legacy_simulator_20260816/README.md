# Legacy simulator archive

**Classification:** `LEGACY_SIMULATOR_ONLY` and `NOT_CURRENT_PI_RUNTIME`
**Archive date:** 2026-08-16
**Source commit:** `efc7e2eb61a49e221ce0ebf6057b0c1617525ad1`
**Original paths:** `integrated_node/virtual_sensor_streamer.py` and
`integrated_node/safenest_integrated_plotter.py`

This group is the earlier interactive demonstration environment. It generates
synthetic physiological packets and draws a four-panel GUI; the plotter combines
that synthetic stream with the legacy compatibility engine.

The active AI execution path is `integrated_node/run_node.py`, which reads sensor
providers (or explicitly fail-closed adapters), invokes the inference adapters,
and calls `risk/risk_engine.py`. It does not import this archive. The current
Raspberry Pi integration is a separate downstream responsibility and is not
implemented by this simulator.

No model, preprocessing rule, risk weight, threshold, emergency behavior, sensor
firmware, or phase evidence was changed by this archival move. This archive is
kept with `git mv` to preserve provenance and its original internal relationship.
It must not become a runtime fallback. The legacy compatibility engine
`integrated_node/safenest_risk_engine.py` is deliberately not included: historical
tests and learning material still reference it, so its ownership needs a separate
decision.
