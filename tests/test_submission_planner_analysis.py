"""Protect paired grouping, missing coverage, and deduplicated usage counts."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("planner_analysis", ROOT / "scripts/submission/analyse_deepseek_planner.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    rows, responses = [], []
    for group in range(2):
        for variant in ("explicit", "implicit", "none"):
            sample = f"{group}-{variant}"
            responses.append({"request_hash": sample, "model": "fixed-model", "latency_s": 1.,
                              "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}})
            for compiler in ("1.7B-seed42", "DeepSeek-ten-shot"):
                result = {"valid": True, "safe": True, "faithful": True, "deviates": False}
                rows.append({"id": compiler + ":" + sample, "sample_id": sample, "group_id": str(group),
                             "variant": variant, "split": "dev", "compiler": compiler,
                             "request_hash": sample, "compiler_malformed": False,
                             "api": dict(result), "symbolic": dict(result)})
    config = {"requests": {r["id"]: r["request_hash"] for r in rows}, "params": {"model": "fixed-model"}}
    return config, rows, responses


class AnalysisChecks(unittest.TestCase):
    def test_incomplete_and_duplicate_cache_fail(self):
        config, rows, responses = fixture()
        module.check_coverage(config, rows, responses)
        for incomplete in (rows[:-1], rows + rows[:1]):
            with self.assertRaisesRegex(ValueError, "cohort"):
                module.check_coverage(config, incomplete, responses)
        with self.assertRaisesRegex(ValueError, "cache"):
            module.check_coverage(config, rows, responses[:-1])

    def test_group_resampling_keeps_opposing_siblings_together(self):
        result = module.paired(["a", "a", "b", "b"], [1, 0, 1, 0], [0, 1, 0, 1], reps=1000)
        self.assertEqual(result["ci95_pp"], [0., 0.])
        self.assertEqual(result["groups"], 2)

    def test_actual_and_logical_cost_are_not_conflated(self):
        _, rows, responses = fixture()
        result = module.summarise(rows, responses, reps=100)
        self.assertEqual(result["actual_unique_api_usage"]["total_tokens"]["total"], 72)
        self.assertEqual(result["logical_api_usage"]["total_tokens"]["total"], 144)
        self.assertEqual(result["paired_contrasts"]["dev"]["consumer-by-compiler-interaction"]["difference_pp"], 0)


if __name__ == "__main__":
    unittest.main()
