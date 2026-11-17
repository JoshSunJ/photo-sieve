# Verification record

## Completed locally

- 12 standard-library tests: matching thresholds/margins, malformed inputs,
  finite scores, authentication, request limits, busy response, health, and no
  engine deletion endpoint.
- Ruff lint for the Python engine/tests.
- Python source compilation and CLI help.
- Dependency installation and `pip check`: no broken requirements.
- Info.plist and Xcode project syntax validation with `plutil`.
- Shared Xcode scheme XML validation and deterministic project regeneration.
- Real CLIP inference on generated red/blue square images using CPU, including
  repeated cached inference and invalid-image rejection. Red ranked red above
  blue; blue ranked blue above red. This establishes basic inference wiring,
  **not** photo-cleanup accuracy.
- End-to-end folder command on generated images: two images scored, one corrupt
  image skipped, with HTML, JSON, and thumbnail outputs checked.
- Git ignore checks for images, reports, local environment, and `.env`.

Installed ML combination: macOS ARM64, Python 3.13, PyTorch 2.15.0,
torchvision 0.29.2, OpenCLIP 3.3.0, Pillow 12.3.0. A version snapshot is committed.
MPS was unavailable to the execution environment, so the real smoke test used CPU.

## Not yet verified

- A local Swift build: installed Xcode refuses builds until its license is
  reviewed and accepted by the user. No license was accepted automatically.
- A physical-device run, Photos/library permissions, deletion, cancellation of
  Apple's prompt, Recently Deleted recovery, and iCloud synchronization.
- Recognition accuracy for ramen, portraits, subjective descriptions, or any
  private labeled collection.
- MPS inference, battery use, and large-library performance.

No personal photo library was scanned or modified while building this repository.

## GitHub Actions

The initial CLI credential can create the public repository and publish source,
but GitHub rejected publishing a workflow because it lacks the `workflow` scope.
The connected GitHub app also rejected workflow creation with HTTP 403
(`Resource not accessible by integration`). The complete workflow is retained
at `ci/checks.yml` and is **not active**. There is no passing CI run to report.

If activation remains unavailable, enable it from GitHub's web editor by creating
`.github/workflows/checks.yml` with the contents of `ci/checks.yml`, or authorize
workflow access in your own terminal and commit that file. No additional access
is needed to run the Python checks locally.

## Reproduce the real-model smoke check

This downloads weights on first use and uses only synthetic images:

```bash
source .venv/bin/activate
HF_HOME="$PWD/data/model-cache" TORCH_HOME="$PWD/data/torch-cache" \
  python scripts/smoke_model.py --device cpu
```

For real photos, start with the controlled manual tests in `DEVICE_TEST_PLAN.md`.
