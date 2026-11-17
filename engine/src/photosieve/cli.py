import argparse
import html
import json
import secrets
import socket
from pathlib import Path

from .contracts import ScoreRequest, finite_number, prompts_from


def scan_folder(args):
    from PIL import Image, ImageOps

    from .model import ClipScorer

    root = args.folder.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Choose an image folder")
    output = args.output.resolve()
    if output.exists():
        raise ValueError("Output already exists; choose a new report folder")
    prompts = prompts_from(args.prompt, required=True)
    excludes = prompts_from(args.keep, required=False)
    threshold = finite_number(args.threshold, "threshold", -1, 1)
    margin = finite_number(args.margin, "margin", 0, 2)
    scorer = ClipScorer(args.device)
    output.mkdir(parents=True)
    (output / "thumbnails").mkdir()
    rows, skipped = [], []
    suffixes = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or path.suffix.lower() not in suffixes or not path.is_file():
            continue
        if output == path or output in path.parents:
            continue
        try:
            import io

            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((768, 768))
                buffer = io.BytesIO()
                image.save(buffer, "JPEG", quality=80)
            data = buffer.getvalue()
            result = scorer.score(ScoreRequest(data, prompts, excludes, threshold, margin))
            name = f"{len(rows):06d}.jpg"
            (output / "thumbnails" / name).write_bytes(data)
            rows.append({"path": str(path), "thumbnail": f"thumbnails/{name}", **result})
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            skipped.append({"path": str(path), "reason": str(exc)})
    rows.sort(key=lambda row: row["score"], reverse=True)
    report = {"api_version": 1, "prompts": prompts, "results": rows, "skipped": skipped}
    (output / "results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    cards = "".join(
        '<article><img loading="lazy" src="'
        + row["thumbnail"]
        + '"><p>'
        + html.escape(Path(row["path"]).name)
        + "</p><p>"
        + html.escape(row["best_prompt"])
        + f" · {row['score']:.3f}"
        + (" · candidate" if row["candidate"] else "")
        + "</p></article>"
        for row in rows
    )
    page = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Photo Sieve review</title><style>"
        "body{font:16px system-ui;background:#101518;color:#eef5f1;padding:24px}"
        "main{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));"
        "gap:16px}article{background:#1c2823;padding:12px;border-radius:16px}"
        "img{width:100%;height:220px;object-fit:contain}p{overflow-wrap:anywhere}"
        "</style><h1>Photo Sieve</h1><p>Ranked by similarity; no files were deleted. "
        "Scores are not probabilities. This report contains private thumbnails.</p><main>"
        + cards
        + "</main></html>"
    )
    (output / "review.html").write_text(page, encoding="utf-8")
    print(f"Scored {len(rows)}; skipped {len(skipped)}. Open {output / 'review.html'}")


def main():
    parser = argparse.ArgumentParser(description="Local photo matching. No automatic deletion.")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Start the local iPhone scoring engine")
    serve.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--device", choices=["auto", "cpu", "mps"], default="auto")
    scan = commands.add_parser("scan", help="Read a folder and produce a local review report")
    scan.add_argument("folder", type=Path)
    scan.add_argument("--prompt", action="append", required=True)
    scan.add_argument("--keep", action="append", default=[])
    scan.add_argument("--threshold", type=float, default=0.25)
    scan.add_argument("--margin", type=float, default=0.02)
    scan.add_argument("--device", choices=["auto", "cpu", "mps"], default="auto")
    scan.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "scan":
            scan_folder(args)
            return
        from .model import ClipScorer
        from .server import SieveServer

        print("Loading CLIP; first launch downloads model weights, not photos.", flush=True)
        scorer = ClipScorer(args.device)
        token = secrets.token_urlsafe(24)
        with SieveServer((args.host, args.port), scorer, token) as server:
            print(f"Ready on {args.host}:{server.server_port} · device {scorer.device}")
            print(f"Pairing token (enter on your iPhone): {token}")
            print(f"Try Mac address: http://{socket.gethostname().split('.')[0]}.local:{args.port}")
            if args.host == "127.0.0.1":
                print("Loopback only. For iPhone access, restart with --host 0.0.0.0")
            else:
                print(
                    "LAN mode: use trusted private Wi-Fi. "
                    "HTTP is not encrypted. No port forwarding."
                )
            print(
                "No image files or request logs are saved. Ctrl-C stops and clears RAM.", flush=True
            )
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    except (ValueError, OSError, ImportError, RuntimeError) as exc:
        parser.exit(1, f"Photo Sieve: {exc}\n")


if __name__ == "__main__":
    main()
