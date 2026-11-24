"""Regression for Markdown wrappers, malformed plans and minimum-edit scoring."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "planner_parity", ROOT / "scripts/submission/rescore_deepseek_planner_parity.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ParsingParityChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api, _, parser = module.components(ROOT)
        cls.parser = staticmethod(parser)
        with (ROOT / "data/processed_v5/dev.jsonl").open(encoding="utf-8") as f:
            cls.row = json.loads(next(f))

    def test_single_fence_changes_only_wrapper(self):
        actions = self.row["witness_plan"]
        raw = json.dumps(actions)
        fenced = "```json\n" + raw + "\n```"
        self.assertIsNone(module.parse_actions(fenced, self.row["task"], "strict_json", self.parser))
        for mode in ("single_fence", "e2_shared"):
            self.assertEqual(module.parse_actions(fenced, self.row["task"], mode, self.parser), actions)
        self.assertEqual(self.parser(raw, self.row), self.parser(fenced, self.row))

    def test_missing_unknown_duplicate_and_truncated_remain_invalid(self):
        actions = self.row["witness_plan"]
        cases = [actions * 2, ["unavailable_tool"], actions[:-1], []]
        for candidate in cases:
            text = "```json\n" + json.dumps(candidate) + "\n```"
            result = module.parse_actions(text, self.row["task"], "e2_shared", self.parser)
            self.assertFalse(self.api.outcome(self.row, result)["valid"])
        self.assertIsNone(module.parse_actions('["unfinished', self.row["task"], "e2_shared", self.parser))

    def test_shared_parser_receives_public_task_only(self):
        observed = []
        def spy(raw, row):
            observed.append(set(row))
            return self.parser(raw, row)
        raw = json.dumps(self.row["witness_plan"])
        self.assertEqual(module.parse_actions(raw, self.row["task"], "e2_shared", spy), self.row["witness_plan"])
        self.assertEqual(observed, [{"task"}])

    def test_safe_unnecessary_edit_is_not_faithful_for_none(self):
        row = dict(self.row, gold={"constraints": []})
        actions = self.api.default_plan(row["task"])
        stage = row["task"]["stages"][0]
        actions[0] = next(r for r in stage["alternatives"] if r != stage["default"])
        raw = "```json\n" + json.dumps(actions) + "\n```"
        result = self.api.outcome(row, module.parse_actions(raw, row["task"], "e2_shared", self.parser))
        self.assertTrue(result["valid"])
        self.assertTrue(result["safe"])
        self.assertTrue(result["deviates"])
        self.assertFalse(result["faithful"])


if __name__ == "__main__":
    unittest.main()
