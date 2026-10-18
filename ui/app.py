"""
Supply Prescript - Streamlined Operational UI
A clean, intuitive, and modern decision desk for Supply Chain Prescriptive Analytics.
"""

import os
import sys
import time
import pandas as pd
import plotly.express as px
import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db_manager import get_connection, record_decision_writeback
from database.seed_data import seed_complete_operational_environment
from models.predictive_model import SupplyChainPredictor
from models.prescriptive_solver import PrescriptiveSolver, run_optimization_audit
from models.closed_loop import ClosedLoopEngine

# Page configuration
st.set_page_config(
    page_title="Supply Prescript | Prescriptive Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom minimalist styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; }
    
    .header-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 1.25rem;
        background: #0f172a;
        color: #ffffff;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .header-title {
        font-size: 1.2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .header-sub {
        font-size: 0.8rem;
        color: #94a3b8;
    }
    .status-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid #334155;
        color: #e2e8f0;
    }
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem 1.15rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease;
    }
    .metric-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 2px 6px 0 rgba(0, 0, 0, 0.07);
    }
    .metric-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1.2;
        color: #0f172a;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.2rem;
    }
    .shipment-summary-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0 1.25rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .summary-left {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
    }
    .summary-id-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .shipment-badge {
        font-family: monospace;
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
    }
    .risk-badge {
        font-size: 0.7rem;
        font-weight: 700;
        padding: 0.2rem 0.55rem;
        border-radius: 4px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .risk-critical { background: #fee2e2; color: #dc2626; border: 1px solid #fecaca; }
    .risk-high { background: #ffedd5; color: #ea580c; border: 1px solid #fed7aa; }
    .risk-medium { background: #fef3c7; color: #d97706; border: 1px solid #fde68a; }
    .risk-low { background: #dcfce7; color: #16a34a; border: 1px solid #bbf7d0; }
    .status-pill {
        font-size: 0.72rem;
        font-weight: 500;
        padding: 0.15rem 0.5rem;
        border-radius: 9999px;
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
    }
    .summary-meta {
        font-size: 0.82rem;
        color: #64748b;
        display: flex;
        gap: 0.6rem;
    }
    .summary-right {
        display: flex;
        align-items: center;
        gap: 1.5rem;
    }
    .summary-stat {
        text-align: right;
    }
    .stat-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748b;
    }
    .stat-val {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
    }
    .stat-danger {
        color: #dc2626;
    }
    .stat-prob {
        color: #7c3aed;
    }
    .decision-tile {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.15rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 250px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 0.75rem;
    }
    .decision-tile.optimal {
        border: 2px solid #2563eb;
        background: #fafcff;
    }
    .tile-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.65rem;
    }
    .tile-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.25;
    }
    .tile-type {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 2px;
    }
    .badge-optimal {
        background: #2563eb;
        color: #ffffff;
        font-size: 0.65rem;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        white-space: nowrap;
    }
    .tile-hero {
        background: #f8fafc;
        border-radius: 6px;
        padding: 0.55rem 0.75rem;
        margin-bottom: 0.75rem;
        display: flex;
        justify-content: space-between;
        align-items: baseline;
    }
    .hero-savings {
        font-size: 1.2rem;
        font-weight: 800;
        color: #059669;
    }
    .hero-roi {
        font-size: 0.85rem;
        font-weight: 700;
        color: #2563eb;
    }
    .tile-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.4rem 0.6rem;
        font-size: 0.82rem;
        margin-bottom: 0.4rem;
    }
    .grid-label {
        font-size: 0.68rem;
        color: #64748b;
        text-transform: uppercase;
        font-weight: 600;
    }
    .grid-val {
        font-weight: 600;
        color: #0f172a;
    }
    .action-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 1.1rem;
        margin-bottom: 0.75rem;
        height: 100%;
    }
    .action-card.recommended {
        border: 2px solid #2563eb;
        background: #f8faff;
    }
    .badge-optimal {
        background: #2563eb;
        color: #ffffff;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 4px;
        float: right;
    }
</style>
""", unsafe_allow_html=True)

# Ensure database is seeded
def ensure_db():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM shipments")
            if cursor.fetchone()[0] == 0:
                seed_complete_operational_environment()
    except Exception:
        seed_complete_operational_environment()

ensure_db()

@st.cache_data(ttl=5)
def load_data():
    with get_connection() as conn:
        df = pd.read_sql_query("""
            SELECT s.*, p.delay_probability, p.predicted_delay_days, p.risk_tier,
                   d.selected_option, d.option_title as executed_strategy, d.approved_cost as executed_cost
            FROM shipments s
            LEFT JOIN predictions p ON s.shipment_id = p.shipment_id
            LEFT JOIN decision_log d ON s.shipment_id = d.shipment_id
            ORDER BY p.delay_probability DESC
        """, conn)
    engine = ClosedLoopEngine()
    analytics = engine.get_decision_roi_analytics()
    return df, analytics

df_fleet, analytics = load_data()

# Predictor instance
predictor = SupplyChainPredictor()
predictor.load()

# Currency Conversion Rate
USD_TO_INR = 83.0  # 1 USD = 83.0 INR

# Header
st.markdown(f"""
<div class="header-bar">
    <div>
        <div class="header-title">📦 Supply Prescript</div>
        <div class="header-sub">Operational Prescriptive Decision Desk</div>
    </div>
    <div style="display:flex; align-items:center; gap:0.5rem;">
        <span class="status-tag"><span style="color:#22c55e;">●</span> Live System</span>
        <span class="status-tag">Currency: <strong style="color:#f59e0b;">INR (₹)</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# Top 4 Clean KPIs
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Monitored Shipments</div>
        <div class="metric-value">{len(df_fleet):,}</div>
        <div class="metric-sub">Active Fleet Tracking</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    at_risk = len(df_fleet[df_fleet['risk_tier'].isin(['CRITICAL', 'HIGH'])])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">At-Risk Shipments</div>
        <div class="metric-value" style="color:#dc2626;">{at_risk:,}</div>
        <div class="metric-sub">Requires Intervention</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    loss_prev = analytics.get("total_loss_prevented", 0.0) * USD_TO_INR
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Financial Loss Prevented</div>
        <div class="metric-value" style="color:#059669;">₹{loss_prev:,.0f}</div>
        <div class="metric-sub">Realized Financial Savings</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    avg_roi = analytics.get("avg_decision_roi_pct", 0.0)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Realized Decision ROI</div>
        <div class="metric-value" style="color:#2563eb;">{avg_roi:.1f}%</div>
        <div class="metric-sub">Closed-Loop Capital Return</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# 2 Simple Tabs
tab_decisions, tab_outcomes = st.tabs([
    "⚡ Decision Desk (Predict & Prescribe)",
    "📈 Performance & Closed-Loop ROI"
])

# =============================================================
# TAB 1: DECISION DESK (Action-Oriented)
# =============================================================
with tab_decisions:
    # Unified single-strip triage filter controls
    st.markdown("#### 1. Prioritized Shipment Triage")
    c_tier, c_cat, c_sel, c_budget = st.columns([1.1, 1.1, 1.8, 1.1])
    with c_tier:
        tier_filter = st.selectbox(
            "Filter Risk Tier",
            options=["At-Risk (CRITICAL & HIGH)", "CRITICAL Only", "HIGH Only", "MEDIUM Risk", "All Shipments"],
            index=0,
            key="ui_tier_filter"
        )
    with c_cat:
        available_cats = ["All Categories"] + sorted([str(c) for c in df_fleet['category_name'].dropna().unique()])
        cat_filter = st.selectbox(
            "Filter Category",
            options=available_cats,
            index=0,
            key="ui_cat_filter"
        )

    # Apply filters
    df_filtered = df_fleet.copy()
    if tier_filter == "At-Risk (CRITICAL & HIGH)":
        df_filtered = df_filtered[df_filtered['risk_tier'].isin(['CRITICAL', 'HIGH'])]
    elif tier_filter == "CRITICAL Only":
        df_filtered = df_filtered[df_filtered['risk_tier'] == 'CRITICAL']
    elif tier_filter == "HIGH Only":
        df_filtered = df_filtered[df_filtered['risk_tier'] == 'HIGH']
    elif tier_filter == "MEDIUM Risk":
        df_filtered = df_filtered[df_filtered['risk_tier'] == 'MEDIUM']

    if cat_filter != "All Categories":
        df_filtered = df_filtered[df_filtered['category_name'] == cat_filter]

    filtered_shipment_list = df_filtered['shipment_id'].tolist()
    if not filtered_shipment_list:
        filtered_shipment_list = df_fleet['shipment_id'].tolist()

    with c_sel:
        selected_id = st.selectbox(
            f"Active Shipment ({len(filtered_shipment_list)} available)",
            options=filtered_shipment_list,
            index=0,
            help="Showing shipments prioritized by delay probability and applied filters."
        )
    
    selected_row = df_fleet[df_fleet['shipment_id'] == selected_id].iloc[0]

    with c_budget:
        order_total_inr = float(selected_row['order_total']) * USD_TO_INR
        default_budget_inr = float(max(10000.0, round(order_total_inr * 0.70, -2)))
        budget_limit_inr = st.number_input(
            "Budget Cap (₹)",
            min_value=5000.0,
            max_value=2000000.0,
            value=default_budget_inr,
            step=1000.0,
            help="Maximum intervention budget constraint in INR (₹)"
        )

    # Clean, modern shipment summary card
    risk_class = str(selected_row['risk_tier']).lower() if pd.notnull(selected_row['risk_tier']) else 'low'
    st.markdown(f"""
    <div class="shipment-summary-card">
        <div class="summary-left">
            <div class="summary-id-row">
                <span class="shipment-badge">{selected_row['shipment_id']}</span>
                <span class="risk-badge risk-{risk_class}">{selected_row['risk_tier']} RISK</span>
                <span class="status-pill">{selected_row['current_status']}</span>
            </div>
            <div class="summary-meta">
                <span>Category: <strong>{selected_row['category_name']}</strong></span>
                <span>•</span>
                <span>Mode: <strong>{selected_row['shipping_mode']}</strong></span>
            </div>
        </div>
        <div class="summary-right">
            <div class="summary-stat">
                <div class="stat-label">Order Value</div>
                <div class="stat-val">₹{order_total_inr:,.0f}</div>
            </div>
            <div class="summary-stat">
                <div class="stat-label">Predicted Delay</div>
                <div class="stat-val stat-danger">{selected_row['predicted_delay_days']:.1f} days late</div>
            </div>
            <div class="summary-stat">
                <div class="stat-label">Disruption Probability</div>
                <div class="stat-val stat-prob">{selected_row['delay_probability']:.1%}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Solve prescriptions
    solver = PrescriptiveSolver()
    budget_limit_usd = budget_limit_inr / USD_TO_INR
    result = solver.solve_prescriptions(
        order_total=float(selected_row['order_total']),
        predicted_delay_days=float(selected_row['predicted_delay_days']),
        max_budget=budget_limit_usd
    )

    baseline_loss_inr = result['baseline_disruption_cost'] * USD_TO_INR
    st.markdown(f"#### 2. Choose Prescribed Action & Execute *(Unmitigated Loss Risk: :red[₹{baseline_loss_inr:,.2f}] )*")

    prescriptions = result['prescriptions']
    cols = st.columns(3)

    for i, p in enumerate(prescriptions[:3]):
        with cols[i]:
            is_rec = p['is_optimal']
            card_class = "decision-tile optimal" if is_rec else "decision-tile"
            badge = '<span class="badge-optimal">★ RECOMMENDED</span>' if is_rec else ""
            cost_inr = p['estimated_cost'] * USD_TO_INR
            savings_inr = p['net_financial_benefit'] * USD_TO_INR
            budget_label = "✅ In Budget" if p['satisfies_budget'] else "⚠️ Over Cap"

            st.markdown(f"""
            <div class="{card_class}">
                <div>
                    <div class="tile-header">
                        <div>
                            <div class="tile-title">{p['title']}</div>
                            <div class="tile-type">{p['strategy_type']}</div>
                        </div>
                        {badge}
                    </div>
                    <div class="tile-hero">
                        <div>
                            <div class="grid-label">Net Savings</div>
                            <div class="hero-savings">+₹{savings_inr:,.0f}</div>
                        </div>
                        <div style="text-align:right;">
                            <div class="grid-label">Projected ROI</div>
                            <div class="hero-roi">+{p['roi_pct']:.0f}%</div>
                        </div>
                    </div>
                    <div class="tile-grid">
                        <div>
                            <div class="grid-label">Expedite Cost</div>
                            <div class="grid-val">₹{cost_inr:,.0f}</div>
                        </div>
                        <div>
                            <div class="grid-label">Time Saved</div>
                            <div class="grid-val">{p['days_saved']:.1f} days</div>
                        </div>
                        <div>
                            <div class="grid-label">SLA Adherence</div>
                            <div class="grid-val">{p['sla_compliance_rate']}%</div>
                        </div>
                        <div>
                            <div class="grid-label">Feasibility</div>
                            <div class="grid-val">{budget_label}</div>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            btn_label = f"⚡ Execute {p['title']}" if is_rec else f"Execute {p['title']}"
            btn_type = "primary" if is_rec else "secondary"
            if st.button(btn_label, key=f"exec_{p['option_id']}", use_container_width=True, type=btn_type):
                with st.spinner("Writing decision back to operational database..."):
                    res = record_decision_writeback(
                        shipment_id=selected_id,
                        selected_option=p['option_id'],
                        option_title=p['title'],
                        approved_cost=p['estimated_cost'],
                        predicted_lead_time_days=p['expected_delay_days'],
                        operator_id="LogisticsOperator",
                        execution_notes=f"Selected {p['title']} with projected ROI {p['roi_pct']}% (Cost: ₹{cost_inr:,.2f} INR)"
                    )
                    st.success(f"✅ Decision recorded! Shipment status updated.")
                    st.cache_data.clear()
                    time.sleep(0.3)
                    st.rerun()

    # Expandable Full Shipments Pipeline
    with st.expander("📋 Browse All Monitored Shipments", expanded=False):
        df_browse = df_fleet[['shipment_id', 'risk_tier', 'delay_probability', 'predicted_delay_days', 'order_total', 'category_name', 'shipping_mode', 'current_status']].copy()
        df_browse['order_total'] = df_browse['order_total'] * USD_TO_INR
        st.dataframe(
            df_browse.style.format({
                'delay_probability': '{:.1%}',
                'predicted_delay_days': '{:.1f} days',
                'order_total': '₹{:,.2f}'
            }),
            use_container_width=True,
            height=260
        )
        csv_browse = df_browse.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Monitored Shipments (CSV)",
            data=csv_browse,
            file_name="monitored_shipments.csv",
            mime="text/csv",
            key="dl_monitored_csv"
        )

    # Fleet Portfolio Batch Optimizer Expander
    with st.expander("⚡ Fleet Portfolio Prescriptive Optimizer (Multi-Shipment Batch Allocation)", expanded=False):
        st.markdown("""
        **Fleet-Wide Mixed Integer Linear Programming (MILP) Optimizer**:
        Optimally allocate intervention strategies across a cohort of at-risk shipments simultaneously,
        maximizing total network loss prevention under a unified corporate expediting budget cap.
        """)
        
        batch_c1, batch_c2 = st.columns([1, 1])
        with batch_c1:
            batch_count = st.slider("Cohort Size (Top At-Risk Shipments):", min_value=3, max_value=20, value=6, step=1, key="portfolio_slider")
        with batch_c2:
            portfolio_budget_inr = st.number_input(
                "Unified Fleet Budget Cap (₹):",
                min_value=20000.0,
                max_value=5000000.0,
                value=250000.0,
                step=10000.0,
                key="portfolio_budget_input",
                help="Unified corporate budget limit across all selected cohort shipments"
            )
            
        target_batch_df = df_fleet[df_fleet['risk_tier'].isin(['CRITICAL', 'HIGH'])].head(batch_count)
        if target_batch_df.empty:
            target_batch_df = df_fleet.head(batch_count)
            
        if st.button(f"🎯 Solve Fleet MILP for {len(target_batch_df)} Shipments", key="btn_run_portfolio", type="primary"):
            batch_items = target_batch_df.to_dict(orient="records")
            portfolio_budget_usd = portfolio_budget_inr / USD_TO_INR
            port_res = solver.solve_portfolio_optimization(batch_items, portfolio_budget=portfolio_budget_usd)
            
            p_spend_inr = port_res["total_allocated_spend"] * USD_TO_INR
            p_prev_inr = port_res["total_loss_prevented"] * USD_TO_INR
            p_surplus_inr = port_res["budget_surplus"] * USD_TO_INR
            
            # Fleet KPI summary
            kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
            kpi_c1.metric("Allocated Spend", f"₹{p_spend_inr:,.0f}", f"{port_res['budget_utilized_pct']:.1f}% budget used")
            kpi_c2.metric("Loss Prevented", f"₹{p_prev_inr:,.0f}")
            kpi_c3.metric("Budget Surplus", f"₹{p_surplus_inr:,.0f}")
            kpi_c4.metric("Portfolio ROI", f"{port_res['portfolio_roi_pct']:.1f}%")
            
            # Table of allocations
            df_alloc = pd.DataFrame(port_res["allocations"])
            df_alloc_disp = df_alloc[['shipment_id', 'category_name', 'order_total', 'predicted_delay_days', 'selected_option', 'option_title', 'allocated_cost', 'days_saved', 'net_savings', 'roi_pct']].copy()
            df_alloc_disp['order_total'] = df_alloc_disp['order_total'] * USD_TO_INR
            df_alloc_disp['allocated_cost'] = df_alloc_disp['allocated_cost'] * USD_TO_INR
            df_alloc_disp['net_savings'] = df_alloc_disp['net_savings'] * USD_TO_INR
            
            st.dataframe(
                df_alloc_disp.style.format({
                    'order_total': '₹{:,.2f}',
                    'allocated_cost': '₹{:,.2f}',
                    'net_savings': '₹{:,.2f}',
                    'predicted_delay_days': '{:.1f}d',
                    'days_saved': '{:.1f}d',
                    'roi_pct': '{:.1f}%'
                }),
                use_container_width=True
            )
            
            csv_port = df_alloc_disp.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Optimal Batch Prescriptions (CSV)",
                data=csv_port,
                file_name="optimal_fleet_prescriptions.csv",
                mime="text/csv",
                key="dl_batch_csv"
            )

# =============================================================
# TAB 2: PERFORMANCE & CLOSED-LOOP ROI
# =============================================================
with tab_outcomes:
    st.subheader("Closed-Loop Impact & Realized Performance")
    st.caption("Tracks whether executed prescriptions delivered their expected savings against actual freight bills and carrier outcomes.")

    engine = ClosedLoopEngine()

    # Action buttons in one compact row
    act_col1, act_col2 = st.columns([1, 1])
    with act_col1:
        if st.button("🔄 Sync & Evaluate Realized Outcomes", type="primary", use_container_width=True):
            evaluated = engine.simulate_and_evaluate_pending_decisions()
            st.success(f"Evaluated {len(evaluated)} executed decisions with realized carrier outcomes!")
            st.cache_data.clear()
            time.sleep(0.4)
            st.rerun()
    with act_col2:
        if st.button("🤖 Recalibrate Models on Realized Data", use_container_width=True):
            with st.spinner("Retraining model with outcome feedback..."):
                retrain_res = engine.trigger_continuous_retraining()
                st.success(f"Models retrained! New version: {retrain_res['new_version']}")
                st.cache_data.clear()
                time.sleep(0.4)
                st.rerun()

    st.write("")

    # Realized outcomes data
    with get_connection() as conn:
        df_outcomes = pd.read_sql_query("""
            SELECT o.outcome_id, o.shipment_id, d.option_title,
                   o.predicted_cost, o.actual_cost, o.cost_variance,
                   o.predicted_delay_days, o.actual_delay_days,
                   o.financial_loss_prevented, o.decision_roi_pct,
                   o.evaluated_at
            FROM outcomes o
            JOIN decision_log d ON o.decision_id = d.decision_id
            ORDER BY o.outcome_id DESC
        """, conn)

    if not df_outcomes.empty:
        ch_c1, ch_c2 = st.columns([1, 1])
        with ch_c1:
            # Mini Chart: Quoted vs Actual Cost (INR)
            df_cost_chart = df_outcomes.head(15).copy()
            df_cost_chart['predicted_cost'] = df_cost_chart['predicted_cost'] * USD_TO_INR
            df_cost_chart['actual_cost'] = df_cost_chart['actual_cost'] * USD_TO_INR
            fig_cost = px.bar(
                df_cost_chart,
                x="shipment_id",
                y=["predicted_cost", "actual_cost"],
                barmode="group",
                title="Quoted vs Realized Expediting Cost (₹)",
                labels={"value": "Cost (₹)", "variable": "Cost Type"},
                color_discrete_map={"predicted_cost": "#3b82f6", "actual_cost": "#10b981"}
            )
            fig_cost.update_layout(margin=dict(l=10, r=10, t=35, b=10), height=260)
            st.plotly_chart(fig_cost, use_container_width=True)

        with ch_c2:
            # ROI by Strategy Type
            df_strat_roi = df_outcomes.groupby("option_title", as_index=False).agg(
                avg_roi=("decision_roi_pct", "mean"),
                count=("outcome_id", "count")
            )
            fig_strat = px.bar(
                df_strat_roi,
                x="option_title",
                y="avg_roi",
                color="avg_roi",
                color_continuous_scale="Blues",
                title="Average Realized Decision ROI (%) by Strategy",
                labels={"avg_roi": "Average ROI (%)", "option_title": "Intervention Strategy"}
            )
            fig_strat.update_layout(margin=dict(l=10, r=10, t=35, b=10), height=260, showlegend=False)
            st.plotly_chart(fig_strat, use_container_width=True)

        st.markdown("#### Realized Outcomes Ledger")
        df_outcomes_disp = df_outcomes.copy()
        for col in ['predicted_cost', 'actual_cost', 'cost_variance', 'financial_loss_prevented']:
            df_outcomes_disp[col] = df_outcomes_disp[col] * USD_TO_INR
        st.dataframe(
            df_outcomes_disp.style.format({
                'predicted_cost': '₹{:,.2f}',
                'actual_cost': '₹{:,.2f}',
                'cost_variance': '₹{:+,.2f}',
                'financial_loss_prevented': '₹{:,.2f}',
                'decision_roi_pct': '{:.1f}%',
                'predicted_delay_days': '{:.1f}d',
                'actual_delay_days': '{:.1f}d'
            }),
            use_container_width=True,
            height=250
        )
        csv_outcomes = df_outcomes_disp.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Realized Outcomes Ledger (CSV)",
            data=csv_outcomes,
            file_name="realized_outcomes_ledger.csv",
            mime="text/csv",
            key="dl_outcomes_csv"
        )
    else:
        st.info("No outcomes evaluated yet. Click 'Sync & Evaluate Realized Outcomes' to process pending decisions.")

    # Collapsible Section for Technical Diagnostics & Audit
    with st.expander("🛠️ Advanced Solver Diagnostics & Audit Trail", expanded=False):
        audit_res = run_optimization_audit(n_trials=50)
        st.markdown(f"""
        **Mathematical Constraint Compliance Proof**:
        - **Verdict**: {audit_res['verdict']}
        - **Trials Evaluated**: {audit_res['trials_evaluated']}
        - **Hard Budget Violations**: {audit_res['violations_detected']}
        - **Compliance Rate**: **{audit_res['constraint_compliance_rate_pct']:.1f}%**
        """)
        
        with get_connection() as conn:
            df_audit_log = pd.read_sql_query("SELECT * FROM audit_log ORDER BY audit_id DESC LIMIT 50", conn)
        st.markdown("##### Recent Transactional Audit Log")
        st.dataframe(df_audit_log, use_container_width=True, height=200)
