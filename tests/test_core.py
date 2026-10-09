import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retry import with_retry, RateLimiter
from schemas import ExtractedCompany, CATEGORIES, SELLS_TO


class TestRetry(unittest.TestCase):
    def test_retries_then_succeeds(self):
        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise TimeoutError("boom")
            return "ok"

        self.assertEqual(with_retry(flaky, tries=3, base=0.0), "ok")
        self.assertEqual(calls["n"], 3)

    def test_raises_after_budget(self):
        def always():
            raise TimeoutError("boom")
        with self.assertRaises(TimeoutError):
            with_retry(always, tries=2, base=0.0)


class TestSchemas(unittest.TestCase):
    def test_valid_company(self):
        c = ExtractedCompany("Vercel", category="dev_tools", sells_to="businesses")
        self.assertEqual(c.validate(), [])

    def test_bad_values_are_caught(self):
        c = ExtractedCompany("X", category="not_a_category", sells_to="aliens")
        self.assertEqual(len(c.validate()), 2)

    def test_unknown_is_valid_in_both(self):
        self.assertIn("unknown", CATEGORIES)
        self.assertIn("unknown", SELLS_TO)


if __name__ == "__main__":
    unittest.main()
