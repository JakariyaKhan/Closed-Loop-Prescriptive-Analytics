# Supply Prescript: Closed-Loop Prescriptive Analytics

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost-orange.svg)](https://xgboost.readthedocs.io/)
[![PuLP OR](https://img.shields.io/badge/Operations_Research-PuLP_MILP-green.svg)](https://coin-or.github.io/pulp/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit_Clean-red.svg)](https://streamlit.io/)
[![FastAPI](https://img.shields.io/badge/Write--Back-FastAPI_ACID-teal.svg)](https://fastapi.tiangolo.com/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://jakariyakhan-closed-loop-prescriptive-anal-streamlit-app-ot2bxl.streamlit.app/)

**Project 3** from the Advanced Data Analytics enterprise architecture portfolio: **"Supply Prescript" - Closed-Loop Prescriptive Analytics**.

> 🌐 **Live Interactive App**: [https://jakariyakhan-closed-loop-prescriptive-anal-streamlit-app-ot2bxl.streamlit.app/](https://jakariyakhan-closed-loop-prescriptive-anal-streamlit-app-ot2bxl.streamlit.app/)

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

### 🌐 Access Live Cloud App
Access the deployed live application instantly in your browser:
👉 **[https://jakariyakhan-closed-loop-prescriptive-anal-streamlit-app-ot2bxl.streamlit.app/](https://jakariyakhan-closed-loop-prescriptive-anal-streamlit-app-ot2bxl.streamlit.app/)**

### 1. Launch the Clean & Modern Operational UI (Local)
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
python tests/test_pipeline.py
```

---

## 💻 Interface Walkthrough: Streamlined 2-Tab Decision Desk

The user interface has been refined into a minimalist, clutter-free operational desk designed for high-throughput decision-making:

### 1. ⚡ Decision Desk (Predict & Prescribe)
- **Minimalist Header & System Status**: Clean top bar with live system status badge, active model version, and INR (₹) currency alignment.
- **Top Operational KPI Cards**: 4 high-contrast cards tracking monitored fleet count, at-risk shipments requiring intervention, total financial loss prevented, and realized Decision ROI.
- **Single-Strip Unified Triage**: Streamlined control bar combining **Risk Tier Filter**, **Category Filter**, **Shipment Selector**, and **Budget Cap (₹)** in a single cohesive row.
- **At-a-Glance Shipment Summary Profile**: Clean card presenting shipment ID, risk tier badge, current state, order total in INR (₹), predicted delay, and disruption probability.
- **High-Contrast Prescriptive Decision Tiles**:
  - **Recommended Action Spotlight**: The optimal MILP prescription is highlighted with clear visual priority and a `★ RECOMMENDED` badge.
  - **Net Financial Benefit & ROI**: Clear hero metrics displaying net savings (+₹) and projected ROI (%) directly up front.
  - **2x2 Feasibility Grid**: Side-by-side comparison of expedite cost, days saved, SLA adherence rate, and budget feasibility.
  - **1-Click Transactional Execution**: Direct write-back button executing the chosen action and mutating shipment status in SQLite.
- **⚡ Fleet Portfolio Batch Optimizer**: Formulates and solves a multi-shipment MILP knapsack allocation across high-risk cohorts under a unified corporate budget limit.
- **Collapsible Monitored Inventory**: Clean table view with 1-click CSV export (`monitored_shipments.csv`).

### 2. 📈 Performance & Closed-Loop ROI
- **Realized Outcome Evaluation**: 1-click sync comparing quoted costs to realized carrier invoices (surcharges, actual arrival times).
- **Automated Model Recalibration**: 1-click model update incorporating closed-loop operational feedback into upstream ML models.
- **Polished Minimalist Visualizations**:
  - Quoted vs. Realized Expediting Cost (₹) tracking carrier surcharge deviations.
  - Average Realized Decision ROI (%) stratified by Intervention Strategy.
- **Outcomes Ledger & Audit Proof**: Clean tabular outcome registry with CSV download, plus mathematical compliance proof confirming 100% hard constraint adherence.

---

## 🧪 Verification & Test Results

```
Ran 7 tests in 1.091s
OK
- test_01_predictive_model_loaded: PASSED (ROC-AUC > 0.65, MAE < 2.0 days)
- test_02_prescriptive_solver_logic: PASSED (Top 3 Pareto options generated, budget constraints enforced)
- test_03_optimization_audit_hard_constraint: PASSED (100% compliance rate, 0 violations across randomized trials)
- test_04_transactional_writeback: PASSED (ACID insert into decision_log & status mutated)
- test_05_closed_loop_evaluation: PASSED (Outcome evaluation & Decision ROI computed)
- test_06_portfolio_optimization_solver: PASSED (Fleet-wide MILP allocation under unified budget cap)
- test_07_portfolio_zero_budget_fallback: PASSED (Zero-budget default to Status Quo with zero spend)
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
