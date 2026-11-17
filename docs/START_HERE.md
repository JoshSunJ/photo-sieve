# Your first sessions with Photo Sieve

The goal is to learn how an ML feature becomes a dependable software product.
Work in small vertical slices: input → useful output → check the behavior.
Don't build every layer in isolation and hope they integrate at the end.

## Session 1 · Run code without touching your library

1. Follow the README to activate `.venv` and install the engine.
2. Run `make test` (or `PYTHONPATH=engine/src python -m unittest discover -s engine/tests -v`
   if Xcode setup blocks Apple's `make`). These tests use a fake scorer, so they do not download a
   model or access your photos. Read `test_contracts.py` beside `contracts.py`.
3. Place 10–20 disposable images in `data/inbox/`. Include desired matches and
   visually similar nonmatches: ramen, spaghetti, soup, menus, and screenshots.
4. Run the README's folder scan. Open its HTML report and inspect the ranking.
5. Repeat with a different output folder and one changed description.

**Before running:** predict which image should rank first and why. **After
running:** write down one false positive and one false negative. A program can
execute correctly while its model makes poor decisions. These are different
kinds of quality.

Small exercise: change the candidate policy to require two include descriptions
instead of any one. First write the desired input/output example as a test.
Make it pass on a branch, then discard or keep the experiment deliberately.

## Session 2 · Trace one photo through the system

Read these in order:

1. `PhotoLibrary.thumbnail`: PhotoKit asset → image → JPEG bytes.
2. `EngineClient.score`: bytes + descriptions → versioned JSON request.
3. `server.Handler.do_POST`: authentication → bounded input → validation.
4. `ClipScorer.score`: image/text → normalized vectors → similarity values.
5. `rank_scores`: similarities → candidate suggestion.
6. `ScanViewModel.start`: response → ranked preview state.
7. `ContentView.review`: state → visible cards and manual selection.
8. `PhotoLibrary.delete`: selected local IDs → PhotoKit change request.

Notice the Mac never receives the local IDs and cannot trigger step 8. The ML
process has only the permission to propose a score. That's an architecture
decision, not just a warning in the UI.

Exercise: explain where each of these belongs before editing anything:

| Change | Likely home |
| --- | --- |
| Reject descriptions longer than 240 characters | Engine contracts and matching client validation |
| Change the model checkpoint | Model adapter and model metadata |
| Add an album picker | PhotoKit adapter and UI/orchestration |
| Change a card's spacing | SwiftUI view |
| Change candidate policy | Pure ranking function + policy tests |
| Retry a dropped scoring request | Network/orchestration layer |

## Session 3 · Run the native app on test assets

1. Open the Xcode project and complete the README signing steps.
2. Run the Mac engine in LAN mode and pair the app.
3. Start with limited Photos access to disposable test images.
4. Scan 100 assets. Inspect the progress counts and candidate filter.
5. Select one disposable image. Cancel the app's confirmation. Verify it remains.
6. Repeat and cancel Apple's deletion prompt. Verify it remains again.
7. Repeat and approve. Verify it disappears, then recover it in Recently Deleted.

Perform every check in `DEVICE_TEST_PLAN.md` before using a real library. No
automated test of Python code can prove that Apple's device permissions and
deletion flows work as intended.

## Session 4 · Make a small product improvement

Choose **one** issue. Good first issues:

- Add a large preview sheet with an explicit Select button.
- Make the progress copy distinguish "waiting for Mac" from "fetching thumbnail".
- Add a "ramen" preset that fills descriptions but does not select any results.
- Show the model name in an About screen.

Use this workflow:

```bash
git switch -c feat/large-preview
# edit one useful slice, then inspect your diff
git diff
make check
.venv/bin/ruff check engine/src engine/tests
git add ios/PhotoSieve/ContentView.swift
git commit -m "Add a larger preview before selecting photos"
git push -u origin feat/large-preview
```

Open a pull request with: what behavior changed, why it matters, how you tested
it, and what remains uncertain. Do not say "tested" when you only read code.
Distinguish automated checks, simulator runs, and physical-device tests.

## Questions you should be able to answer

- Why is a similarity score not a probability?
- Why doesn't the server have a delete route?
- What happens if Photos permission changes during a scan?
- What happens if the phone loses Wi-Fi after 37 photos?
- What data persists after the app or engine exits?
- Why can a keep description fail to protect a photo?
- How would a model upgrade affect cached vectors and thresholds?
- What evidence would justify moving from 100 test photos to a whole library?

If you can explain those in your own words, you understand more than the syntax.
Continue with `DESIGN_AND_WORKFLOW.md` for the reasoning behind the product.
