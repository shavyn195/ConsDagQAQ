"""Coverage and pairing tests with analytically determined observations."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("e3_analysis", ROOT / "scripts/submission/analyse_e3_ablation.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def fixture():
    rows, baseline, arm = [], [], []
    for group in ("a", "b"):
        for variant in ("explicit", "implicit", "none"):
            row = {"sample_id": group + variant, "group_id": group, "variant": variant}
            rows.append(row)
            base = dict(row, faithful_success=variant == "implicit", valid_faithful=variant == "implicit",
                        safe_success=True, valid_constraints=True, deviates_from_default=False)
            changed = dict(base, faithful_success=variant == "explicit", valid_faithful=variant == "explicit")
            baseline.append(base)
            arm.append(changed)
    return rows, arm, baseline


class AblationAnalysisChecks(unittest.TestCase):
    def test_reorder_is_allowed_but_missing_extra_and_duplicate_ids_fail(self):
        rows, _, _ = fixture()
        predictions = [{"sample_id": r["sample_id"], "raw": str(i)} for i, r in enumerate(rows)]
        self.assertEqual(analysis.align(rows, predictions[::-1]), [str(i) for i in range(6)])
        for bad in (predictions[:-1], predictions + predictions[:1], predictions + [{"sample_id": "extra", "raw": ""}]):
            with self.assertRaisesRegex(ValueError, "prediction IDs"):
                analysis.align(rows, bad)

    def test_broken_triplet_fails(self):
        rows, _, _ = fixture()
        rows[0]["variant"] = "none"
        with self.assertRaisesRegex(ValueError, "E/I/N"):
            analysis.align(rows, [{"sample_id": r["sample_id"], "raw": ""} for r in rows])

    def test_opposing_siblings_cancel_in_every_group_draw(self):
        rows, arm, baseline = fixture()
        result = analysis.contrast(rows, arm, baseline, reps=100)
        # Every E/I group has (+1,-1), so every group draw has exactly zero mean.
        cell = result["constrained"]["paired_arm_minus_baseline"]["faithful_success"]
        self.assertEqual(cell["difference_pp"], 0.)
        self.assertEqual(cell["ci95_pp"], [0., 0.])
        self.assertEqual(cell["groups"], 2)
        self.assertEqual(result["explicit"]["paired_arm_minus_baseline"]["faithful_success"]["difference_pp"], 100.)

    def test_pair_identity_mismatch_fails(self):
        rows, arm, baseline = fixture()
        arm[0]["group_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "identities"):
            analysis.contrast(rows, arm, baseline, reps=100)


if __name__ == "__main__":
    unittest.main()
