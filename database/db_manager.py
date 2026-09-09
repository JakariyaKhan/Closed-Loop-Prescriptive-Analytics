"""
Operational Database Manager for Supply Prescript
Handles SQLite transactional storage, operational write-backs, and audit trails.
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "supply_prescript.db")

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def initialize_database(db_path: str = DB_PATH) -> None:
    """Initializes the operational database schema."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Shipments Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            shipment_id TEXT PRIMARY KEY,
            shipping_mode TEXT NOT NULL,
            category_name TEXT NOT NULL,
            order_region TEXT NOT NULL,
            customer_segment TEXT NOT NULL,
            scheduled_shipping_days INTEGER NOT NULL,
            product_price REAL NOT NULL,
            order_quantity INTEGER NOT NULL,
            order_total REAL NOT NULL,
            benefit_per_order REAL NOT NULL,
            real_shipping_days INTEGER,
            actual_delay_days INTEGER,
            ground_truth_late INTEGER,
            current_status TEXT DEFAULT 'PENDING'
        );
        """)
        
        # 2. Predictive Insights Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT NOT NULL UNIQUE,
            delay_probability REAL NOT NULL,
            predicted_delay_days REAL NOT NULL,
            risk_tier TEXT NOT NULL,
            model_version TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE
        );
        """)
        
        # 3. Prescriptive Interventions Table (PuLP/SciPy solutions)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT NOT NULL,
            option_id TEXT NOT NULL,          -- 'OPTION_A', 'OPTION_B', 'OPTION_C'
            option_title TEXT NOT NULL,
            strategy_type TEXT NOT NULL,
            estimated_cost REAL NOT NULL,
            days_saved REAL NOT NULL,
            expected_delay_days REAL NOT NULL,
            sla_compliance_rate REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
            UNIQUE(shipment_id, option_id)
        );
        """)
        
        # 4. Decision Log (Transactional Write-Back)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_log (
            decision_id TEXT PRIMARY KEY,
            shipment_id TEXT NOT NULL,
            selected_option TEXT NOT NULL,
            option_title TEXT NOT NULL,
            approved_cost REAL NOT NULL,
            predicted_lead_time_days REAL NOT NULL,
            operator_id TEXT NOT NULL,
            execution_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            execution_notes TEXT,
            lifecycle_status TEXT DEFAULT 'ACTIVE',  -- 'ACTIVE', 'IN_PROGRESS', 'RESOLVED'
            FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE
        );
        """)
        
        # 5. Closed-Loop Outcomes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS outcomes (
            outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT NOT NULL UNIQUE,
            shipment_id TEXT NOT NULL,
            predicted_cost REAL NOT NULL,
            actual_cost REAL NOT NULL,
            cost_variance REAL NOT NULL,
            predicted_delay_days REAL NOT NULL,
            actual_delay_days REAL NOT NULL,
            delay_variance REAL NOT NULL,
            sla_breached INTEGER DEFAULT 0,
            decision_roi_pct REAL NOT NULL,
            financial_loss_prevented REAL NOT NULL,
            evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            feedback_status TEXT DEFAULT 'UNREVIEWED', -- 'UNREVIEWED', 'LEARNED'
            FOREIGN KEY (decision_id) REFERENCES decision_log(decision_id) ON DELETE CASCADE
        );
        """)
        
        # 6. Audit Trail Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            entity_id TEXT,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        conn.commit()
    print(f"Operational database successfully initialized at {db_path}")

def seed_shipments_from_df(df: pd.DataFrame, limit: int = 500, db_path: str = DB_PATH) -> int:
    """Populates operational shipments table with sample records from preprocessed dataset."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM shipments")
        if cursor.fetchone()['count'] > 0:
            print("Database already contains operational shipments.")
            return cursor.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]

        insert_query = """
        INSERT OR IGNORE INTO shipments (
            shipment_id, shipping_mode, category_name, order_region, customer_segment,
            scheduled_shipping_days, product_price, order_quantity, order_total,
            benefit_per_order, real_shipping_days, actual_delay_days, ground_truth_late, current_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        records = []
        sample_df = df.head(limit)
        for _, row in sample_df.iterrows():
            records.append((
                str(row['Shipment_ID']),
                str(row.get('shipping_mode', 'Standard Class')),
                str(row.get('category_name', 'General')),
                str(row.get('order_region', 'North America')),
                str(row.get('customer_segment', 'Consumer')),
                int(row.get('scheduled_shipping_days', 4)),
                float(row.get('product_price', 100.0)),
                int(row.get('order_quantity', 1)),
                float(row.get('order_total', 100.0)),
                float(row.get('benefit_per_order', 25.0)),
                int(row.get('real_shipping_days', 4)),
                int(row.get('delay_days', 0)),
                int(row.get('late_risk', 0)),
                'PENDING'
            ))
            
        cursor.executemany(insert_query, records)
        conn.commit()
        
        # Log audit
        cursor.execute(
            "INSERT INTO audit_log (action_type, entity_id, details) VALUES (?, ?, ?)",
            ("SEED_DATA", "SYSTEM", f"Seeded {len(records)} shipments into operational database.")
        )
        conn.commit()
        print(f"Seeded {len(records)} shipments.")
        return len(records)

def record_decision_writeback(
    shipment_id: str,
    selected_option: str,
    option_title: str,
    approved_cost: float,
    predicted_lead_time_days: float,
    operator_id: str = "LogisticsManager_01",
    execution_notes: str = "Prescription executed via Operational UI"
) -> Dict[str, Any]:
    """
    Executes an ACID transactional write-back into the operational database.
    Updates the shipment status and logs the intervention decision.
    """
    decision_id = f"DEC-{int(datetime.now(timezone.utc).timestamp())}-{shipment_id[-5:]}"
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Check if already decided
        cursor.execute("SELECT decision_id FROM decision_log WHERE shipment_id = ?", (shipment_id,))
        existing = cursor.fetchone()
        if existing:
            # Update existing
            cursor.execute("""
            UPDATE decision_log
            SET selected_option = ?, option_title = ?, approved_cost = ?,
                predicted_lead_time_days = ?, operator_id = ?, execution_notes = ?,
                execution_timestamp = CURRENT_TIMESTAMP
            WHERE shipment_id = ?
            """, (selected_option, option_title, approved_cost, predicted_lead_time_days, operator_id, execution_notes, shipment_id))
            decision_id = existing['decision_id']
        else:
            # Insert transactional record
            cursor.execute("""
            INSERT INTO decision_log (
                decision_id, shipment_id, selected_option, option_title,
                approved_cost, predicted_lead_time_days, operator_id, execution_notes, lifecycle_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (decision_id, shipment_id, selected_option, option_title, approved_cost, predicted_lead_time_days, operator_id, execution_notes, 'ACTIVE'))
        
        # Update shipment status
        cursor.execute(
            "UPDATE shipments SET current_status = ? WHERE shipment_id = ?",
            (f"INTERVENED_{selected_option}", shipment_id)
        )
        
        # Record audit log
        cursor.execute(
            "INSERT INTO audit_log (action_type, entity_id, details) VALUES (?, ?, ?)",
            ("WRITEBACK_DECISION", decision_id, f"Executed {selected_option} for {shipment_id} (Cost: ${approved_cost:.2f})")
        )
        
        conn.commit()
        
    return {
        "status": "SUCCESS",
        "decision_id": decision_id,
        "shipment_id": shipment_id,
        "selected_option": selected_option,
        "approved_cost": approved_cost,
        "message": f"Decision {decision_id} written back to operational database."
    }

if __name__ == "__main__":
    initialize_database()
