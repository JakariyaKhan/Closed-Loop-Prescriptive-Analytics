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
        padding: 1rem 1.5rem;
        background: #0f172a;
        color: #ffffff;
        border-radius: 10px;
        margin-bottom: 1.25rem;
    }
    .pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        margin-left: 0.35rem;
        background: #1e293b;
        border: 1px solid #334155;
    }
    .metric-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748b;
        margin-bottom: 0.2rem;
    }
    .metric-number {
        font-size: 1.5rem;
        font-weight: 700;
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
        <h3 style="margin:0; font-size:1.3rem; font-weight:700;">📦 Supply Prescript</h3>
        <span style="font-size:0.85rem; opacity:0.85;">Closed-Loop Prescriptive Decision Desk</span>
    </div>
    <div>
        <span class="pill">Currency: <strong style="color:#f59e0b;">INR (₹)</strong></span>
        <span class="pill">Model: <strong style="color:#38bdf8;">{predictor.version}</strong></span>
        <span class="pill">Solver: <strong style="color:#4ade80;">MILP Optimization</strong></span>
        <span class="pill">Storage: <strong style="color:#a78bfa;">ACID SQLite</strong></span>
    </div>
</div>
""", unsafe_allow_html=True)

# Top 4 Clean KPIs
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Monitored Shipments</div>
        <div class="metric-number">{len(df_fleet):,}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    at_risk = len(df_fleet[df_fleet['risk_tier'].isin(['CRITICAL', 'HIGH'])])
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">At-Risk Shipments</div>
        <div class="metric-number" style="color:#dc2626;">{at_risk:,}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    loss_prev = analytics.get("total_loss_prevented", 0.0) * USD_TO_INR
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Financial Loss Prevented</div>
        <div class="metric-number" style="color:#059669;">₹{loss_prev:,.0f}</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    avg_roi = analytics.get("avg_decision_roi_pct", 0.0)
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">Realized Decision ROI</div>
        <div class="metric-number" style="color:#2563eb;">{avg_roi:.1f}%</div>
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
    # High risk shipments list
    high_risk_list = df_fleet[df_fleet['risk_tier'].isin(['CRITICAL', 'HIGH'])]['shipment_id'].tolist()
    if not high_risk_list:
        high_risk_list = df_fleet['shipment_id'].tolist()

    st.markdown("#### 1. Select At-Risk Shipment")
    
    col_sel, col_budget = st.columns([3, 1])
    with col_sel:
        selected_id = st.selectbox(
            "Select shipment needing intervention:",
            options=high_risk_list,
            index=0,
            help="Showing high-risk shipments prioritized by delay probability."
        )
    
    selected_row = df_fleet[df_fleet['shipment_id'] == selected_id].iloc[0]

    with col_budget:
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

    # Clean shipment summary card
    st.markdown(f"""
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:12px 16px; margin: 10px 0 20px 0; display:flex; justify-content:space-between; flex-wrap:wrap; font-size:0.9rem;">
        <div><strong>Shipment:</strong> <code>{selected_row['shipment_id']}</code></div>
        <div><strong>Category:</strong> {selected_row['category_name']}</div>
        <div><strong>Order Total:</strong> ₹{order_total_inr:,.2f}</div>
        <div><strong>Current Mode:</strong> {selected_row['shipping_mode']}</div>
        <div><strong>Predicted Delay:</strong> <span style="color:#dc2626; font-weight:700;">{selected_row['predicted_delay_days']:.1f} days</span></div>
        <div><strong>Status:</strong> <code>{selected_row['current_status']}</code></div>
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
            card_class = "action-card recommended" if is_rec else "action-card"
            badge = '<span class="badge-optimal">RECOMMENDED</span>' if is_rec else ""
            budget_ok = "✅ Within Budget" if p['satisfies_budget'] else "❌ Over Budget"
            cost_inr = p['estimated_cost'] * USD_TO_INR
            savings_inr = p['net_financial_benefit'] * USD_TO_INR

            st.markdown(f"""
            <div class="{card_class}">
                <div>{badge}<strong style="font-size:1.05rem;">{p['title']}</strong></div>
                <div style="color:#64748b; font-size:0.8rem; margin: 4px 0 10px 0;">Strategy: {p['strategy_type']}</div>
                <div style="font-size:0.9rem; line-height:1.6;">
                    <div>• <strong>Expedite Cost:</strong> ₹{cost_inr:,.2f}</div>
                    <div>• <strong>Days Saved:</strong> {p['days_saved']:.1f} days (Remaining: {p['expected_delay_days']:.1f}d)</div>
                    <div>• <strong>SLA Adherence:</strong> {p['sla_compliance_rate']}%</div>
                    <div>• <strong>Net Savings:</strong> <strong style="color:#059669;">+₹{savings_inr:,.2f}</strong></div>
                    <div>• <strong>Projected ROI:</strong> <strong style="color:#2563eb;">{p['roi_pct']:.1f}%</strong></div>
                    <div style="font-size:0.8rem; color:#64748b; margin-top:4px;">{budget_ok} (Cap: ₹{budget_limit_inr:,.0f})</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            btn_type = "primary" if is_rec else "secondary"
            if st.button(f"🚀 Execute {p['title']}", key=f"exec_{p['option_id']}", use_container_width=True, type=btn_type):
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
                    st.success(f"✅ Decision recorded! Shipment status updated to {selected_id}.")
                    st.cache_data.clear()
                    time.sleep(0.4)
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
            height=280
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
        # Mini Chart: Quoted vs Actual Cost (INR)
        df_cost_chart = df_outcomes.head(15).copy()
        df_cost_chart['predicted_cost'] = df_cost_chart['predicted_cost'] * USD_TO_INR
        df_cost_chart['actual_cost'] = df_cost_chart['actual_cost'] * USD_TO_INR
        fig_cost = px.bar(
            df_cost_chart,
            x="shipment_id",
            y=["predicted_cost", "actual_cost"],
            barmode="group",
            title="Quoted vs Realized Expediting Cost in INR (Tracking Carrier Surcharges)",
            labels={"value": "Cost (₹)", "variable": "Cost Type"},
            color_discrete_map={"predicted_cost": "#3b82f6", "actual_cost": "#10b981"}
        )
        fig_cost.update_layout(margin=dict(l=10, r=10, t=35, b=10), height=260)
        st.plotly_chart(fig_cost, use_container_width=True)

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
