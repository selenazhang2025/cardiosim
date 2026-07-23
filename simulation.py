from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from risk_pce2013 import RiskInputs, compute_10y_ascvd_pce2013


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def risk_or_none(inp: RiskInputs) -> Optional[float]:
    return compute_10y_ascvd_pce2013(inp).risk_pct_10y


def apply_interventions(base: RiskInputs, iv: Dict[str, Any]) -> RiskInputs:
    values = asdict(base)

    if iv.get("quit_smoking", False):
        values["smoker"] = False

    if iv.get("start_bp_meds", False):
        values["on_bp_meds"] = True

    sbp_target = iv.get("sbp_target")
    if isinstance(sbp_target, (int, float)):
        values["sbp_mmhg"] = clamp(float(sbp_target), 90, 200)

    tc_delta = iv.get("tc_delta")
    if isinstance(tc_delta, (int, float)) and tc_delta != 0:
        values["total_chol_mgdl"] = clamp(
            values["total_chol_mgdl"] + float(tc_delta), 130, 320
        )

    hdl_delta = iv.get("hdl_delta")
    if isinstance(hdl_delta, (int, float)) and hdl_delta != 0:
        values["hdl_mgdl"] = clamp(values["hdl_mgdl"] + float(hdl_delta), 20, 100)

    return RiskInputs(**values)


def compute_drivers(base: RiskInputs, scenario: RiskInputs) -> List[Tuple[str, float]]:
    base_r = risk_or_none(base)
    scenario_r = risk_or_none(scenario)
    if base_r is None or scenario_r is None:
        return []

    baseline_values = asdict(base)
    scenario_values = asdict(scenario)
    candidates: List[Tuple[str, str]] = [
        ("smoker", "Smoking"),
        ("sbp_mmhg", "Systolic BP"),
        ("on_bp_meds", "BP medication"),
        ("total_chol_mgdl", "Total cholesterol"),
        ("hdl_mgdl", "HDL"),
        ("diabetes", "Diabetes"),
    ]

    changes: List[Tuple[str, float]] = []
    for key, label in candidates:
        if baseline_values[key] == scenario_values[key]:
            continue

        changed_values = dict(baseline_values)
        changed_values[key] = scenario_values[key]
        changed_risk = risk_or_none(RiskInputs(**changed_values))
        if changed_risk is not None:
            changes.append((label, changed_risk - base_r))

    changes.sort(key=lambda item: abs(item[1]), reverse=True)
    return changes


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def compute_timeline(
    base: RiskInputs, scenario: RiskInputs, months: int
) -> List[Dict[str, Optional[float]]]:
    """Interpolate scenario inputs for visualization, not clinical kinetics."""
    if months < 0:
        raise ValueError("months must be non-negative")

    rows: List[Dict[str, Optional[float]]] = []
    for month in range(months + 1):
        t = month / months if months > 0 else 1.0
        interpolated = RiskInputs(
            age_years=base.age_years,
            sex=base.sex,
            race=base.race,
            total_chol_mgdl=_lerp(
                base.total_chol_mgdl, scenario.total_chol_mgdl, t
            ),
            hdl_mgdl=_lerp(base.hdl_mgdl, scenario.hdl_mgdl, t),
            sbp_mmhg=_lerp(base.sbp_mmhg, scenario.sbp_mmhg, t),
            on_bp_meds=scenario.on_bp_meds if t >= 0.5 else base.on_bp_meds,
            smoker=scenario.smoker if t >= 0.5 else base.smoker,
            diabetes=scenario.diabetes if t >= 0.5 else base.diabetes,
        )
        rows.append({"month": month, "risk_pct_10y": risk_or_none(interpolated)})

    return rows
