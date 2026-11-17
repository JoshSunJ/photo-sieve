# Physical-device test plan

Use disposable photos first. Automated Python tests and a simulator build do not
exercise the real Photos library. None of the manual checks below are claimed
as completed merely because this file exists.

## Prepare a controlled sample

Create a small collection of disposable images including wanted matches,
visually similar nonmatches, a screenshot, a Live Photo, and an image you will
remove during testing. Know their expected labels before scanning. Grant limited
Photos permission to this test set initially. Keep at least one recoverable test
image specifically for deletion and recovery checks.

## Permissions and connection

- Deny Photos access: app explains the missing permission; no scan or deletion.
- Grant limited access: only allowed assets appear; limited-access notice is shown.
- Grant full access: newest-100 count respects assets accessible under PhotoKit defaults.
- Deny local-network access: connection fails clearly and no Photos mutation occurs.
- Enter a wrong pairing token: authenticated health check returns an error.
- Enter a public URL or a URL containing credentials: client rejects it.
- Restart engine: old token stops working, new token pairs successfully.
- Stop the engine mid-scan: partial results remain, scan stops with a clear error.

## Scanning and review

- Scan "a bowl of ramen": inspect candidate ranking and nonmatches manually.
- Add sushi on another line: either description can produce a candidate.
- Add a keep description: inspect how the margin changes the candidate set.
- Set a high threshold: fewer candidates; disable filter to inspect retained scores.
- Change settings during scan: controls are disabled; request settings stay consistent.
- Stop scan: no new requests after cancellation settles; partial results remain.
- Start a second scan: old selection/results are cleared before new results appear.
- Scan 500 or all: at most 200 ranked thumbnails retained, counts still reflect the scan.
- Try an iCloud-only image: no automatic network download; unavailable count increases
  if no usable local representation is provided by Photos.
- Try a video: excluded. Try a Live Photo: still representation scanned, entire asset targeted.
- Switch apps or lock phone: record actual suspension behavior; resume is not implemented.
- Revoke/change photo access while running: errors are handled; no stale selected subset
  is silently deleted on a later confirmation.

## Deletion correctness

- No selections: delete is disabled.
- Scanning in progress: selection/deletion is disabled.
- Select one disposable image; cancel the app confirmation: original remains.
- Confirm app dialog, cancel Apple prompt: original remains; selection is not treated as success.
- Confirm both dialogs: only the selected original disappears from Photos and the result list.
- Open Recently Deleted and recover it: recovery works under your library/account conditions.
- Select several assets including one that becomes inaccessible: app refuses the changed set
  rather than silently deleting an accessible subset.
- Try a computer-synced/nondeletable asset: selection is disabled or deletion is refused.
- With iCloud Photos enabled, use only disposable assets to verify cross-device deletion.
- Verify there is no automatic purge of Recently Deleted.

## Privacy and release observations

- Inspect engine logs: no image data, descriptions, PhotoKit IDs, or request URLs printed.
- Inspect repo status after scanning: private data remains ignored.
- Stop the engine/app and restart: prior pairings/results do not persist.
- Capture timings, peak memory, scan completion rate, and OS/device/model versions.
- Test on the minimum supported OS and a current OS before distributing builds.
- Add a large-image inspection view before using the tool on valuable libraries.

Record: device, iOS version, Xcode version, Python/model versions, test date,
checks performed, exact failures, and whether recovery was verified. Do not put
private photos, tokens, local asset IDs, or personal library metadata in a public issue.
