"""
Supply Prescript - Closed-Loop Prescriptive Analytics UI
A simple, clean, and modern operational interface for Supply Chain Logistics.
Integrates XGBoost predictive modeling, PuLP linear programming solver,
transactional write-back, and closed-loop Decision ROI tracking.
"""

import os
import sys
import time
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db_manager import get_connection, record_decision_writeback, initialize_database
from database.seed_data import seed_complete_operational_environment
from models.predictive_model import SupplyChainPredictor
from models.prescriptive_solver import PrescriptiveSolver, run_optimization_audit
from models.closed_loop import ClosedLoopEngine

# Page configuration
st.set_page_config(
    page_title="Supply Prescript | Closed-Loop Prescriptive Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for simple, clean, modern UI
st.markdown("""
<style>
    /* Clean modern styling */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.2rem 1.8rem;
        background: #0f172a;
        color: #f8fafc;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .badge-pill {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        letter-spacing: 0.025em;
    }
    .badge-critical { background-color: #fee2e2; color: #991b1b; }
    .badge-high { background-color: #ffedd5; color: #9a3412; }
    .badge-medium { background-color: #fef3c7; color: #92400e; }
    .badge-low { background-color: #dcfce7; color: #166534; }
    .badge-resolved { background-color: #e0e7ff; color: #3730a3; }
    
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    .metric-title {
        color: #64748b;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        color: #0f172a;
        font-size: 1.65rem;
        font-weight: 700;
    }
    .metric-sub {
        color: #10b981;
        font-size: 0.75rem;
        font-weight: 500;
        margin-top: 0.25rem;
    }
    
    .prescription-card {
        border-radius: 10px;
        padding: 1.25rem;
        border: 2px solid #e2e8f0;
        background: #ffffff;
        margin-bottom: 1rem;
        transition: transform 0.15s ease-in-out;
    }
    .prescription-card.optimal {
        border-color: #3b82f6;
        background: #f8faff;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 0.9rem;
        padding: 8px 16px;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions for database access
def ensure_environment():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM shipments")
            cnt = cursor.fetchone()[0]
            if cnt == 0:
                seed_complete_operational_environment()
    except Exception:
        seed_complete_operational_environment()

ensure_environment()

@st.cache_data(ttl=5)
def load_fleet_data():
    with get_connection() as conn:
        df_shipments = pd.read_sql_query("""
            SELECT s.*, p.delay_probability, p.predicted_delay_days, p.risk_tier,
                   d.selected_option, d.option_title as executed_strategy, d.approved_cost as executed_cost,
                   d.execution_timestamp
            FROM shipments s
            LEFT JOIN predictions p ON s.shipment_id = p.shipment_id
            LEFT JOIN decision_log d ON s.shipment_id = d.shipment_id
            ORDER BY p.delay_probability DESC
        """, conn)
    return df_shipments

@st.cache_data(ttl=5)
def load_analytics_data():
    engine = ClosedLoopEngine()
    return engine.get_decision_roi_analytics()

# Predictor instance
predictor = SupplyChainPredictor()
predictor.load()

# Header Banner
st.markdown(f"""
<div class="main-header">
    <div>
        <h2 style="margin:0; font-size: 1.5rem; font-weight: 700;">📦 Supply Prescript</h2>
        <p style="margin:0; opacity: 0.85; font-size: 0.85rem;">Closed-Loop Prescriptive Analytics & Decision Automation Platform</p>
    </div>
    <div style="text-align: right;">
        <span style="background:#1e293b; padding:4px 10px; border-radius:6px; font-size:0.75rem; border:1px solid #334155;">
            Model: <strong style="color:#38bdf8;">{predictor.version}</strong>
        </span>
        <span style="background:#1e293b; padding:4px 10px; border-radius:6px; font-size:0.75rem; border:1px solid #334155; margin-left: 8px;">
            Solver: <strong style="color:#4ade80;">PuLP MILP</strong>
        </span>
        <span style="background:#1e293b; padding:4px 10px; border-radius:6px; font-size:0.75rem; border:1px solid #334155; margin-left: 8px;">
            Write-Back: <strong style="color:#a78bfa;">ACID SQLite</strong>
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# Top KPIs Row
df_fleet = load_fleet_data()
analytics = load_analytics_data()

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Tracked Shipments</div>
        <div class="metric-value">{len(df_fleet):,}</div>
        <div class="metric-sub">Kaggle DataCo Feed</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    critical_count = len(df_fleet[df_fleet['risk_tier'].isin(['CRITICAL', 'HIGH'])])
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Disruption At-Risk</div>
        <div class="metric-value" style="color:#dc2626;">{critical_count}</div>
        <div class="metric-sub" style="color:#dc2626;">Needs Prescriptive Action</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    avg_delay = df_fleet[df_fleet['delay_probability'] >= 0.5]['predicted_delay_days'].mean()
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Avg Predicted Delay</div>
        <div class="metric-value">{avg_delay:.1f} <span style="font-size:1rem;">days</span></div>
        <div class="metric-sub">XGBoost Regressor</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    savings = analytics.get("total_loss_prevented", 0.0)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Financial Loss Prevented</div>
        <div class="metric-value" style="color:#059669;">${savings:,.0f}</div>
        <div class="metric-sub" style="color:#059669;">Prescribed Actions</div>
    </div>
    """, unsafe_allow_html=True)

with kpi5:
    roi = analytics.get("avg_decision_roi_pct", 0.0)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Average Decision ROI</div>
        <div class="metric-value" style="color:#2563eb;">{roi:.1f}%</div>
        <div class="metric-sub" style="color:#2563eb;">Closed-Loop Realized</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Navigation Tabs
tab_radar, tab_prescribe, tab_audit, tab_closed_loop, tab_logs = st.tabs([
    "🎯 Disruption Radar (Predictive)",
    "⚡ Prescriptive Action Center",
    "🛡️ Optimization & Constraints Audit",
    "🔄 Closed-Loop ROI & Feedback",
    "📜 System Audit & Write-Back Log"
])

# -------------------------------------------------------------
# TAB 1: DISRUPTION RADAR
# -------------------------------------------------------------
with tab_radar:
    st.subheader("Live Supply Chain Disruption Radar")
    st.caption("XGBoost dual-model predictive baseline detecting delay probability and estimated lead-time disruption.")
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        selected_risk = st.multiselect(
            "Filter by Risk Tier",
            options=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH"]
        )
    with col_filter2:
        regions = ["All"] + sorted(df_fleet['order_region'].dropna().unique().tolist())
        selected_region = st.selectbox("Order Region", options=regions, index=0)
    with col_filter3:
        status_filter = st.selectbox("Fulfillment Status", options=["All", "PENDING (Unmitigated)", "INTERVENED"], index=0)

    # Filter data
    filtered_df = df_fleet.copy()
    if selected_risk:
        filtered_df = filtered_df[filtered_df['risk_tier'].isin(selected_risk)]
    if selected_region != "All":
        filtered_df = filtered_df[filtered_df['order_region'] == selected_region]
    if status_filter == "PENDING (Unmitigated)":
        filtered_df = filtered_df[filtered_df['current_status'] == 'PENDING']
    elif status_filter == "INTERVENED":
        filtered_df = filtered_df[filtered_df['current_status'].str.startswith('INTERVENED')]

    # Visual Analytics Row
    chart_c1, chart_c2 = st.columns([1, 1])
    with chart_c1:
        fig_risk = px.histogram(
            filtered_df,
            x="delay_probability",
            nbins=25,
            color="risk_tier",
            color_discrete_map={"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#f59e0b", "LOW": "#10b981"},
            title="Delay Probability Distribution (XGBoost Classifier)"
        )
        fig_risk.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=280)
        st.plotly_chart(fig_risk, use_container_width=True)

    with chart_c2:
        fig_scatter = px.scatter(
            filtered_df,
            x="order_total",
            y="predicted_delay_days",
            color="risk_tier",
            size="order_quantity",
            hover_data=["shipment_id", "category_name", "shipping_mode"],
            color_discrete_map={"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#f59e0b", "LOW": "#10b981"},
            title="Disruption Exposure: Cargo Value vs Expected Delay Duration"
        )
        fig_scatter.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=280)
        st.plotly_chart(fig_scatter, use_container_width=True)

    # Interactive Table
    st.write(f"Showing **{len(filtered_df)}** shipments matching criteria:")
    display_cols = [
        'shipment_id', 'risk_tier', 'delay_probability', 'predicted_delay_days',
        'order_total', 'category_name', 'shipping_mode', 'order_region', 'current_status'
    ]
    st.dataframe(
        filtered_df[display_cols].style.format({
            'delay_probability': '{:.1%}',
            'predicted_delay_days': '{:.1f} days',
            'order_total': '${:,.2f}'
        }),
        use_container_width=True,
        height=320
    )

# -------------------------------------------------------------
# TAB 2: PRESCRIPTIVE ACTION CENTER
# -------------------------------------------------------------
with tab_prescribe:
    st.subheader("⚡ Prescriptive Decision Center & Write-Back")
    st.caption("Linear Programming (PuLP) optimization prescribing 3 mathematically optimal alternatives under hard constraints.")
    
    # Select shipment
    high_risk_shipments = df_fleet[df_fleet['risk_tier'].isin(['CRITICAL', 'HIGH'])]['shipment_id'].tolist()
    if not high_risk_shipments:
        high_risk_shipments = df_fleet['shipment_id'].tolist()
        
    col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])
    with col_sel1:
        active_shipment_id = st.selectbox(
            "Select Flagged Shipment for Prescriptive Optimization:",
            options=high_risk_shipments,
            index=0
        )
    
    selected_row = df_fleet[df_fleet['shipment_id'] == active_shipment_id].iloc[0]
    
    with col_sel2:
        max_budget_input = st.number_input(
            "Hard Budget Limit ($)",
            min_value=100.0,
            max_value=10000.0,
            value=float(max(300.0, round(selected_row['order_total'] * 0.70, 2))),
            step=50.0
        )
    with col_sel3:
        max_sla_delay = st.number_input(
            "Max Allowable SLA Delay (Days)",
            min_value=0.0,
            max_value=14.0,
            value=float(max(1.0, round(selected_row['predicted_delay_days'], 1))),
            step=0.5
        )

    # Details of selected shipment
    st.markdown(f"""
    <div style="background:#f1f5f9; padding: 12px 16px; border-radius: 8px; margin-bottom: 15px; font-size: 0.9rem; display:flex; justify-content:space-between;">
        <span><strong>Order Total:</strong> ${selected_row['order_total']:,.2f}</span>
        <span><strong>Category:</strong> {selected_row['category_name']}</span>
        <span><strong>Mode:</strong> {selected_row['shipping_mode']}</span>
        <span><strong>Region:</strong> {selected_row['order_region']}</span>
        <span><strong>Predicted Delay:</strong> <strong style="color:#dc2626;">{selected_row['predicted_delay_days']:.1f} days</strong></span>
        <span><strong>Status:</strong> <code>{selected_row['current_status']}</code></span>
    </div>
    """, unsafe_allow_html=True)

    # Run PuLP solver
    solver = PrescriptiveSolver()
    optimization = solver.solve_prescriptions(
        order_total=float(selected_row['order_total']),
        predicted_delay_days=float(selected_row['predicted_delay_days']),
        max_budget=max_budget_input,
        max_allowable_delay=max_sla_delay
    )

    baseline_loss = optimization['baseline_disruption_cost']
    st.markdown(f"**Baseline Disruption Loss if Unmitigated (Status Quo):** :red[**${baseline_loss:,.2f}**]")
    
    # Render Prescriptions Cards
    prescriptions = optimization['prescriptions']
    card_cols = st.columns(3)
    
    for i, p in enumerate(prescriptions[:3]):
        with card_cols[i]:
            is_rec = p['is_optimal']
            border_style = "border: 2px solid #2563eb; background:#eff6ff;" if is_rec else "border: 1px solid #cbd5e1; background:#ffffff;"
            rec_badge = "<span style='background:#2563eb; color:white; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:700;'>★ RECOMMENDED OPTIMAL</span>" if is_rec else ""
            
            budget_flag = "✅ Within Budget" if p['satisfies_budget'] else "❌ Exceeds Budget"
            sla_flag = "✅ Within SLA" if p['satisfies_sla'] else "⚠️ Breaches SLA"
            
            st.markdown(f"""
            <div style="{border_style} border-radius:10px; padding:15px; margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="font-size:1.05rem;">{p['option_id'][-1]}: {p['title']}</strong>
                    {rec_badge}
                </div>
                <div style="color:#64748b; font-size:0.8rem; margin-top:2px;">Strategy: {p['strategy_type']}</div>
                <hr style="margin:8px 0;">
                <div style="font-size:0.9rem;">
                    <div><strong>Expediting Cost:</strong> ${p['estimated_cost']:,.2f}</div>
                    <div><strong>Remaining Delay:</strong> {p['expected_delay_days']:.1f} days (Saves {p['days_saved']:.1f}d)</div>
                    <div><strong>SLA Compliance:</strong> {p['sla_compliance_rate']}%</div>
                    <div><strong>Net Financial Benefit:</strong> <span style="color:#059669; font-weight:600;">+${p['net_financial_benefit']:,.2f}</span></div>
                    <div><strong>Expected ROI:</strong> <span style="color:#2563eb; font-weight:700;">{p['roi_pct']:.1f}%</span></div>
                </div>
                <hr style="margin:8px 0;">
                <div style="font-size:0.75rem;">
                    <div>{budget_flag} (Cap: ${max_budget_input:,.0f})</div>
                    <div>{sla_flag}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action button
            button_label = f"🚀 Execute {p['title']}"
            if st.button(button_label, key=f"btn_exec_{p['option_id']}", use_container_width=True, type="primary" if is_rec else "secondary"):
                with st.spinner("Executing transactional write-back to database..."):
                    res = record_decision_writeback(
                        shipment_id=active_shipment_id,
                        selected_option=p['option_id'],
                        option_title=p['title'],
                        approved_cost=p['estimated_cost'],
                        predicted_lead_time_days=p['expected_delay_days'],
                        operator_id="LogisticsManager_Admin",
                        execution_notes=f"Approved {p['strategy_type']} via Prescriptive UI (ROI: {p['roi_pct']}%)"
                    )
                    st.success(f"✅ Decision **{res['decision_id']}** written back to operational database! Shipment status updated.")
                    st.cache_data.clear()
                    time.sleep(0.5)
                    st.rerun()

    # Visual Trade-Off Comparison
    st.write("")
    st.markdown("#### ⚖️ Mathematical Trade-Off Analysis (Cost vs Speed vs Net Savings)")
    df_tradeoff = pd.DataFrame(prescriptions[:3])
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(
        x=df_tradeoff['title'],
        y=df_tradeoff['estimated_cost'],
        name="Intervention Cost ($)",
        marker_color="#f97316"
    ))
    fig_comp.add_trace(go.Bar(
        x=df_tradeoff['title'],
        y=df_tradeoff['net_financial_benefit'],
        name="Net Financial Savings ($)",
        marker_color="#10b981"
    ))
    fig_comp.update_layout(
        barmode='group',
        margin=dict(l=20, r=20, t=30, b=20),
        height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_comp, use_container_width=True)

# -------------------------------------------------------------
# TAB 3: OPTIMIZATION & GOVERNANCE AUDIT
# -------------------------------------------------------------
with tab_audit:
    st.subheader("🛡️ Optimization & Constraint Governance Audit")
    st.caption("Mid-Project Review verification: Mathematical proof that the solver NEVER recommends an action violating hard budget constraints.")

    col_a1, col_a2 = st.columns([1, 2])
    with col_a1:
        st.markdown(r"""
        **Business Constraints Definition:**
        - $\sum x_k \cdot \text{Cost}_k \le B_{max}$ *(Strict Hard Budget Bound)*
        - $\sum x_k = 1$ *(Mutually Exclusive Decision Selection)*
        - Feasibility Guarantee: In extreme under-budget scenarios, system safely reverts to `STATUS_QUO` ($0 cost).
        """)
        trials_count = st.slider("Monte-Carlo Audit Scenarios", min_value=25, max_value=200, value=75, step=25)
        run_audit_btn = st.button("▶ Run Live Constraint Audit", type="primary", use_container_width=True)

    with col_a2:
        audit_res = run_optimization_audit(n_trials=trials_count)
        
        st.markdown(f"""
        <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:8px; padding:15px; margin-bottom:15px;">
            <h4 style="margin:0; color:#15803d;">{audit_res['verdict']}</h4>
            <div style="font-size:0.9rem; color:#166534; margin-top:5px;">
                <strong>Trials Tested:</strong> {audit_res['trials_evaluated']} |
                <strong>Violations:</strong> {audit_res['violations_detected']} |
                <strong>Compliance Rate:</strong> {audit_res['constraint_compliance_rate_pct']:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Simulation Scatter Plot
    np.random.seed(101)
    audit_data = []
    for i in range(trials_count):
        val = np.random.uniform(200.0, 5000.0)
        del_d = np.random.uniform(1.0, 14.0)
        budg = np.random.uniform(150.0, 1800.0)
        res = solver.solve_prescriptions(val, del_d, max_budget=budg)
        chosen = next(p for p in res['prescriptions'] if p['is_optimal'])
        audit_data.append({
            "Trial": i + 1,
            "Budget Limit ($)": budg,
            "Prescribed Option": chosen['title'],
            "Prescribed Cost ($)": chosen['estimated_cost'],
            "Violated": chosen['estimated_cost'] > budg
        })
    df_audit = pd.DataFrame(audit_data)

    fig_audit = px.scatter(
        df_audit,
        x="Budget Limit ($)",
        y="Prescribed Cost ($)",
        color="Prescribed Option",
        symbol="Violated",
        title="Audit Scatter: Prescribed Cost vs Budget Limit (Every point strictly below red diagonal y=x bound)"
    )
    # Add y=x diagonal line
    fig_audit.add_trace(go.Scatter(
        x=[0, 1800],
        y=[0, 1800],
        mode="lines",
        name="Hard Budget Bound (y=x)",
        line=dict(color="red", dash="dash")
    ))
    fig_audit.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=320)
    st.plotly_chart(fig_audit, use_container_width=True)

# -------------------------------------------------------------
# TAB 4: CLOSED-LOOP ROI & FEEDBACK
# -------------------------------------------------------------
with tab_closed_loop:
    st.subheader("🔄 Closed-Loop Analytics & Continuous Learning")
    st.caption("Closing the loop: Compares predicted intervention cost against actual realized outcomes, calculates Decision ROI, and retrains models on drift.")

    engine = ClosedLoopEngine()

    col_cl1, col_cl2 = st.columns([1, 1])
    with col_cl1:
        st.markdown("#### Realized Outcome Evaluation")
        st.write("Scan operational pipeline for pending executed decisions and realize actual historical outcomes (actual freight bills, SLA delivery checks).")
        if st.button("📊 Evaluate Realized Outcomes & Compute Variance", type="primary"):
            evaluated = engine.simulate_and_evaluate_pending_decisions()
            st.success(f"Evaluated **{len(evaluated)}** executed decisions against realized operational metrics!")
            st.cache_data.clear()
            time.sleep(0.5)
            st.rerun()

    with col_cl2:
        st.markdown("#### Continuous Learning Trigger")
        st.write("When discrepancy or variance exceeds threshold, trigger automatic retraining of the XGBoost model to incorporate new feedback.")
        if st.button("🤖 Trigger Continuous Learning Retraining"):
            with st.spinner("Retraining XGBoost models with closed-loop feedback..."):
                retrain_res = engine.trigger_continuous_retraining()
                st.success(f"Continuous Learning Completed! Model updated to version **{retrain_res['new_version']}**.")
                st.cache_data.clear()
                time.sleep(0.5)
                st.rerun()

    st.divider()

    # Decision ROI Macro Metrics
    cl_stats = engine.get_decision_roi_analytics()
    
    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    with r_col1:
        st.metric("Total Decisions Evaluated", cl_stats['total_outcomes'])
    with r_col2:
        st.metric("Positive Outcome / SLA Success", f"{cl_stats['positive_outcome_rate_pct']:.1f}%")
    with r_col3:
        st.metric("Total Net Savings", f"${cl_stats['total_loss_prevented']:,.2f}")
    with r_col4:
        st.metric("Total Cost Discrepancy / Variance", f"${cl_stats['total_cost_variance']:,.2f}")

    # Realized Outcomes Table
    with get_connection() as conn:
        df_outcomes = pd.read_sql_query("""
            SELECT o.outcome_id, o.decision_id, o.shipment_id, d.selected_option, d.option_title,
                   o.predicted_cost, o.actual_cost, o.cost_variance,
                   o.predicted_delay_days, o.actual_delay_days,
                   o.sla_breached, o.financial_loss_prevented, o.decision_roi_pct,
                   o.feedback_status, o.evaluated_at
            FROM outcomes o
            JOIN decision_log d ON o.decision_id = d.decision_id
            ORDER BY o.outcome_id DESC
        """, conn)

    if not df_outcomes.empty:
        st.write("")
        st.markdown("#### 📈 Predicted vs Actual Cost Discrepancy by Decision")
        fig_var = px.bar(
            df_outcomes.head(20),
            x="shipment_id",
            y=["predicted_cost", "actual_cost"],
            barmode="group",
            title="Quoted vs Realized Expediting Cost (Tracking Realized Surcharges)",
            labels={"value": "Cost ($)", "variable": "Metric"}
        )
        fig_var.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=280)
        st.plotly_chart(fig_var, use_container_width=True)

        st.markdown("#### Evaluated Operational Outcomes Ledger")
        st.dataframe(
            df_outcomes.style.format({
                'predicted_cost': '${:,.2f}',
                'actual_cost': '${:,.2f}',
                'cost_variance': '${:+,.2f}',
                'financial_loss_prevented': '${:,.2f}',
                'decision_roi_pct': '{:.1f}%',
                'predicted_delay_days': '{:.1f}d',
                'actual_delay_days': '{:.1f}d'
            }),
            use_container_width=True,
            height=260
        )
    else:
        st.info("No outcomes evaluated yet. Click 'Evaluate Realized Outcomes' above to simulate historical feedback.")

# -------------------------------------------------------------
# TAB 5: SYSTEM AUDIT & WRITE-BACK LOG
# -------------------------------------------------------------
with tab_logs:
    st.subheader("📜 System Transactional Audit Trail")
    st.caption("Immutable record of all human operator write-backs, optimization checks, and automated continuous learning events.")

    with get_connection() as conn:
        df_audit_log = pd.read_sql_query("SELECT * FROM audit_log ORDER BY audit_id DESC LIMIT 100", conn)
        df_decisions = pd.read_sql_query("SELECT * FROM decision_log ORDER BY execution_timestamp DESC LIMIT 100", conn)

    st.markdown("#### Live Write-Back Audit Log")
    st.dataframe(df_audit_log, use_container_width=True, height=220)

    st.markdown("#### Transactional Decision Registry (`decision_log` Table)")
    st.dataframe(
        df_decisions.style.format({
            'approved_cost': '${:,.2f}',
            'predicted_lead_time_days': '{:.1f} days'
        }),
        use_container_width=True,
        height=240
    )
