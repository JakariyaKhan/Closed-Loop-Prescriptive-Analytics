# Supply Prescript: Closed-Loop Prescriptive Analytics

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![PuLP OR](https://img.shields.io/badge/Operations_Research-PuLP_MILP-green.svg)](https://coin-or.github.io/pulp/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit_Clean-red.svg)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/Write--Back-FastAPI_ACID-teal.svg)](https://fastapi.tiangolo.com/)

**Project 3** from the Advanced Data Analytics enterprise architecture portfolio: **"Supply Prescript" - Closed-Loop Prescriptive Analytics**.

---

## 🎯 Executive Overview & Problem Statement

Predictive analytics (e.g. predicting supply chain delay) tell you **what will happen**, but human operators still have to figure out **what to do**. Furthermore, traditional enterprise dashboards are passive and "dead"—if an operator makes a decision, the system rarely tracks whether that decision actually worked.

**Supply Prescript** closes this loop:
1. **Predicts**: An XGBoost model flags disruption risk and estimates delay duration on active shipments.
2. **Prescribes**: An Operations Research solver (**PuLP Mixed Integer Linear Programming**) formulates business constraints (budget limits, SLA tolerances, carrier capacity) and prescribes the **Top 3 Pareto-Optimal Alternatives** (Option A: Air Freight Expedite, Option B: Secondary Supplier Hot-Transfer, Option C: Dynamic Route Buffer).
3. **Writes Back**: An operator selects an option and executes it directly from the clean UI, performing an ACID transactional write-back into the operational database.
4. **Closes the Loop**: The engine continuously tracks realized outcomes (actual freight bills, fuel surcharges, SLA adherence) against predictions, calculates **Decision ROI**, and automatically triggers model retraining and parameter recalibration.

---

## 📊 Kaggle Dataset Integration

This project is built on the gold-standard **Kaggle DataCo Smart Supply Chain Dataset** (`DataCoSupplyChainDataset.csv`).
- **Telemetry & Lead Times**: `Days for shipping (real)`, `Days for shipment (scheduled)`, `Late_delivery_risk`, `Delivery Status`, `Shipping Mode`.
- **Commercial Attributes**: `Order Region`, `Category Name`, `Customer Segment`, `Product Price`, `Order Item Total`, `Benefit per order`.
- **Feature Engineering**: Risk tiers, lead-time variance, base shipping mode risk factors, and financial disruption exposure modeling.

---

## 🏛️ System Architecture

```mermaid
graph TD
    A[Kaggle DataCo Dataset] --> B[Data Preprocessing & Feature Engineering]
    B --> C[XGBoost Predictive Baseline]
    C -->|Predicted Delay Days & Risk Tier| D[PuLP / SciPy Prescriptive Solver]
    D -->|Top 3 Pareto-Optimal Actions| E[Clean Operational UI]
    E -->|1-Click Decision Execution| F[ACID Write-Back Architecture]
    F -->|Insert / Mutate| G[(Operational SQLite DB)]
    G --> H[Closed-Loop Outcome Evaluator]
    H -->|Realized vs Predicted Variance & ROI| I[Continuous Learning Pipeline]
    I -->|Dynamic Model Retraining| C
```

---

## 🚀 Quick Start Guide

### 1. Launch the Clean & Modern Operational UI
Run the master launcher:
```bash
python run.py 1
# Or directly:
streamlit run ui/app.py
```
Open your browser at: **`http://localhost:8501`**

### 2. Launch the Transactional Write-Back REST API
```bash
python run.py 2
# Or directly:
uvicorn api.app:app --reload --port 8000
```
Interactive Swagger API docs available at: **`http://127.0.0.1:8000/docs`**

### 3. Run Automated Tests
```bash
python run.py 3
# Or directly:
python -m unittest tests/test_pipeline.py
```

---

## 💻 Interface Walkthrough & Key Tabs

### 1. 🎯 Disruption Radar (Predictive)
- Real-time fleet pipeline monitoring active shipments.
- XGBoost delay risk radar, risk tier filters (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`).
- Cargo value vs. expected delay duration exposure scatter plot.

### 2. ⚡ Prescriptive Action Center
- Select any flagged order (e.g. high-value microchips facing a 7-day delay).
- Set interactive hard business constraints:
  - **Hard Budget Limit ($)**
  - **Max Allowable SLA Delay (Days)**
- Generates **Option A**, **Option B**, and **Option C** cards with real-time trade-offs:
  - **Option A (Air Freight Expedite)**: 0.0 days delay, 99.2% SLA, expediting cost, calculated ROI.
  - **Option B (Secondary Supplier Hot-Transfer)**: 1-2 days delay, moderate cost, 91.5% SLA.
  - **Option C (Dynamic Route Buffer & Multi-Modal)**: Lowest cost, partial schedule absorption.
- **🚀 Execute Decision Button**: Performs instant write-back to the database, mutating status to `INTERVENED_OPTION_X`.

### 3. 🛡️ Optimization & Constraints Audit
- Mid-Project Review audit proof.
- Monte-Carlo testing verifying that the solver **never** recommends an action exceeding the hard budget constraint.
- Visual proof scatter plot with $y = x$ boundary showing **100% mathematical constraint compliance**.

### 4. 🔄 Closed-Loop ROI & Continuous Learning
- **Realized Outcome Evaluation**: Compares quoted intervention costs against realized bills (tracking carrier surcharges and actual arrival times).
- **Decision ROI Analytics**:
  $$\text{Decision ROI} = \frac{\text{Loss Prevented} - \text{Intervention Cost}}{\text{Intervention Cost}} \times 100\%$$
- **Continuous Learning Loop**: Retrains the XGBoost model dynamically on outcome feedback, increments model version (e.g. `v1.1.0-closed-loop`), and updates weights.

### 5. 📜 System Audit & Write-Back Log
- Immutable transactional log of all operator actions, optimization checks, and continuous learning events.

---

## 🧪 Verification & Test Results

```
Ran 5 tests in 0.903s
OK
- test_01_predictive_model_loaded: PASSED (ROC-AUC > 0.74, MAE < 0.70 days)
- test_02_prescriptive_solver_logic: PASSED (Top 3 Pareto options generated)
- test_03_optimization_audit_hard_constraint: PASSED (100% compliance rate, 0 violations)
- test_04_transactional_writeback: PASSED (ACID insert into decision_log & status mutated)
- test_05_closed_loop_evaluation: PASSED (Outcome evaluation & Decision ROI computed)
```

---

## 📁 Repository Structure

```
Closed-Loop Prescriptive Analytics/
├── api/
│   └── app.py                  # FastAPI transactional write-back & analytics API
├── data/
│   ├── download_dataset.py     # Streaming downloader for Kaggle DataCo dataset
│   ├── data_loader.py          # Feature engineering & preprocessing pipeline
│   └── supply_chain_data.csv   # Real supply chain dataset (25,000 records)
├── database/
│   ├── db_manager.py           # SQLite transactional manager & write-back functions
│   ├── seed_data.py            # Operational environment seeder
│   └── supply_prescript.db     # Transactional operational database
├── models/
│   ├── predictive_model.py     # Dual XGBoost classifier & regressor
│   ├── prescriptive_solver.py  # PuLP MILP optimization engine & audit proof
│   └── closed_loop.py          # Realized outcome evaluation & continuous learning
├── tests/
│   └── test_pipeline.py        # Automated test suite
├── ui/
│   └── app.py                  # Simple and clean modern Streamlit UI
├── README.md                   # Comprehensive system documentation
└── run.py                      # Master CLI launcher
```
