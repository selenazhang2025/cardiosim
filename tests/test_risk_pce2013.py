import unittest
from dataclasses import FrozenInstanceError

from risk_pce2013 import RiskInputs, compute_10y_ascvd_pce2013


def inputs(*, age=55, sex="female", race="white_or_other", **overrides):
    values = {
        "age_years": age,
        "sex": sex,
        "race": race,
        "total_chol_mgdl": 213,
        "hdl_mgdl": 50,
        "sbp_mmhg": 120,
        "on_bp_meds": False,
        "smoker": False,
        "diabetes": False,
    }
    values.update(overrides)
    return RiskInputs(**values)


class RiskEquationTests(unittest.TestCase):
    def test_rejects_ages_below_and_above_supported_range(self):
        for age in (39, 80):
            with self.subTest(age=age):
                self.assertIsNone(compute_10y_ascvd_pce2013(inputs(age=age)).risk_pct_10y)

    def test_accepts_inclusive_age_boundaries(self):
        for age in (40, 79):
            with self.subTest(age=age):
                self.assertIsNotNone(compute_10y_ascvd_pce2013(inputs(age=age)).risk_pct_10y)

    def test_selects_each_cohort_equation(self):
        expected_groups = {
            ("female", "black"): "black_female",
            ("female", "white_or_other"): "white_female",
            ("male", "black"): "black_male",
            ("male", "white_or_other"): "white_male",
        }
        for (sex, race), expected_group in expected_groups.items():
            with self.subTest(sex=sex, race=race):
                result = compute_10y_ascvd_pce2013(inputs(sex=sex, race=race))
                self.assertEqual(result.details["group"], expected_group)
                self.assertGreaterEqual(result.risk_pct_10y, 0.0)
                self.assertLessEqual(result.risk_pct_10y, 100.0)

    def test_typical_case_regression_value(self):
        result = compute_10y_ascvd_pce2013(inputs())
        self.assertEqual(result.risk_pct_10y, 2.1)

    def test_result_contains_model_metadata(self):
        result = compute_10y_ascvd_pce2013(inputs())
        self.assertEqual(
            set(result.details), {"group", "linear_predictor", "s0", "mean"}
        )

    def test_inputs_are_immutable(self):
        case = inputs()
        with self.assertRaises(FrozenInstanceError):
            case.smoker = True


if __name__ == "__main__":
    unittest.main()
