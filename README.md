# Photo Sieve

Find photos by text, review the matches, and delete selected originals from your iPhone.

**Prototype architecture: an iPhone app + a Mac on the same trusted local Wi-Fi.**
The iPhone reads Photos with your permission. A Python process on your Mac runs a
pretrained CLIP model against thumbnails. The iPhone displays results and uses
PhotoKit to request deletion of only the photos you explicitly select. There is
no cloud inference and the Mac cannot delete iPhone assets.

This is **not yet an entirely on-iPhone ML app**. Moving the embedding model into
Core ML is a later milestone, not a capability claimed by this prototype.

## What is implemented

- SwiftUI iPhone app and committed Xcode project; iOS 17+.
- Photos read/write authorization, including limited access.
- Newest 100 / 500 / all accessible image assets.
- Local thumbnail retrieval: automatic iCloud downloads are disabled.
- Multiple search descriptions, optional keep descriptions, tunable score/margin.
- Sequential scans, stop button, progress, partial results after errors.
- Up to 200 ranked thumbnails in memory; nothing selected automatically.
- Review selection, application confirmation, then Apple's PhotoKit deletion request.
- Mac-only pairing token, local-host validation, no HTTP redirects, no image request logs.
- CLIP on Apple Silicon MPS when available, with explicit CPU mode.
- Read-only folder scanner with a ranked HTML/JSON review report.
- Unit/API tests and a ready-to-enable GitHub Actions workflow with a simulator build.

## Start the Mac engine

Use **Python 3.10–3.13**. Python 3.14 is intentionally excluded until this
dependency combination is validated. On this Mac, `python3.13` is available.

```bash
cd photo-sieve
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e './engine[dev]'
photosieve serve --host 0.0.0.0
```

The first launch downloads model weights. Allow time for that to complete; no
personal photos are needed for the download. When ready, the terminal prints a
fresh pairing token. Enter it on the iPhone along with the Mac's local address,
such as `http://My-Mac.local:8765`.

Find the Mac's local hostname in **System Settings → General → Sharing**. If
`.local` resolution fails, use its private IPv4 address from Wi-Fi settings.
`0.0.0.0` is the listen address, **not** the address to enter on the phone.
The default without `--host` listens only on `127.0.0.1` for desktop development.

## Run the iPhone app

1. Open `ios/PhotoSieve.xcodeproj` in Xcode. If Xcode asks you to review its
   license or install iOS platform components, complete those steps yourself.
2. In **Signing & Capabilities**, select your Apple development team. Change the
   bundle identifier if Xcode reports that it is unavailable. No team ID is
   committed to this repository.
3. Connect your iPhone, trust the Mac, enable Developer Mode if requested,
   select the phone as the run destination, and press Run.
4. Put the phone and Mac on the same trusted private Wi-Fi. Permit local-network
   access on the phone and allow the Mac process through its firewall when asked.
5. Enter the local address and pairing token. Start with `a bowl of ramen` and
   100 photos. Grant access only to a disposable test album's photos initially,
   using Apple's limited Photos permission.
6. Scan. Tap individual matching photos to select them. Delete only after
   checking the selection. Cancel Apple's prompt to verify the cancel path first.

**Deletion affects the original asset, not just an album entry.** An entire Live
Photo is deleted if selected. With iCloud Photos enabled, deletion syncs to the
other devices on the same account. Photos normally retains deleted items in
Recently Deleted for 30 days. This app never empties Recently Deleted.

Simulator builds are useful for UI checks, but real-device testing is required
for library permissions, Wi-Fi access, iCloud behavior, and deletion prompts.

## Try folder scanning without installing an iPhone app

Copy sample JPEG/PNG files into `data/inbox/`, then:

```bash
photosieve scan data/inbox \
  --prompt 'a bowl of ramen' \
  --prompt 'a plate of sushi' \
  --keep 'a screenshot of a restaurant menu' \
  --threshold 0.25 \
  --output data/reports/food-first-pass
open data/reports/food-first-pass/review.html
```

This mode **does not delete any files** or touch Apple Photos. It creates local
thumbnails and a JSON report containing original paths. Treat those reports as
private. Use a new output folder for each run. JPEG, PNG, WebP, BMP, and TIFF are
supported; export HEIC as JPEG first. iPhone thumbnails already arrive as JPEG.

## How matching works

CLIP maps an image and a text description into vectors in the same space. Their
normalized dot product is cosine similarity. The strongest include description
wins. A photo is a candidate when:

```text
best_include_score >= threshold
and, if keep descriptions exist:
best_include_score - best_keep_score >= margin
```

`0.25` is an uncalibrated starting point, **not a 25% probability**. The correct
threshold depends on your images and descriptions. Keep descriptions compare
visual content; they cannot reliably identify friends or personal importance.
Subjective descriptions such as `hot girls` are accepted as text but may behave
inconsistently. More concrete visual descriptions tend to be easier to evaluate.

## Repository map

| Path | Responsibility |
| --- | --- |
| `ios/PhotoSieve/ContentView.swift` | UI, review, confirmation |
| `ios/PhotoSieve/ScanViewModel.swift` | Scan orchestration and selection state |
| `ios/PhotoSieve/PhotoLibrary.swift` | PhotoKit access, thumbnails, deletion |
| `ios/PhotoSieve/EngineClient.swift` | Local HTTP client and API types |
| `engine/src/photosieve/contracts.py` | Input validation and candidate policy |
| `engine/src/photosieve/model.py` | CLIP inference and bounded RAM caches |
| `engine/src/photosieve/server.py` | Authenticated local scoring API |
| `engine/src/photosieve/cli.py` | Server startup and read-only folder reports |
| `engine/tests/` | Matching and API boundary tests |
| `docs/START_HERE.md` | Guided first run and first learning exercises |
| `docs/DESIGN_AND_WORKFLOW.md` | Architecture, principles, ML evaluation, workflow |
| `docs/DEVICE_TEST_PLAN.md` | Manual test procedure before real deletion |
| `docs/API.md` | Versioned HTTP contract |
| `docs/ROADMAP.md` | Prototype limits and staged product plan |
| `scripts/generate_xcode_project.py` | Reproducible project generation |
| `data/` | Ignored private photos and generated reports |

## Development checks

Tests use only Python's standard library and a fake scorer. They require neither
model downloads nor private photos:

```bash
make check
.venv/bin/ruff check engine/src engine/tests
```

Unsigned iOS build, after completing Xcode setup:

```bash
xcodebuild -project ios/PhotoSieve.xcodeproj -scheme PhotoSieve \
  -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath /tmp/photosieve-build CODE_SIGNING_ALLOWED=NO build
```

Dependency ranges are specified in `engine/pyproject.toml`. A tested installed
version snapshot is in `engine/requirements-macos-arm64-py313.txt`; it is specific
to macOS ARM64 and Python 3.13, not a cross-platform lock or a hash-verified lock.
To recreate that combination, install the snapshot first, then the editable app:

```bash
python -m pip install -r engine/requirements-macos-arm64-py313.txt
python -m pip install -e ./engine --no-deps
```

If model downloading reports a SOCKS dependency error in another environment,
install `socksio` in the virtual environment. The provided snapshot includes it.
The lightweight CI job tests API behavior, not model accuracy or model downloads.
See `docs/VERIFICATION.md` for checks actually performed and current CI status.

## Privacy and prototype limits

The iPhone sends JPEG thumbnails and descriptions, not filenames, library IDs,
GPS metadata, or originals. Thumbnails are re-encoded before transmission. The
server keeps bounded image/text embeddings in RAM and doesn't persist requests.
The phone keeps up to 200 preview images in RAM until a new scan or app exit.
Memory-only storage is not a promise of secure erasure from OS swap/crash data.
Model weights persist in the ML library's normal download cache.

**Local HTTP is not encrypted.** Pairing prevents casual unauthenticated use; it
does not protect against a hostile Wi-Fi network. Use trusted private Wi-Fi,
never forward the port, and stop the process when done. TLS with authenticated
pairing, or fully on-device inference, is required before broader distribution.

The app is foreground-only, scans images rather than videos, does not observe
library changes continuously, retains only 200 results, and does not resume
after termination. It has no background service, cloud backend, accounts,
telemetry, automatic deletion, or guaranteed subjective-content recognition.

## References

- [OpenCLIP implementation and inference examples](https://github.com/mlfoundations/open_clip)
- [PhotoKit change requests](https://developer.apple.com/documentation/photokit/requesting-changes-to-the-photo-library)
- [PhotoKit synchronous thumbnail behavior](https://developer.apple.com/documentation/photos/phimagerequestoptions/issynchronous)
- [Local networking transport settings](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsallowslocalnetworking)
- [Apple's photo deletion and recovery behavior](https://support.apple.com/en-us/104967)

Start learning with [the guided walkthrough](docs/START_HERE.md).
