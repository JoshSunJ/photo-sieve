import http.client
import json
import threading
import unittest

from photosieve.contracts import MAX_BODY_BYTES, rank_scores
from photosieve.server import SieveServer

TOKEN = "test-only-token-not-a-real-secret"


class FakeScorer:
    def __init__(self):
        self.calls = 0

    def score(self, request):
        self.calls += 1
        return {
            **rank_scores(
                request.prompts, [0.4] * len(request.prompts), [], request.threshold, request.margin
            ),
            "model": "test-only",
        }


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scorer = FakeScorer()
        cls.server = SieveServer(("127.0.0.1", 0), cls.scorer, TOKEN)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request(self, method="GET", path="/v1/health", data=None, headers=None, auth=True):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        request_headers = {"Content-Type": "application/json"}
        if auth:
            request_headers["Authorization"] = f"Bearer {TOKEN}"
        request_headers.update(headers or {})
        try:
            connection.request(method, path, data, request_headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read()), dict(response.getheaders())
        finally:
            connection.close()

    def test_pairing_required_before_scoring(self):
        before = self.scorer.calls
        status, _, _ = self.request("POST", "/v1/score", b"{}", auth=False)
        self.assertEqual(status, 401)
        self.assertEqual(self.scorer.calls, before)

    def test_health_and_no_store(self):
        status, body, headers = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ready")
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_score_round_trip(self):
        body = json.dumps({"api_version": 1, "image_base64": "aW1hZ2U=", "prompts": ["ramen"]})
        status, result, _ = self.request("POST", "/v1/score", body)
        self.assertEqual(status, 200)
        self.assertTrue(result["candidate"])
        self.assertEqual(result["best_prompt"], "ramen")

    def test_deletion_is_not_an_engine_capability(self):
        status, _, _ = self.request("POST", "/v1/delete", "{}")
        self.assertEqual(status, 404)

    def test_bad_json_and_non_object_are_rejected(self):
        for body in ["{", "[]", '{"api_version": 1}']:
            with self.subTest(body=body):
                self.assertEqual(self.request("POST", "/v1/score", body)[0], 400)

    def test_bad_content_type_and_oversized_body_are_rejected(self):
        self.assertEqual(
            self.request("POST", "/v1/score", "{}", {"Content-Type": "text/plain"})[0], 415
        )
        self.assertEqual(
            self.request("POST", "/v1/score", "{}", {"Content-Length": str(MAX_BODY_BYTES + 1)})[0],
            413,
        )

    def test_busy_engine_has_bounded_inflight_requests(self):
        self.server.slots.acquire()
        self.server.slots.acquire()
        try:
            self.assertEqual(self.request("POST", "/v1/score", "{}")[0], 429)
        finally:
            self.server.slots.release()
            self.server.slots.release()


if __name__ == "__main__":
    unittest.main()
