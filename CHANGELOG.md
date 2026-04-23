# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.1] - 2026

### Changed
- 32 canonical axes renamed to English (INTENTION, MASS, CONFIDENCE, ...).
  Short codes (S1..P8) unchanged.
- Canonical space restructured into 4 functional blocks:
  Semantics / Dynamics / Gravity / Precision (8 axes each).
- Three axis substitutions vs v0.5:
  D7 SATURATION → CAUSALITY
  G2 DISTANCE → TEMPORAL_ANCHOR
  P7 COST → ACTION

### Removed
- `unc[32]` vector removed from Cogon struct. Uncertainty now lives in
  three specific axes: S5_ENTROPY, P4_NOISE, P6_CONFIDENCE.

### Wire format
- Frame remains 96 bytes. The 32-byte region formerly holding `unc`
  is now `reserved[32]` and always written as zeros. VERSION stays at
  0x02; a future bump to 0x03 will signal new semantics in that region.
- v0.4 frames decode correctly on v0.5.1 (reserved data is dropped).

### Added
- BLEND operator: per-block rules (D4=min, G1=accumulate, G7=max, P6=min).
- DIST operator: weighted by (c1.P6 + c2.P6)/2 instead of per-dim (1-unc).
- ANOMALY_SCORE: centroid weighted by G1_MASS.
- Rules R22 (axis clamp [0,1]) and R23 (G7_K_INTERACTION normalized).
- Pilar 4 boot defaults: 4 axes deviate from 0.5 on boot
  (S7=1.0, G7=0.1, P1=0.8, P7=0.0).
- W matrix calibrated projector as primary embedding → sem[32] path.
  Keyword heuristics retained as opt-in fallback behind
  `keyword-fallback` feature flag.

### Governance
- Adopted Apache-2.0 license.
- Added CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md.

### Internal
- Workspace-wide version alignment via `[workspace.package]`.
- Removed abandoned `leet1337/` experimental parallel workspace
  (preserved in branch `archive/leet1337-experimental`).

## [0.4.0] - 2026

### Added
- 32-axis canonical space across 3 philosophical groups (Ontological,
  Epistemic, Pragmatic) with three valence dimensions (A13, B8, C10).

### Changed
- Expanded from 20 axes (v0.3) to 32.

## Earlier versions

See git history for v0.1 (17 axes), v0.2 (20 axes), v0.3 (30 axes).
