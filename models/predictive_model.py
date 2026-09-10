"""
Predictive Engine for Supply Prescript
Trains and evaluates XGBoost Classifier (delay probability) and Regressor (delay duration)
using historical Kaggle DataCo supply chain features.
"""

import os
import sys
import joblib
import json
import numpy as np
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score, mean_absolute_error, mean_squared_error
from typing import Dict, Any, Tuple, Optional

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "xgboost_classifier.joblib")
REGRESSOR_PATH = os.path.join(MODEL_DIR, "xgboost_regressor.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

class SupplyChainPredictor:
    def __init__(self):
        self.clf: Optional[xgb.XGBClassifier] = None
        self.reg: Optional[xgb.XGBRegressor] = None
        self.feature_columns: list = []
        self.metrics: Dict[str, Any] = {}
        self.version: str = "v1.0.0"
        
    def train(self, X: pd.DataFrame, y_class: pd.Series, y_reg: pd.Series, version: str = "v1.0.0") -> Dict[str, Any]:
        """Trains dual XGBoost models for disruption classification and delay duration regression."""
        self.version = version
        self.feature_columns = list(X.columns)
        
        # Train-test split
        X_train, X_test, y_c_train, y_c_test, y_r_train, y_r_test = train_test_split(
            X, y_class, y_reg, test_size=0.2, random_state=42, stratify=y_class
        )
        
        print("Training XGBoost Classifier for Delay Risk...")
        self.clf = xgb.XGBClassifier(
            n_estimators=120,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42
        )
        self.clf.fit(X_train, y_c_train)
        
        # Classifier Evaluation
        y_c_pred_proba = self.clf.predict_proba(X_test)[:, 1]
        y_c_pred = (y_c_pred_proba >= 0.5).astype(int)
        
        roc_auc = float(roc_auc_score(y_c_test, y_c_pred_proba))
        acc = float(accuracy_score(y_c_test, y_c_pred))
        f1 = float(f1_score(y_c_test, y_c_pred))
        
        print(f"Classifier Results: ROC-AUC={roc_auc:.3f}, Accuracy={acc:.3f}, F1={f1:.3f}")
        
        print("Training XGBoost Regressor for Delay Days Duration...")
        self.reg = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42
        )
        self.reg.fit(X_train, y_r_train)
        
        # Regressor Evaluation
        y_r_pred = self.reg.predict(X_test).clip(min=0)
        mae = float(mean_absolute_error(y_r_test, y_r_pred))
        rmse = float(np.sqrt(mean_squared_error(y_r_test, y_r_pred)))
        
        print(f"Regressor Results: MAE={mae:.2f} days, RMSE={rmse:.2f} days")
        
        # Extract Top 10 Feature Importances
        importances = self.clf.feature_importances_
        sorted_indices = np.argsort(importances)[::-1][:10]
        top_features = [
            {"feature": self.feature_columns[idx], "importance": float(importances[idx])}
            for idx in sorted_indices
        ]
        
        self.metrics = {
            "version": self.version,
            "roc_auc": round(roc_auc, 4),
            "accuracy": round(acc, 4),
            "f1_score": round(f1, 4),
            "mae_days": round(mae, 3),
            "rmse_days": round(rmse, 3),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "top_features": top_features
        }
        
        self.save()
        return self.metrics

    def predict_disruption(self, X_input: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, list]:
        """
        Generates predictions for new shipment records:
        - Delay probability (0.0 to 1.0)
        - Predicted delay days (0.0 to N days)
        - Risk Tier ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
        """
        if self.clf is None or self.reg is None:
            self.load()
            
        # Align columns
        aligned_X = pd.DataFrame(0.0, index=X_input.index, columns=self.feature_columns)
        for col in X_input.columns:
            if col in self.feature_columns:
                aligned_X[col] = X_input[col]
                
        proba = self.clf.predict_proba(aligned_X)[:, 1]
        days = self.reg.predict(aligned_X).clip(min=0)
        
        tiers = []
        for p, d in zip(proba, days):
            if p >= 0.75 or d >= 5.0:
                tiers.append("CRITICAL")
            elif p >= 0.50 or d >= 2.0:
                tiers.append("HIGH")
            elif p >= 0.30:
                tiers.append("MEDIUM")
            else:
                tiers.append("LOW")
                
        return proba, days, tiers

    def save(self) -> None:
        """Serializes models and metadata."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.clf, CLASSIFIER_PATH)
        joblib.dump(self.reg, REGRESSOR_PATH)
        metadata = {
            "version": self.version,
            "feature_columns": self.feature_columns,
            "metrics": self.metrics
        }
        with open(METADATA_PATH, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"Models successfully saved to {MODEL_DIR}")

    def load(self) -> bool:
        """Loads serialized models and metadata."""
        if os.path.exists(CLASSIFIER_PATH) and os.path.exists(REGRESSOR_PATH) and os.path.exists(METADATA_PATH):
            self.clf = joblib.load(CLASSIFIER_PATH)
            self.reg = joblib.load(REGRESSOR_PATH)
            with open(METADATA_PATH, "r") as f:
                metadata = json.load(f)
                self.version = metadata.get("version", "v1.0.0")
                self.feature_columns = metadata.get("feature_columns", [])
                self.metrics = metadata.get("metrics", {})
            return True
        return False

def train_baseline():
    from data.data_loader import load_and_preprocess_data, prepare_model_features
    df, _ = load_and_preprocess_data()
    X, y_c, y_r, _ = prepare_model_features(df)
    predictor = SupplyChainPredictor()
    predictor.train(X, y_c, y_r, version="v1.0.0-baseline")
    return predictor

if __name__ == "__main__":
    train_baseline()
