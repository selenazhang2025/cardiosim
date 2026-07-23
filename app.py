
from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from risk_pce2013 import RiskInputs, compute_10y_ascvd_pce2013
from simulation import (
    apply_interventions,
    clamp,
    compute_drivers,
    compute_timeline,
    risk_or_none,
)


# -----------------------------
# Helpers
# -----------------------------
def risk_band(risk_pct: Optional[float]) -> str:
    if risk_pct is None:
        return "Out of range"
    if risk_pct < 5:
        return "Low (<5%)"
    if risk_pct < 7.5:
        return "Borderline (5–7.4%)"
    if risk_pct < 20:
        return "Intermediate (7.5–19.9%)"
    return "High (≥20%)"

def risk_style(risk_pct: Optional[float]) -> Dict[str, str]:
    if risk_pct is None:
        return {"bg": "#6b7280", "fg": "white"}  # gray
    if risk_pct < 5:
        return {"bg": "#16a34a", "fg": "white"}  # green
    if risk_pct < 7.5:
        return {"bg": "#ca8a04", "fg": "white"}  # amber
    if risk_pct < 20:
        return {"bg": "#ea580c", "fg": "white"}  # orange
    return {"bg": "#dc2626", "fg": "white"}      # red

def render_risk_badge(title: str, risk_pct: Optional[float]) -> None:
    style = risk_style(risk_pct)
    value = "—" if risk_pct is None else f"{risk_pct:.1f}%"
    band = risk_band(risk_pct)
    st.markdown(
        f"""
        <div style="border-radius:16px;padding:16px;background:{style['bg']};color:{style['fg']};">
          <div style="font-size:14px;opacity:0.95;">{title}</div>
          <div style="font-size:34px;font-weight:800;line-height:1.1;margin-top:4px;">{value}</div>
          <div style="font-size:13px;opacity:0.95;margin-top:6px;">{band}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_gauge(title: str, risk_pct: Optional[float], max_pct: float = 30.0) -> None:
    """
    Semicircle gauge rendered as raw HTML/SVG via components.html (no Markdown parsing issues).
    """
    if risk_pct is None:
        st.markdown(f"**{title}**")
        st.caption("Out of range for 10-year PCE (ages 40–79).")
        return

    pct = float(risk_pct)
    pct_clamped = clamp(pct, 0.0, max_pct)
    ratio = pct_clamped / max_pct  # 0..1
    angle = -180 + 180 * ratio

    html = f"""<!doctype html>
<html>
  <body style="margin:0;">
    <div style="border:1px solid rgba(0,0,0,0.08); border-radius:16px; padding:12px;">
      <div style="font-size:14px; margin-bottom:6px; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;">
        {title}
      </div>

      <svg width="100%" viewBox="0 0 220 140">
        <path d="M 20 120 A 90 90 0 0 1 200 120" fill="none" stroke="#e5e7eb" stroke-width="18" stroke-linecap="round"/>

        <path d="M 20 120 A 90 90 0 0 1 80 40"  fill="none" stroke="#16a34a" stroke-width="18" stroke-linecap="round"/>
        <path d="M 80 40  A 90 90 0 0 1 110 30" fill="none" stroke="#ca8a04" stroke-width="18" stroke-linecap="round"/>
        <path d="M 110 30 A 90 90 0 0 1 170 55" fill="none" stroke="#ea580c" stroke-width="18" stroke-linecap="round"/>
        <path d="M 170 55 A 90 90 0 0 1 200 120" fill="none" stroke="#dc2626" stroke-width="18" stroke-linecap="round"/>

        <g transform="translate(110,120) rotate({angle})">
          <line x1="0" y1="0" x2="80" y2="0" stroke="#111827" stroke-width="4" stroke-linecap="round"/>
          <circle cx="0" cy="0" r="7" fill="#111827"/>
        </g>

        <text x="20"  y="135" font-size="10" fill="#6b7280">0%</text>
        <text x="196" y="135" font-size="10" fill="#6b7280">{max_pct:.0f}%+</text>

        <text x="110" y="80"  text-anchor="middle" font-size="22" font-weight="700" fill="#111827">{pct:.1f}%</text>
        <text x="110" y="102" text-anchor="middle" font-size="11" fill="#6b7280">{risk_band(pct)}</text>
      </svg>
    </div>
  </body>
</html>
"""
    st.html(html)

# -----------------------------
# Streamlit setup
# -----------------------------
st.set_page_config(page_title="CardioSim (10-year ASCVD)", layout="wide")

st.title("CardioSim — 10-year ASCVD Risk Simulator")
st.caption("Educational only. Not medical advice. Uses ACC/AHA Pooled Cohort Equations (2013) for ages 40–79.")

TYPICAL = RiskInputs(
    age_years=55,
    sex="female",
    race="white_or_other",
    total_chol_mgdl=213,
    hdl_mgdl=50,
    sbp_mmhg=120,
    on_bp_meds=False,
    smoker=False,
    diabetes=False,
)

HIGH_RISK = RiskInputs(
    age_years=60,
    sex="male",
    race="white_or_other",
    total_chol_mgdl=260,
    hdl_mgdl=38,
    sbp_mmhg=155,
    on_bp_meds=False,
    smoker=True,
    diabetes=False,
)

if "base_inputs" not in st.session_state:
    st.session_state.base_inputs = asdict(TYPICAL)

if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = []


colL, colR = st.columns([1, 1.15], gap="large")

with colL:
    st.subheader("Quick presets (for smooth demo)")
    p1, p2, p3 = st.columns(3)
    if p1.button("Typical"):
        st.session_state.base_inputs = asdict(TYPICAL)
    if p2.button("High-risk"):
        st.session_state.base_inputs = asdict(HIGH_RISK)
    if p3.button("Reset"):
        st.session_state.base_inputs = asdict(TYPICAL)

    st.divider()
    st.subheader("Baseline inputs")

    base_dict = dict(st.session_state.base_inputs)

    age = st.slider("Age (years) — intended 40–79", 20, 90, int(base_dict["age_years"]))
    sex = st.selectbox("Sex", ["female", "male"], index=0 if base_dict["sex"] == "female" else 1)
    race_display = st.selectbox(
        "Race (PCE supports Black vs White/Other)",
        ["White / Other", "Black"],
        index=0 if base_dict["race"] == "white_or_other" else 1,
    )

    race = "white_or_other" if race_display == "White / Other" else "black"

    st.markdown("**Labs & vitals**")
    tc = st.slider("Total cholesterol (mg/dL)", 130, 320, int(base_dict["total_chol_mgdl"]))
    hdl = st.slider("HDL (mg/dL)", 20, 100, int(base_dict["hdl_mgdl"]))
    sbp = st.slider("Systolic BP (mmHg)", 90, 200, int(base_dict["sbp_mmhg"]))
    on_meds = st.checkbox("On BP medication", value=bool(base_dict["on_bp_meds"]))

    st.markdown("**Conditions**")
    smoker = st.checkbox("Current smoker", value=bool(base_dict["smoker"]))
    diabetes = st.checkbox("Diabetes", value=bool(base_dict["diabetes"]))

    base = RiskInputs(
        age_years=float(age),
        sex=sex,     # type: ignore
        race=race,   # type: ignore
        total_chol_mgdl=float(tc),
        hdl_mgdl=float(hdl),
        sbp_mmhg=float(sbp),
        on_bp_meds=bool(on_meds),
        smoker=bool(smoker),
        diabetes=bool(diabetes),
    )
    st.session_state.base_inputs = asdict(base)

    st.divider()
    st.subheader("What-if interventions (scenario)")

    quit_smoking = st.checkbox("Quit smoking (what-if)", value=False)
    start_bp_meds = st.checkbox("Start BP meds (what-if)", value=False)

    sbp_target_on = st.checkbox("Set SBP target (what-if)", value=True)
    sbp_target = None
    if sbp_target_on:
        sbp_target = st.slider("Target SBP (mmHg)", 90, 200, int(base.sbp_mmhg))

    cA, cB = st.columns(2)
    with cA:
        tc_delta = st.slider("Change total cholesterol (mg/dL)", -80, 80, 0, step=5)
    with cB:
        hdl_delta = st.slider("Change HDL (mg/dL)", -20, 20, 0, step=1)

    iv = {
        "quit_smoking": quit_smoking,
        "start_bp_meds": start_bp_meds,
        "sbp_target": float(sbp_target) if sbp_target is not None else None,
        "tc_delta": float(tc_delta),
        "hdl_delta": float(hdl_delta),
    }

    scenario = apply_interventions(base, iv)

    st.divider()
    st.subheader("Save scenario")
    scenario_name = st.text_input("Scenario name", value="My plan")
    if st.button("Save this scenario"):
        st.session_state.saved_scenarios.append(
            {"name": scenario_name, "baseline": asdict(base), "scenario": asdict(scenario), "iv": iv}
        )
        st.success("Saved!")

with colR:
    st.subheader("Results")

    base_r = compute_10y_ascvd_pce2013(base).risk_pct_10y
    scen_r = compute_10y_ascvd_pce2013(scenario).risk_pct_10y

    # Gauges first (looks impressive)
    g1, g2 = st.columns(2)
    with g1:
        render_gauge("Baseline 10-year risk (dial)", base_r, max_pct=30.0)
    with g2:
        render_gauge("Scenario 10-year risk (dial)", scen_r, max_pct=30.0)

    # Badges + delta
    st.markdown("#### Summary")
    r1, r2, r3 = st.columns(3)
    with r1:
        render_risk_badge("Baseline 10-year risk", base_r)
    with r2:
        render_risk_badge("Scenario 10-year risk", scen_r)
    with r3:
        with r3:
            if base_r is None or scen_r is None:
                render_risk_badge("Δ Risk (Scenario − Baseline)", None)
            else:
                delta = round(scen_r - base_r, 1)
                render_risk_badge("Δ Risk (Scenario − Baseline)", delta)

    if base_r is None or scen_r is None:
        st.warning("The 10-year PCE calculation is intended for ages 40–79. Adjust age to see results.")
    else:
        df = pd.DataFrame({"Case": ["Baseline", "Scenario"], "10y_risk_pct": [base_r, scen_r]})
        st.bar_chart(df.set_index("Case"))

        st.markdown("### What changed the risk the most (approx.)")
        drivers = compute_drivers(base, scenario)
        if not drivers:
            st.write("No changes detected.")
        else:
            for name, contrib in drivers[:5]:
                st.write(f"- **{name}**: {contrib:+.2f}% (scenario − baseline)")

        st.divider()
        st.markdown("### Timeline projection (demo mode)")
        months = st.slider("Months to reach scenario", 1, 24, 6)
        timeline = pd.DataFrame(compute_timeline(base, scenario, months))
        st.line_chart(timeline.set_index("month"))
        st.caption("This is a simple interpolation for visualization (not a clinical kinetics model).")

    st.divider()
    st.subheader("Saved scenarios")
    if len(st.session_state.saved_scenarios) == 0:
        st.caption("No saved scenarios yet.")
    else:
        rows = []
        for item in st.session_state.saved_scenarios:
            b = RiskInputs(**item["baseline"])
            s = RiskInputs(**item["scenario"])
            br = risk_or_none(b)
            sr = risk_or_none(s)
            rows.append(
                {
                    "name": item["name"],
                    "baseline_%": br,
                    "scenario_%": sr,
                    "delta_%": (None if br is None or sr is None else round(sr - br, 1)),
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        cX, cY = st.columns([1, 1])
        with cX:
            if st.button("Clear saved scenarios"):
                st.session_state.saved_scenarios = []
                st.success("Cleared.")
        with cY:
            export_df = pd.DataFrame(rows)
            st.download_button(
                "Download scenarios CSV",
                data=export_df.to_csv(index=False).encode("utf-8"),
                file_name="cardiosim_scenarios.csv",
                mime="text/csv",
            )

st.divider()
st.markdown(
    """
### Important notes
- This is an educational simulator — not medical advice.
- The **Pooled Cohort Equations (2013)** are intended for **ages 40–79**.
- The original model includes a race input (**Black vs White/Other**) because that is how the equations were constructed.
  This reflects model design and population-level calibration — **not** biological determinism.
- Future versions of CardioSim can explore updated, more inclusive models and calibration strategies.
"""
)
