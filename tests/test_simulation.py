import unittest

from risk_pce2013 import RiskInputs
from simulation import apply_interventions, compute_drivers, compute_timeline


def baseline(**overrides):
    values = {
        "age_years": 60,
        "sex": "male",
        "race": "white_or_other",
        "total_chol_mgdl": 260,
        "hdl_mgdl": 38,
        "sbp_mmhg": 155,
        "on_bp_meds": False,
        "smoker": True,
        "diabetes": False,
    }
    values.update(overrides)
    return RiskInputs(**values)


class InterventionTests(unittest.TestCase):
    def test_applies_all_interventions_without_mutating_baseline(self):
        original = baseline()
        scenario = apply_interventions(
            original,
            {
                "quit_smoking": True,
                "start_bp_meds": True,
                "sbp_target": 125,
                "tc_delta": -40,
                "hdl_delta": 12,
            },
        )
        self.assertTrue(original.smoker)
        self.assertFalse(original.on_bp_meds)
        self.assertEqual(original.sbp_mmhg, 155)
        self.assertFalse(scenario.smoker)
        self.assertTrue(scenario.on_bp_meds)
        self.assertEqual(scenario.sbp_mmhg, 125)
        self.assertEqual(scenario.total_chol_mgdl, 220)
        self.assertEqual(scenario.hdl_mgdl, 50)

    def test_clamps_numeric_interventions(self):
        scenario = apply_interventions(
            baseline(), {"sbp_target": 500, "tc_delta": 500, "hdl_delta": -500}
        )
        self.assertEqual(scenario.sbp_mmhg, 200)
        self.assertEqual(scenario.total_chol_mgdl, 320)
        self.assertEqual(scenario.hdl_mgdl, 20)

    def test_ignores_non_numeric_interventions(self):
        original = baseline()
        scenario = apply_interventions(
            original, {"sbp_target": "120", "tc_delta": None, "hdl_delta": []}
        )
        self.assertEqual(scenario, original)


class DriverTests(unittest.TestCase):
    def test_reports_only_changed_candidate_factors(self):
        original = baseline()
        scenario = apply_interventions(
            original, {"quit_smoking": True, "tc_delta": -30}
        )
        drivers = compute_drivers(original, scenario)
        self.assertEqual({name for name, _ in drivers}, {"Smoking", "Total cholesterol"})

    def test_sorts_drivers_by_absolute_change(self):
        original = baseline()
        scenario = apply_interventions(
            original, {"quit_smoking": True, "sbp_target": 120, "hdl_delta": 15}
        )
        magnitudes = [abs(change) for _, change in compute_drivers(original, scenario)]
        self.assertEqual(magnitudes, sorted(magnitudes, reverse=True))

    def test_returns_no_drivers_for_unsupported_age(self):
        original = baseline(age_years=30)
        self.assertEqual(compute_drivers(original, original), [])


class TimelineTests(unittest.TestCase):
    def test_returns_months_plus_one_samples_with_correct_endpoints(self):
        original = baseline()
        scenario = apply_interventions(
            original, {"quit_smoking": True, "sbp_target": 120, "hdl_delta": 10}
        )
        rows = compute_timeline(original, scenario, 6)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["month"], 0)
        self.assertEqual(rows[-1]["month"], 6)

    def test_zero_month_timeline_uses_scenario(self):
        original = baseline()
        scenario = apply_interventions(original, {"quit_smoking": True})
        rows = compute_timeline(original, scenario, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["month"], 0)

    def test_rejects_negative_months(self):
        with self.assertRaisesRegex(ValueError, "months must be non-negative"):
            compute_timeline(baseline(), baseline(), -1)


if __name__ == "__main__":
    unittest.main()
