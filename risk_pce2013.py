from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any

Sex = Literal["female", "male"]
Race = Literal["black", "white_or_other"]

@dataclass(frozen=True)
class RiskInputs:
    age_years: float           # intended 40–79 for 10-year PCE
    sex: Sex
    race: Race

    total_chol_mgdl: float
    hdl_mgdl: float
    sbp_mmhg: float
    on_bp_meds: bool

    smoker: bool
    diabetes: bool

@dataclass(frozen=True)
class RiskResult:
    risk_pct_10y: Optional[float]   # None if age outside 40–79
    details: Optional[Dict[str, Any]] = None

def _round1(x: float) -> float:
    return round(x, 1)

def compute_10y_ascvd_pce2013(inp: RiskInputs) -> RiskResult:
    # PCE 10-year risk is defined/validated for ages 40–79
    if inp.age_years < 40 or inp.age_years > 79:
        return RiskResult(risk_pct_10y=None, details=None)

    ln_age = math.log(inp.age_years)
    ln_tc = math.log(inp.total_chol_mgdl)
    ln_hdl = math.log(inp.hdl_mgdl)

    # Treated vs untreated SBP handling
    tr_ln_sbp = math.log(inp.sbp_mmhg) if inp.on_bp_meds else 0.0
    nt_ln_sbp = 0.0 if inp.on_bp_meds else math.log(inp.sbp_mmhg)

    age_tc = ln_age * ln_tc
    age_hdl = ln_age * ln_hdl
    age_tr_sbp = ln_age * tr_ln_sbp
    age_nt_sbp = ln_age * nt_ln_sbp
    age_smoke = ln_age if inp.smoker else 0.0

    is_black = inp.race == "black"
    is_male = inp.sex == "male"

    # Risk = 1 - S0 ** exp(lp - mean)
    if is_black and not is_male:
        group = "black_female"
        s0 = 0.95334
        mean = 86.6081
        lp = (
            17.1141 * ln_age
            + 0.9396 * ln_tc
            - 18.9196 * ln_hdl
            + 4.4748 * age_hdl
            + 29.2907 * tr_ln_sbp
            - 6.4321 * age_tr_sbp
            + 27.8197 * nt_ln_sbp
            - 6.0873 * age_nt_sbp
            + 0.6908 * (1.0 if inp.smoker else 0.0)
            + 0.8738 * (1.0 if inp.diabetes else 0.0)
        )
    elif (not is_black) and (not is_male):
        group = "white_female"
        s0 = 0.96652
        mean = -29.1817
        lp = (
            -29.799 * ln_age
            + 4.884 * (ln_age ** 2)
            + 13.54 * ln_tc
            - 3.114 * age_tc
            - 13.578 * ln_hdl
            + 3.149 * age_hdl
            + 2.019 * tr_ln_sbp
            + 1.957 * nt_ln_sbp
            + 7.574 * (1.0 if inp.smoker else 0.0)
            - 1.665 * age_smoke
            + 0.661 * (1.0 if inp.diabetes else 0.0)
        )
    elif is_black and is_male:
        group = "black_male"
        s0 = 0.89536
        mean = 19.5425
        lp = (
            2.469 * ln_age
            + 0.302 * ln_tc
            - 0.307 * ln_hdl
            + 1.916 * tr_ln_sbp
            + 1.809 * nt_ln_sbp
            + 0.549 * (1.0 if inp.smoker else 0.0)
            + 0.645 * (1.0 if inp.diabetes else 0.0)
        )
    else:
        group = "white_male"
        s0 = 0.91436
        mean = 61.1816
        lp = (
            12.344 * ln_age
            + 11.853 * ln_tc
            - 2.664 * age_tc
            - 7.99 * ln_hdl
            + 1.769 * age_hdl
            + 1.797 * tr_ln_sbp
            + 1.764 * nt_ln_sbp
            + 7.837 * (1.0 if inp.smoker else 0.0)
            - 1.795 * age_smoke
            + 0.658 * (1.0 if inp.diabetes else 0.0)
        )

    risk = 1.0 - (s0 ** math.exp(lp - mean))
    risk_pct = _round1(100.0 * risk)

    return RiskResult(
        risk_pct_10y=risk_pct,
        details={"group": group, "linear_predictor": lp, "s0": s0, "mean": mean},
    )