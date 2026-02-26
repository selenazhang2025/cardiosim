# CardioSim — 10-Year ASCVD Risk Simulator

CardioSim is an interactive cardiovascular risk simulator built using the 2013 ACC/AHA Pooled Cohort Equations.

## Features
- Real 10-year ASCVD risk calculation
- Interactive lifestyle intervention simulation
- Dial-based risk visualization
- Timeline projection
- Scenario comparison and export

## Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py