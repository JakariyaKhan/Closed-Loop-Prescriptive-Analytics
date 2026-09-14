"""
FastAPI Operational Service & Write-Back API for Supply Prescript
Provides transactional REST endpoints for prescriptive decision execution,
audit trails, and closed-loop continuous learning.
"""

import os
import sys
from fastapi import FastAPI, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.db_manager import get_connection, record_decision_writeback
from models.predictive_model import SupplyChainPredictor
from models.prescriptive_solver import PrescriptiveSolver, run_optimization_audit
from models.closed_loop import ClosedLoopEngine

app = FastAPI(
    title="Supply Prescript - Operational API",
    description="Transactional Closed-Loop Prescriptive Analytics Service for Supply Chain Operations",
    version="1.0.0"
)

class DecisionPayload(BaseModel):
    shipment_id: str = Field(..., example="SHP-2026-10042")
    selected_option: str = Field(..., example="OPTION_A")
    option_title: str = Field(..., example="Air Freight Expedite")
    approved_cost: float = Field(..., example=650.0)
    predicted_lead_time_days: float = Field(..., example=0.0)
    operator_id: str = Field(default="LogisticsManager_01", example="LogisticsManager_01")
    execution_notes: Optional[str] = Field(default="Approved via Operational Dashboard", example="Prioritized for high-tier customer")

@app.get("/api/health")
def health_check():
    predictor = SupplyChainPredictor()
    predictor.load()
    return {
        "status": "HEALTHY",
        "system": "Supply Prescript Engine",
        "model_version": predictor.version,
        "metrics": predictor.metrics
    }

@app.get("/api/shipments")
def get_shipments(
    risk_filter: Optional[str] = Query(None, description="Filter by risk tier: CRITICAL, HIGH, MEDIUM, LOW"),
    status_filter: Optional[str] = Query(None, description="Filter by status: PENDING, INTERVENED"),
    limit: int = Query(50, ge=1, le=200)
):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT s.*, p.delay_probability, p.predicted_delay_days, p.risk_tier,
                   d.selected_option, d.execution_timestamp, d.approved_cost as intervened_cost
            FROM shipments s
            LEFT JOIN predictions p ON s.shipment_id = p.shipment_id
            LEFT JOIN decision_log d ON s.shipment_id = d.shipment_id
            WHERE 1=1
        """
        params = []
        if risk_filter:
            query += " AND p.risk_tier = ?"
            params.append(risk_filter)
        if status_filter:
            if status_filter == "PENDING":
                query += " AND s.current_status = 'PENDING'"
            else:
                query += " AND s.current_status LIKE 'INTERVENED%'"
                
        query += " ORDER BY p.delay_probability DESC, s.order_total DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        return {"count": len(rows), "shipments": rows}

@app.get("/api/prescriptions/{shipment_id}")
def get_prescriptions(
    shipment_id: str,
    max_budget: Optional[float] = Query(None, description="Optional custom budget constraint cap"),
    max_delay_days: Optional[float] = Query(None, description="Optional max allowable delay constraint")
):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, p.delay_probability, p.predicted_delay_days, p.risk_tier
            FROM shipments s
            LEFT JOIN predictions p ON s.shipment_id = p.shipment_id
            WHERE s.shipment_id = ?
        """, (shipment_id,))
        shipment = cursor.fetchone()
        
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")
        
    ship_dict = dict(shipment)
    solver = PrescriptiveSolver()
    result = solver.solve_prescriptions(
        order_total=float(ship_dict['order_total']),
        predicted_delay_days=float(ship_dict['predicted_delay_days'] or 3.0),
        max_budget=max_budget,
        max_allowable_delay=max_delay_days
    )
    return {
        "shipment_id": shipment_id,
        "order_details": {
            "shipping_mode": ship_dict['shipping_mode'],
            "category_name": ship_dict['category_name'],
            "order_total": ship_dict['order_total'],
            "risk_tier": ship_dict['risk_tier'],
            "predicted_delay_days": ship_dict['predicted_delay_days']
        },
        "optimization_result": result
    }

@app.post("/api/decisions")
def execute_decision_writeback(payload: DecisionPayload):
    """
    ACID Transactional write-back endpoint executing an operational decision
    and mutating the underlying database.
    """
    try:
        res = record_decision_writeback(
            shipment_id=payload.shipment_id,
            selected_option=payload.selected_option,
            option_title=payload.option_title,
            approved_cost=payload.approved_cost,
            predicted_lead_time_days=payload.predicted_lead_time_days,
            operator_id=payload.operator_id,
            execution_notes=payload.execution_notes
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/roi")
def get_roi_analytics():
    engine = ClosedLoopEngine()
    analytics = engine.get_decision_roi_analytics()
    return analytics

@app.get("/api/audit/optimization")
def audit_optimization(trials: int = Query(100, ge=10, le=500)):
    """Validates that solver never violates business budget constraints."""
    result = run_optimization_audit(n_trials=trials)
    return result

@app.post("/api/retrain")
def trigger_continuous_retrain():
    """Triggers closed-loop retraining pipeline based on outcome discrepancies."""
    engine = ClosedLoopEngine()
    result = engine.trigger_continuous_retraining()
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
