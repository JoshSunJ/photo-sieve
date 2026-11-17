import base64
import unittest

from photosieve.contracts import MAX_IMAGE_BYTES, parse_request, rank_scores


def payload(**changes):
    data = {
        "api_version": 1,
        "image_base64": base64.b64encode(b"test-image").decode(),
        "prompts": ["ramen"],
    }
    return {**data, **changes}


class ContractTests(unittest.TestCase):
    def test_multiple_descriptions_are_or_and_keep_has_margin(self):
        result = rank_scores(("ramen", "beach"), [0.1, 0.4], [0.39], 0.25, 0.02)
        self.assertEqual(result["best_prompt"], "beach")
        self.assertFalse(result["candidate"])
        self.assertTrue(rank_scores(("ramen",), [0.4], [], 0.25, 0.02)["candidate"])

    def test_threshold_is_required_even_without_keep(self):
        self.assertFalse(rank_scores(("ramen",), [0.1], [], 0.25, 0)["candidate"])

    def test_prompts_are_trimmed_and_deduplicated(self):
        request = parse_request(payload(prompts=[" ramen ", "", "ramen"]))
        self.assertEqual(request.prompts, ("ramen",))

    def test_rejects_invalid_inputs(self):
        invalid = [
            payload(api_version=2),
            payload(prompts=[]),
            payload(prompts="ramen"),
            payload(prompts=[123]),
            payload(prompts=["a" * 241]),
            payload(prompts=[str(n) for n in range(13)]),
            payload(threshold=float("nan")),
            payload(threshold=True),
            payload(threshold=2),
            payload(margin=-1),
            payload(margin="0.2"),
            payload(image_base64="not base64!"),
            payload(image_base64=""),
            payload(image_base64="a" * (MAX_IMAGE_BYTES * 2)),
            payload(exclude_prompts=None),
            [],
            None,
        ]
        for item in invalid:
            with self.subTest(item=str(item)[:80]), self.assertRaises(ValueError):
                parse_request(item)

    def test_rejects_nonfinite_model_output(self):
        with self.assertRaises(ValueError):
            rank_scores(("ramen",), [float("nan")], [], 0.25, 0.02)


if __name__ == "__main__":
    unittest.main()
