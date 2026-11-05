"""
Automated Test Suite for Supply Prescript
Validates Predictive Model, Prescriptive Solver, Transactional Write-Back, and Closed Loop.
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db_manager import initialize_database, get_connection, record_decision_writeback
from models.predictive_model import SupplyChainPredictor
from models.prescriptive_solver import PrescriptiveSolver, run_optimization_audit
from models.closed_loop import ClosedLoopEngine

class TestSupplyPrescriptPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()
        cls.predictor = SupplyChainPredictor()
        cls.has_model = cls.predictor.load()
        cls.solver = PrescriptiveSolver()
        cls.engine = ClosedLoopEngine()

    def test_01_predictive_model_loaded(self):
        """Verify XGBoost models are loaded with valid metrics."""
        self.assertTrue(self.has_model, "Predictor should load pre-trained model.")
        self.assertIn("roc_auc", self.predictor.metrics)
        self.assertGreater(self.predictor.metrics["roc_auc"], 0.65)
        self.assertLess(self.predictor.metrics["mae_days"], 2.0)

    def test_02_prescriptive_solver_logic(self):
        """Verify solver generates candidate options and selects optimal action under budget."""
        order_val = 2500.0
        delay_days = 8.0
        budget = 900.0
        
        result = self.solver.solve_prescriptions(order_val, delay_days, max_budget=budget)
        
        self.assertIn("prescriptions", result)
        self.assertGreaterEqual(len(result["prescriptions"]), 3)
        
        # Verify recommended option satisfies budget
        optimal = next(p for p in result["prescriptions"] if p["is_optimal"])
        self.assertLessEqual(optimal["estimated_cost"], budget)
        self.assertTrue(optimal["satisfies_budget"])

    def test_03_optimization_audit_hard_constraint(self):
        """Audit proof that the solver NEVER recommends an action violating budget constraint."""
        audit = run_optimization_audit(n_trials=50)
        self.assertTrue(audit["audit_passed"])
        self.assertEqual(audit["violations_detected"], 0)
        self.assertEqual(audit["constraint_compliance_rate_pct"], 100.0)

    def test_04_transactional_writeback(self):
        """Verify clicking execute decision successfully performs transactional writeback into DB."""
        test_shipment = "SHP-2026-10001"
        res = record_decision_writeback(
            shipment_id=test_shipment,
            selected_option="OPTION_A",
            option_title="Air Freight Expedite",
            approved_cost=750.0,
            predicted_lead_time_days=0.0,
            operator_id="UnitTester",
            execution_notes="Automated test write-back"
        )
        self.assertEqual(res["status"], "SUCCESS")
        
        # Verify record exists in DB
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM decision_log WHERE shipment_id = ?", (test_shipment,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['selected_option'], "OPTION_A")
            self.assertEqual(float(row['approved_cost']), 750.0)
            
            # Verify shipment status mutated
            cursor.execute("SELECT current_status FROM shipments WHERE shipment_id = ?", (test_shipment,))
            ship_row = cursor.fetchone()
            self.assertEqual(ship_row['current_status'], "INTERVENED_OPTION_A")

    def test_05_closed_loop_evaluation(self):
        """Verify outcomes table records actual costs, variance, and calculates Decision ROI."""
        evaluated = self.engine.simulate_and_evaluate_pending_decisions()
        # Verify analytics calculation
        analytics = self.engine.get_decision_roi_analytics()
        self.assertGreaterEqual(analytics["total_outcomes"], 1)
        self.assertIn("positive_outcome_rate_pct", analytics)
        self.assertIn("avg_decision_roi_pct", analytics)

    def test_06_portfolio_optimization_solver(self):
        """Verify fleet-wide MILP optimizer allocates interventions without violating global budget."""
        test_shipments = [
            {"shipment_id": "SHP-PORT-01", "order_total": 3500.0, "predicted_delay_days": 8.0, "category_name": "Electronics"},
            {"shipment_id": "SHP-PORT-02", "order_total": 1200.0, "predicted_delay_days": 3.0, "category_name": "Apparel"},
            {"shipment_id": "SHP-PORT-03", "order_total": 2800.0, "predicted_delay_days": 6.5, "category_name": "Computers"},
            {"shipment_id": "SHP-PORT-04", "order_total": 950.0,  "predicted_delay_days": 2.0, "category_name": "Footwear"},
            {"shipment_id": "SHP-PORT-05", "order_total": 4200.0, "predicted_delay_days": 9.0, "category_name": "Industrial"}
        ]
        portfolio_budget = 2000.0
        result = self.solver.solve_portfolio_optimization(test_shipments, portfolio_budget=portfolio_budget)
        
        self.assertEqual(result["solver_status"], "Optimal")
        self.assertEqual(result["shipments_count"], 5)
        self.assertLessEqual(result["total_allocated_spend"], portfolio_budget + 1e-4)
        self.assertEqual(len(result["allocations"]), 5)
        self.assertGreater(result["total_loss_prevented"], 0.0)
        
        # Verify each shipment has a valid assigned option
        valid_options = {"STATUS_QUO", "OPTION_A", "OPTION_B", "OPTION_C"}
        for alloc in result["allocations"]:
            self.assertIn(alloc["selected_option"], valid_options)

    def test_07_portfolio_zero_budget_fallback(self):
        """Verify portfolio optimizer defaults to STATUS_QUO when budget is zero."""
        test_shipments = [
            {"shipment_id": "SHP-ZERO-01", "order_total": 2000.0, "predicted_delay_days": 5.0}
        ]
        result = self.solver.solve_portfolio_optimization(test_shipments, portfolio_budget=0.0)
        self.assertEqual(result["total_allocated_spend"], 0.0)
        self.assertEqual(result["allocations"][0]["selected_option"], "STATUS_QUO")

    def test_08_solver_nan_resilience_and_sla_constraint(self):
        """Verify solver gracefully handles NaN/None and enforces max_allowable_delay."""
        # 1. NaN resilience
        res_nan = self.solver.solve_prescriptions(order_total=None, predicted_delay_days=float('nan'))
        self.assertIsNotNone(res_nan["best_recommended_option"])
        self.assertFalse(np.isnan(res_nan["baseline_disruption_cost"]))
        for p in res_nan["prescriptions"]:
            self.assertFalse(np.isnan(p["estimated_cost"]))
            self.assertFalse(np.isnan(p["roi_pct"]))

        # 2. SLA Constraint (max_allowable_delay=0.0 should only allow zero-delay options like OPTION_A)
        res_sla = self.solver.solve_prescriptions(
            order_total=3000.0,
            predicted_delay_days=6.0,
            max_budget=2000.0,
            max_allowable_delay=0.0
        )
        self.assertEqual(res_sla["best_recommended_option"], "OPTION_A")

    def test_09_decision_update_resets_outcome(self):
        """Verify re-deciding a shipment cleanly clears old outcome and allows fresh evaluation."""
        test_ship = "SHP-2026-10002"
        # 1. Initial decision: OPTION_B
        record_decision_writeback(
            shipment_id=test_ship,
            selected_option="OPTION_B",
            option_title="Secondary Supplier Hot-Transfer",
            approved_cost=300.0,
            predicted_lead_time_days=1.0,
            operator_id="Tester1"
        )
        # Evaluate outcome
        self.engine.simulate_and_evaluate_pending_decisions()
        with get_connection() as conn:
            row = conn.cursor().execute("SELECT * FROM outcomes WHERE shipment_id = ?", (test_ship,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(float(row['predicted_cost']), 300.0)

        # 2. Update decision: OPTION_A
        record_decision_writeback(
            shipment_id=test_ship,
            selected_option="OPTION_A",
            option_title="Air Freight Expedite",
            approved_cost=700.0,
            predicted_lead_time_days=0.0,
            operator_id="Tester2"
        )
        # Verify old outcome was purged to prevent stale evaluation mismatch
        with get_connection() as conn:
            row = conn.cursor().execute("SELECT * FROM outcomes WHERE shipment_id = ?", (test_ship,)).fetchone()
            self.assertIsNone(row)

        # Re-evaluate
        evals = self.engine.simulate_and_evaluate_pending_decisions()
        self.assertTrue(any(e["shipment_id"] == test_ship for e in evals))
        with get_connection() as conn:
            row = conn.cursor().execute("SELECT * FROM outcomes WHERE shipment_id = ?", (test_ship,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(float(row['predicted_cost']), 700.0)

    def test_10_status_quo_loss_prevented_zero(self):
        """Verify choosing STATUS_QUO results in 0 financial loss prevented."""
        test_ship = "SHP-2026-10003"
        record_decision_writeback(
            shipment_id=test_ship,
            selected_option="STATUS_QUO",
            option_title="Standard Transit (No Expedite)",
            approved_cost=0.0,
            predicted_lead_time_days=5.0,
            operator_id="Tester3"
        )
        self.engine.simulate_and_evaluate_pending_decisions()
        with get_connection() as conn:
            row = conn.cursor().execute("SELECT * FROM outcomes WHERE shipment_id = ?", (test_ship,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(float(row['actual_cost']), 0.0)
            self.assertEqual(float(row['financial_loss_prevented']), 0.0)
            self.assertEqual(float(row['decision_roi_pct']), 0.0)

    def test_11_predict_disruption_raw_dataframe(self):
        """Verify predictor accepts raw shipment DataFrames with categorical strings."""
        raw_df = pd.DataFrame([{
            'shipping_mode': 'Standard Class',
            'customer_segment': 'Consumer',
            'category_name': 'Electronics',
            'order_region': 'North America',
            'scheduled_shipping_days': 4,
            'product_price': 150.0,
            'order_quantity': 2,
            'order_total': 300.0,
            'benefit_per_order': 50.0
        }])
        proba, days, tiers = self.predictor.predict_disruption(raw_df)
        self.assertEqual(len(proba), 1)
        self.assertTrue(0.0 <= proba[0] <= 1.0)
        self.assertTrue(days[0] >= 0.0)
        self.assertIn(tiers[0], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

    def test_12_fastapi_endpoints(self):
        """Verify all FastAPI REST endpoints execute successfully."""
        from fastapi.testclient import TestClient
        from api.app import app
        client = TestClient(app)

        # Health
        r = client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "HEALTHY")

        # Shipments filter
        r = client.get("/api/shipments?risk_filter=critical&limit=10")
        self.assertEqual(r.status_code, 200)
        self.assertIn("shipments", r.json())

        # Prescriptions
        ship_id = r.json()["shipments"][0]["shipment_id"]
        r = client.get(f"/api/prescriptions/{ship_id}")
        self.assertEqual(r.status_code, 200)
        self.assertIn("optimization_result", r.json())

        # Portfolio optimization with zero budget
        port_res = client.post("/api/prescriptions/portfolio", json={
            "portfolio_budget": 0.0,
            "shipments": [{"shipment_id": "TEST-1", "order_total": 1000.0, "predicted_delay_days": 3.0}]
        })
        self.assertEqual(port_res.status_code, 200)
        self.assertEqual(port_res.json()["total_allocated_spend"], 0.0)

        # Batch write-back
        batch_res = client.post("/api/decisions/batch", json={
            "decisions": [{
                "shipment_id": ship_id,
                "selected_option": "OPTION_C",
                "option_title": "Dynamic Buffer & Re-Routing",
                "approved_cost": 150.0,
                "predicted_lead_time_days": 1.5,
                "operator_id": "ApiBatchTester"
            }]
        })
        self.assertEqual(batch_res.status_code, 200)
        self.assertEqual(batch_res.json()["status"], "SUCCESS")

        # Exports
        self.assertEqual(client.get("/api/export/decisions").status_code, 200)
        self.assertEqual(client.get("/api/export/outcomes").status_code, 200)

    def test_13_continuous_retraining_rescores_pending(self):
        """Verify closed-loop continuous retraining rescores pending shipments in the database."""
        retrain_result = self.engine.trigger_continuous_retraining(force=True)
        self.assertEqual(retrain_result["status"], "RETRAINED")
        self.assertIn("new_version", retrain_result)
        
        # Verify predictions table reflects retrained model version for pending shipments
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.model_version
                FROM predictions p
                JOIN shipments s ON p.shipment_id = s.shipment_id
                WHERE s.current_status = 'PENDING'
                LIMIT 5
            """)
            versions = [row['model_version'] for row in cursor.fetchall()]
            if versions:
                for v in versions:
                    self.assertEqual(v, retrain_result["new_version"])

if __name__ == "__main__":
    unittest.main()
