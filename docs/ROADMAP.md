# Product roadmap

## Current prototype boundary

The implemented path is iPhone PhotoKit → LAN thumbnails → Mac CLIP → ranked
review → explicit selection → PhotoKit deletion. The Mac is required for ML.
There are no cloud AI calls. HTTP is local but unencrypted. Inference quality
on a real user-labeled collection has not been measured.

The folder command is a read-only development tool, not an iPhone deletion path.
The app scans image assets accessible under its Photos authorization and skips
unavailable local thumbnails. It does not promise complete iCloud-library coverage.

## Milestone 1 · Validate the vertical slice

- Complete Xcode license/platform setup and select a signing team.
- Build simulator and run on a physical iPhone.
- Complete permission, cancel, deletion, and recovery device tests.
- Measure ramen retrieval on a small private labeled collection.
- Record latency and memory; capture a working dependency snapshot.

Success means a disposable image can be found, deliberately selected, deleted,
and recovered, with false positives understood and no private data committed.

## Milestone 2 · Make review trustworthy

- Large preview before selection, zoom, dates and Live Photo indicators.
- Album/date filters; visible coverage summary and locally unavailable count.
- Protected favorites and explicit keep/exclusion controls based on PhotoKit
  metadata, rather than asking a model to infer personal importance.
- A paged review queue so the 200-result cap cannot hide useful matches.
- Observe library changes; reconcile removed/edited assets and permission changes.
- Better state enum, scan-session IDs, integration tests of selection invariants.

## Milestone 3 · Remove the Mac

Evaluate a mobile image-text model and a compatible Core ML conversion. Include
the correct text tokenizer and image preprocessing; validate against the Python
reference on fixed synthetic and private labeled samples. Measure size, memory,
latency, thermal behavior, and battery on a real device.

Use a Swift scoring protocol so a Core ML adapter can replace the HTTP client.
Keep PhotoKit and candidate/deletion policy boundaries intact. Remove local
network permissions and pairing only after the replacement actually works.

## Milestone 4 · Support repeat use

- Local embedding index with model/preprocessing versions and invalidation.
- Incremental indexing tied to asset modifications and permission changes.
- Resumable scan sessions, bounded batches, accessibility/localization.
- User-controlled index deletion and accurate privacy disclosures.
- Compatible OS/dependency matrix and repeatable release builds.

## Milestone 5 · Distribution quality

Review model licenses and Apple's current distribution requirements. If a Mac
hop remains, replace plaintext pairing with authenticated encrypted transport.
Add crash recovery, rigorous device tests, and a privacy audit. Keep any analytics
opt-in and image-free. Do not introduce automatic deletion merely because retrieval
looks good on a small sample.

## Features to defer

Accounts, a cloud database, social features, billing, Kubernetes, agents, and
model fine-tuning do not solve the prototype's main uncertainty: can people find
and confidently review the right photos? Add infrastructure when a measured
requirement needs it.
