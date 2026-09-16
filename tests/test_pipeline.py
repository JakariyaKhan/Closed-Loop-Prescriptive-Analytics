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

if __name__ == "__main__":
    unittest.main()
