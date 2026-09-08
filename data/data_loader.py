"""
Data Preprocessing and Feature Engineering Module
Transforms raw Kaggle DataCo supply chain records into model-ready features.
"""

import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from typing import Tuple, Dict, Any

DATA_PATH = os.path.join(os.path.dirname(__file__), "supply_chain_data.csv")

def load_and_preprocess_data(csv_path: str = DATA_PATH) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Loads CSV and applies enterprise supply chain feature engineering."""
    df = pd.read_csv(csv_path)
    
    # Standardize column naming
    col_map = {
        'Days for shipping (real)': 'real_shipping_days',
        'Days for shipment (scheduled)': 'scheduled_shipping_days',
        'Late_delivery_risk': 'late_risk',
        'Delivery Status': 'delivery_status',
        'Shipping Mode': 'shipping_mode',
        'Order Status': 'order_status',
        'Order Region': 'order_region',
        'Order Country': 'order_country',
        'Order City': 'order_city',
        'Category Name': 'category_name',
        'Customer Segment': 'customer_segment',
        'Department Name': 'department_name',
        'Product Price': 'product_price',
        'Order Item Quantity': 'order_quantity',
        'Order Item Total': 'order_total',
        'Benefit per order': 'benefit_per_order',
        'Sales per customer': 'sales_per_customer',
        'Delay_Days': 'delay_days'
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    
    # Fill missing values
    df['order_region'] = df['order_region'].fillna('Unknown')
    df['category_name'] = df['category_name'].fillna('General')
    df['shipping_mode'] = df['shipping_mode'].fillna('Standard Class')
    df['customer_segment'] = df['customer_segment'].fillna('Consumer')
    
    # Feature Engineering
    # 1. Lead Time Buffer: difference between real and scheduled
    if 'delay_days' not in df.columns:
        df['delay_days'] = (df['real_shipping_days'] - df['scheduled_shipping_days']).clip(lower=0)
        
    # 2. Cargo Criticality Score (based on unit price and order value)
    df['cargo_value_tier'] = pd.qcut(df['order_total'], q=4, labels=['Low', 'Medium', 'High', 'Critical'])
    
    # 3. Disruption Risk Factor (historical baseline probability proxy)
    mode_risk_map = {
        'Standard Class': 0.60,
        'Second Class': 0.40,
        'First Class': 0.25,
        'Same Day': 0.10
    }
    df['mode_base_risk'] = df['shipping_mode'].map(mode_risk_map).fillna(0.50)
    
    # 4. Estimated Financial Disruption Cost if Delayed:
    # Formula: Baseline SLA penalty ($150) + Daily Late Penalty ($80/day) + 15% of Order Value
    df['disruption_financial_impact'] = np.round(
        150.0 + (df['delay_days'] * 85.0) + (df['order_total'] * 0.12), 2
    )

    metadata = {
        'total_records': len(df),
        'late_shipments': int(df['late_risk'].sum()),
        'late_ratio': float(df['late_risk'].mean()),
        'avg_delay_days': float(df[df['late_risk'] == 1]['delay_days'].mean()) if (df['late_risk'] == 1).any() else 0.0,
        'categories': df['category_name'].unique().tolist(),
        'shipping_modes': df['shipping_mode'].unique().tolist(),
        'regions': df['order_region'].unique().tolist()
    }
    
    return df, metadata

def prepare_model_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series, list]:
    """Encodes features for XGBoost classifier & regressor."""
    feature_cols = [
        'scheduled_shipping_days',
        'product_price',
        'order_quantity',
        'order_total',
        'benefit_per_order',
        'mode_base_risk'
    ]
    
    # Categorical columns to encode
    cat_cols = ['shipping_mode', 'customer_segment', 'category_name', 'order_region']
    
    # Create dummy encoded features
    df_encoded = pd.get_dummies(df[cat_cols], drop_first=True, dtype=float)
    X = pd.concat([df[feature_cols].copy(), df_encoded], axis=1)
    
    y_class = df['late_risk'].astype(int)
    y_reg = df['delay_days'].astype(float)
    
    return X, y_class, y_reg, list(X.columns)

if __name__ == "__main__":
    df, meta = load_and_preprocess_data()
    print("Preprocessed records:", len(df))
    print(f"Late Risk Ratio: {meta['late_ratio']*100:.1f}%")
    X, y_c, y_r, cols = prepare_model_features(df)
    print("Features matrix shape:", X.shape)
