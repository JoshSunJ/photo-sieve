# Designing a photo cleanup product and learning the engineering behind it

## 1. Define observable behavior before choosing tools

The user story is: "Describe a kind of photo, find likely matches in the photos
I permit, review them, and delete the ones I choose."

An acceptance criterion must be observable. "Use AI" is not one. "Typing ramen
shows ranked thumbnails and selecting a photo is required before deletion" is.
Separate requirements from implementation choices:

| Requirement | Current implementation choice | Alternative later |
| --- | --- | --- |
| Understand text and images | OpenCLIP on Mac | MobileCLIP/Core ML on iPhone |
| Read permitted iPhone photos | PhotoKit | Remains PhotoKit |
| Review proposed matches | SwiftUI cards | Full-screen review or swipe queue |
| Delete originals with consent | PhotoKit change request | Remains PhotoKit |
| Avoid cloud inference | Trusted LAN + local model | Entirely on-device model |
| Support debugging without a phone | Folder scanner | Fixture-backed simulator tests |

Do not promise "all unwanted photos removed" when matching is subjective and
your product cannot see iCloud-only or unpermitted assets. Describe the actual
coverage: accessible image assets whose thumbnails are available locally.

## 2. Draw boundaries around reasons to change

The app has four main responsibilities. PhotoKit owns operating-system access;
the ML adapter owns embeddings; candidate policy owns scoring decisions; the UI
owns presentation and selection. Changes should land in the responsible layer.

The Python `rank_scores` function is pure: given the same input it returns the
same output without network calls, filesystem access, or ML downloads. That
makes edge cases cheap to verify. The server authenticates/validates requests,
then delegates. It doesn't know how to draw cards or delete photos.

This is separation of concerns. It is useful because it localizes a change,
not because a project needs an impressive directory tree. If you replace CLIP,
you should not have to rewrite PhotoKit access or confirmation UI.

The prototype uses one concrete model adapter rather than a hierarchy of base
classes. Tests inject a small fake scorer with the same `score` method. Introduce
a formal protocol when you add a second real implementation, not preemptively.

## 3. Give components only the authority they need

The Mac receives image bytes and descriptions. It returns scores. It does not
receive asset identifiers, Photos credentials, or a deletion API. Even a wrong
score cannot by itself remove a photo. The app also starts with no selection.

This is the principle of least authority. A warning saying "AI can be wrong"
is weaker than an architecture in which AI cannot perform the destructive step.
The same idea applies to an invoice assistant: propose a payment separately
from executing it. It applies to coding agents: prepare a diff separately from
deploying it.

PhotoKit enforces another boundary: library changes happen through Apple's
permission and change APIs. A generic desktop script cannot treat an iPhone's
Photos database as an ordinary mounted folder.

## 4. Treat deletion as a transaction

Reading and scoring can be repeated. Deletion has external side effects.
Model the sequence explicitly:

1. Produce candidate scores, without selecting anything.
2. Let the user create an explicit set of stable PhotoKit local identifiers.
3. Freeze that selection for the confirmation action.
4. Re-fetch the selected assets just before deleting.
5. Check that the full set is still accessible and deletable.
6. Ask PhotoKit to apply the change; let Apple's consent flow run.
7. Remove results from the UI only after success.

Why re-fetch? A photo can be removed or permission can change between scan and
confirmation. That's a time-of-check/time-of-use problem. Never target a photo
by its position in a sorted grid: positions change, identifiers describe assets.

Don't automatically retry deletion after an uncertain result. First reconcile
with the current library. A network retry of a score is harmless; repeating a
destructive command needs different rules. The prototype has no network deletion
command, which removes that entire class of distributed failure.

Recoverability matters too: PhotoKit deletion normally uses Recently Deleted.
It is still deletion of the original, with iCloud synchronization if enabled,
and is not equivalent to removing an item from one album.

## 5. Understand the math you are deploying

Let the image encoder produce vector `v` and the text encoder produce `t`.
Normalize them: `v_hat = v / ||v||`, `t_hat = t / ||t||`.
Then `s = v_hat · t_hat` is cosine similarity, theoretically between -1 and 1.
It tells you how aligned the two learned representations are.

For several include descriptions, this product uses their maximum score:
`s_include = max_j similarity(image, include_j)`. That implements OR: ramen
**or** sushi. A mean would answer a different question and could dilute matches
that fit one description strongly.

Optional keep descriptions produce `s_keep`. A candidate must cross an absolute
threshold and lead the best keep description by a margin. This is a heuristic,
not a guarantee that a treasured photo is protected.

A softmax across descriptions would produce numbers summing to one, but those
numbers depend on the other descriptions you supplied. Removing the "menu"
description could make a weak "ramen" match look more confident. Don't display
such a number as "99% sure this should be deleted."

The model also does not know your private meaning of attractiveness or personal
importance. "Hot girls" and "people I don't know" are not objective visual labels.
You can enter arbitrary descriptions, but concrete visual categories are easier
to test. Never silently treat a subjective match as ground truth.

## 6. Evaluate the product separately from the code

Unit tests can establish that a threshold is implemented correctly. They cannot
establish that the model recognizes your intended content.

Create a small private, human-labeled evaluation collection. For ramen, include
ramen bowls, noodle soup, spaghetti, restaurant menus, cartoon ramen, screenshots,
and photos with several dishes. Give each image a desired label before looking
at its score. Record why ambiguous cases are ambiguous.

Divide images into a tuning set and a held-out check set. Try descriptions and
thresholds on tuning images; inspect the held-out set only after choosing them.
If you repeatedly tune against the held-out set, it is no longer held out.

| Outcome | Meaning in this product |
| --- | --- |
| True positive | A photo you want removed appears as a candidate |
| False positive | A photo you want kept appears as a candidate |
| False negative | A photo you want removed is missed |
| True negative | A photo you want kept is not suggested |

Precision = `TP / (TP + FP)`. Recall = `TP / (TP + FN)`.
For cleanup, start by prioritizing precision because wrong suggestions can lead
to wrong deletion. Keep review mandatory. A high-recall discovery view can be a
separate mode, where users expect to inspect more false positives.

Also track product metrics: scan completion rate, unavailable assets, candidates
selected/kept, review time, and recovery rate. For this private prototype, record
these manually without uploading photo data. Do not claim an accuracy value
until you have a defined dataset and reproducible measurement.

## 7. Budget memory, latency, and battery

Never decode the entire photo library at full resolution. A 12-megapixel RGBA
image can occupy roughly 48 MB before extra copies. Thumbnails are enough for
an initial model that itself resizes images further.

The prototype makes one scoring request at a time. That's slower than batching
but gives bounded load, simple cancellation, and understandable progress. The
phone retains only 200 review thumbnails. The engine bounds its image/text vector
caches. Image features are keyed by a SHA-256 digest of transmitted bytes, so
repeated identical thumbnails can avoid re-encoding during one engine session.

That digest is a cache identity, not proof of what a PhotoKit asset represents.
It must never replace the asset's local ID when deleting. A model version must
also be part of the key if you later persist embeddings across model upgrades.

Next optimizations should follow measurements: time thumbnail extraction,
network transfer, image encoding, and text encoding separately. If transfer
dominates, batching/model migration may help. If PhotoKit dominates, parallel
requests may just waste resources. Avoid optimizing from intuition alone.

The current app fetches asset metadata into an array and keeps a bounded preview
set. For enormous libraries, replace that with paged enumeration, a heap for top
results, and on-demand thumbnails. "All" scans remain foreground-only and may
need to be restarted after app suspension.

## 8. Make state and cancellation explicit

The conceptual states are idle, connecting, authorizing, scanning, reviewing,
deleting, and error. The first version uses a few observable properties. As it
grows, replace combinations of booleans with an enum so impossible states are
unrepresentable, such as scanning and deleting simultaneously.

All UI updates happen on the main actor. Blocking thumbnail retrieval happens
on a background queue. PhotoKit is configured for one callback, which avoids
accidentally resuming a Swift continuation twice. Awaiting network I/O yields
control instead of freezing the UI.

Stopping a scan cancels future work; a current synchronous thumbnail request
may finish first. Partial results remain reviewable, but a new scan clears the
old result set and selection. No automatic resume is claimed. A durable resume
feature will need a checkpoint tied to the query, model, asset IDs, and settings.

## 9. Validate at trust boundaries

The engine cannot assume the iPhone is its only client. It validates API version,
JSON type, descriptions, base64, byte size, image dimensions, finite numeric
settings, and model scores. `NaN` is especially easy to overlook because numeric
comparisons behave unexpectedly around it.

The phone validates the local address, rejects redirects, uses an ephemeral
URLSession, and requires a pairing token. Authentication is checked before
decoding image bodies or running expensive inference. Only two scoring requests
are admitted at once; the model itself is serialized with a lock.

These are bounded-load controls, not protection for an Internet service. The
standard library server still creates connection-handling threads; LAN HTTP
does not protect tokens or images against network interception. Before release,
use authenticated encrypted pairing or eliminate the network hop.

## 10. Privacy is an end-to-end property

"Local AI" describes where inference happens. It doesn't automatically mean
"data never leaves the phone," "traffic is encrypted," or "nothing persists."
Be precise about each claim. This prototype transfers thumbnails to your Mac;
it doesn't upload them to a cloud AI API. Its HTTP is plaintext. Model weights
are downloaded and cached. Folder reports persist thumbnails and file paths.

No logs should contain images, tokens, personal paths, or search descriptions.
If you add diagnostics, prefer counters and timings with explicit local-only
storage and a clear reset control. Git ignores aren't access controls: they
reduce accidental commits but don't stop someone deliberately adding a file.
Inspect staged files before every public push.

When moving toward an App Store build, document actual data flows and third-party
model/dependency licenses. Review the selected checkpoint's model card. Shipping
weights and running them personally are different distribution decisions.

## 11. Build a testing pyramid that matches failure cost

| Layer | What to verify | What it cannot prove |
| --- | --- | --- |
| Pure policy tests | Thresholds, margins, OR semantics, finite inputs | Visual recognition quality |
| API tests with fake model | Auth, malformed input, size limits, status codes | Real checkpoint/device compatibility |
| Real model smoke test | Decode → vector → finite score → response | Useful real-world accuracy |
| Labeled evaluation | Precision/recall on defined examples | All future photo distributions |
| Simulator build | Swift/API compatibility, basic UI wiring | Real Photos deletion and Wi-Fi permissions |
| Physical-device test | Permissions, cancellation, recovery, iCloud effects | Universal behavior across OS versions |

Run cheap checks for every change. Run costly checks when relevant. A rendering
change doesn't justify downloading another model checkpoint; a model upgrade
does justify evaluation again. Never use private photo fixtures in public CI.

## 12. Work in reviewable Git changes

Use one issue and branch per coherent behavior change. Write the observable
before/after behavior, then implement the smallest useful slice. Avoid a massive
"everything refactor" PR mixing UI, model replacement, and persistence.

Inspect `git diff`, then stage specific files. Review `git diff --cached` to
catch tokens, generated reports, and unrelated edits. Commit messages describe
the resulting behavior. Push the branch and let CI run. A solo project still
benefits from a PR: it gives you a second reading of the change and a test record.

For agent-assisted work, ask for a narrow task and acceptance criteria. Example:
"Add an album selector. Keep PhotoKit access in PhotoLibrary, retain explicit
review, and document limited-library behavior. Do not add automatic deletion."
Ask the agent to explain the diff and list checks actually run. Then inspect
the boundary and failure paths yourself.

The provided CI workflow checks Python contracts/API behavior, lint, deterministic
project generation, and an unsigned simulator build when activated. It does not
sign a phone app, benchmark the model, or perform deletion tests on your account.
See `VERIFICATION.md` for activation status and checks actually performed.

## 13. Improve reproducibility before inviting users

Version code, API contracts, model/checkpoint identifiers, preprocessing, and
evaluation cases. A fixed threshold isn't portable across arbitrary models.
Lock dependencies for each tested runtime/platform and record the environment.
Do not confuse a broad compatibility range with a reproducible installation.

For persistent scan metadata, start with a local store rather than introducing
accounts and a cloud service. Save only what is necessary. A saved embedding
index needs model/version metadata, asset modification information, invalidation,
deletion cleanup, and permission-change handling. It is not just a dictionary
dumped to disk.

## 14. Choose the next architectural step from evidence

The Mac engine makes experimentation fast and keeps Python ML approachable.
The product users probably want is a standalone iPhone app. A possible next
step is an Apple MobileCLIP/Core ML integration, but image and text encoders,
tokenizer, preprocessing, normalization, and checkpoint pairing must match.
You cannot compare arbitrary Apple Vision vectors to unrelated text embeddings.

Before replacing the engine, measure real-device model size, memory, latency,
battery impact, and retrieval quality. Keep the same candidate-policy and review
boundaries. Once equivalent behavior is demonstrated, remove local networking
from the user flow entirely.

The best next feature is the one that resolves a measured obstacle. If users
can't trust a tiny preview, add a larger one. If permissions are confusing,
improve access guidance. If matching is poor, improve evaluation and descriptions
before adding animations or a backend.
