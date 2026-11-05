"""
Database Seeder Script for Supply Prescript
Seeds active operational shipments, generates XGBoost disruption predictions,
PuLP prescriptive alternatives, and historical closed-loop decisions.
"""

import os
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db_manager import initialize_database, get_connection, seed_shipments_from_df, record_decision_writeback
from data.data_loader import load_and_preprocess_data, prepare_model_features
from models.predictive_model import SupplyChainPredictor
from models.prescriptive_solver import PrescriptiveSolver
from models.closed_loop import ClosedLoopEngine

def seed_complete_operational_environment(force: bool = False):
    """Initializes the operational database and populates active and historical data."""
    print("Initializing operational database...")
    initialize_database()
    
    # Load raw dataset
    df, _ = load_and_preprocess_data()
    
    # 1. Seed shipments
    seeded_count = seed_shipments_from_df(df, limit=350, force=force)
    print(f"Total shipments in DB: {seeded_count}")
    
    # 2. Generate XGBoost predictions
    predictor = SupplyChainPredictor()
    if not predictor.load():
        print("Model not loaded, training baseline...")
        X, y_c, y_r, _ = prepare_model_features(df)
        predictor.train(X, y_c, y_r)
        
    print("Generating disruption predictions for active shipments...")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM predictions")
        existing_pred_count = cursor.fetchone()['cnt']
        
        if existing_pred_count == 0 or force:
            cursor.execute("SELECT * FROM shipments")
            shipments = cursor.fetchall()
            
            # Format dataframe for prediction
            shipment_rows = [dict(s) for s in shipments]
            ship_df = pd.DataFrame(shipment_rows)
            
            proba, days, tiers = predictor.predict_disruption(ship_df)
            
            # Insert predictions
            records = []
            for i, row in enumerate(shipment_rows):
                records.append((
                    row['shipment_id'],
                    float(proba[i]),
                    float(days[i]),
                    tiers[i],
                    predictor.version
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO predictions (
                    shipment_id, delay_probability, predicted_delay_days, risk_tier, model_version
                ) VALUES (?, ?, ?, ?, ?)
            """, records)
            conn.commit()
            print(f"Generated predictions for {len(records)} shipments.")
            
    # 3. Pre-seed a few historical decisions and outcomes to showcase the Closed-Loop & Decision ROI views
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM decision_log")
        existing_decisions = cursor.fetchone()['cnt']
        
        if existing_decisions == 0 or force:
            print("Seeding historical decisions for closed-loop demonstration...")
            # Pick 20 shipments to have completed historical decisions
            cursor.execute("""
                SELECT s.shipment_id, s.order_total, p.predicted_delay_days
                FROM shipments s
                JOIN predictions p ON s.shipment_id = p.shipment_id
                WHERE p.risk_tier IN ('HIGH', 'CRITICAL')
                LIMIT 25
            """)
            high_risk = cursor.fetchall()
            solver = PrescriptiveSolver()
            
            for i, row in enumerate(high_risk):
                shipment_id = row['shipment_id']
                order_total = float(row['order_total'])
                delay_days = float(row['predicted_delay_days'])
                
                sol = solver.solve_prescriptions(order_total, delay_days)
                # Alternate between Option A, Option B, and Option C
                opt_idx = i % 3
                selected = sol['prescriptions'][opt_idx]
                
                record_decision_writeback(
                    shipment_id=shipment_id,
                    selected_option=selected['option_id'],
                    option_title=selected['title'],
                    approved_cost=selected['estimated_cost'],
                    predicted_lead_time_days=selected['expected_delay_days'],
                    operator_id=f"OpsLead_0{1 + (i % 3)}",
                    execution_notes=f"Authorized {selected['strategy_type']} based on Prescriptive Solver."
                )
                
            print("Simulating historical closed-loop outcomes...")
            engine = ClosedLoopEngine()
            evaluated = engine.simulate_and_evaluate_pending_decisions()
            print(f"Evaluated {len(evaluated)} historical outcomes with realized ROI.")

if __name__ == "__main__":
    force_flag = "--force" in sys.argv or "--reset" in sys.argv
    seed_complete_operational_environment(force=force_flag)
