#!/usr/bin/env python3
"""Opt-in real inference smoke test using generated images, never personal photos."""

import argparse
import io
import json
import math

from photosieve.contracts import ScoreRequest
from photosieve.model import ClipScorer
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["auto", "cpu", "mps"], default="auto")
    args = parser.parse_args()
    scorer = ClipScorer(args.device)
    output = {}
    for color in ["red", "blue"]:
        image = Image.new("RGB", (256, 256), color)
        buffer = io.BytesIO()
        image.save(buffer, "JPEG")
        request = ScoreRequest(
            buffer.getvalue(), ("a solid red square", "a solid blue square"), (), 0.25, 0.02
        )
        first = scorer.score(request)
        second = scorer.score(request)
        if first != second or not math.isfinite(first["score"]):
            raise RuntimeError("Inference/cached inference did not produce stable finite scores")
        output[color] = first
    try:
        scorer.score(ScoreRequest(b"not an image", ("ramen",), (), 0.25, 0.02))
    except ValueError:
        output["invalid_image"] = "rejected"
    else:
        raise RuntimeError("Invalid image was not rejected")
    output["device"] = scorer.device
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
