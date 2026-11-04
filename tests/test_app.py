import json
import os
import threading
import unittest
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import app


class CoreTests(unittest.TestCase):
    def test_extracts_factual_sentences_and_respects_limit(self):
        text = "The Apollo 11 mission landed on the Moon in 1969. This is a short fragment. The mission lasted eight days and brought three astronauts home."
        claims = app.extract_claims(text, limit=1)
        self.assertEqual(len(claims), 1)
        self.assertIn("1969", claims[0])

    def test_freshness_uses_age_and_missing_dates_are_explicit(self):
        now = datetime(2026, 11, 4, tzinfo=timezone.utc)
        score, label, age = app.freshness({"published_date": "2026-11-03T00:00:00Z"}, now)
        self.assertEqual((label, age), ("1 day ago", 1))
        self.assertGreater(score, 90)
        self.assertEqual(app.freshness({}, now), (45, "Date unavailable", None))

    def test_unsupported_results_are_flagged(self):
        result = app.analyze_claim("The moon is made of cheese according to records.", [], demo=False)
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["freshness_score"], 16)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def post(self, value):
        req = Request(self.url + "/api/analyze", data=json.dumps(value).encode(), headers={"Content-Type":"application/json"}, method="POST")
        return urlopen(req)

    def test_rejects_empty_answer(self):
        with self.assertRaises(HTTPError) as caught:
            self.post({"answer":"  "})
        self.assertEqual(caught.exception.code, 400)

    def test_no_key_mode_returns_clearly_labeled_demo(self):
        previous_tavily = os.environ.pop("TAVILY_API_KEY", None)
        previous_bifrost = os.environ.pop("BIFROST_BASE_URL", None)
        try:
            response = self.post({"answer":"The Apollo 11 mission landed on the Moon in 1969."})
            payload = json.loads(response.read())
            self.assertEqual(payload["search_mode"], "demo")
            self.assertIsNone(payload["overall_score"])
            self.assertEqual(payload["claims"][0]["status"], "demo")
        finally:
            if previous_tavily is not None: os.environ["TAVILY_API_KEY"] = previous_tavily
            if previous_bifrost is not None: os.environ["BIFROST_BASE_URL"] = previous_bifrost


if __name__ == "__main__":
    unittest.main()

