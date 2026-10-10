from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    r2_score, mean_absolute_error, mean_squared_error
)
from pydantic import BaseModel, Field
from atlas.tools.registry import registry
from atlas.analytics.engine import engine

class BuildBaselineModelInput(BaseModel):
    target_column: str = Field(description="Column to predict")
    feature_columns: Optional[List[str]] = Field(default=None, description="Subset of features to use")
    model_type: str = Field(default="auto", description="'auto', 'classification', or 'regression'")
    test_size: float = Field(default=0.2, description="Held-out test set proportion (0.1 to 0.4)")
    random_state: int = Field(default=42, description="Random seed for reproducibility")

@registry.register("build_baseline_model", BuildBaselineModelInput)
def build_baseline_model(
    dataset_id: str,
    target_column: str,
    feature_columns: Optional[List[str]] = None,
    model_type: str = "auto",
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Classification/regression baselines, explicit target, train/test split, preprocessing, and appropriate held-out metrics.
    """
    df = engine.get_dataframe(dataset_id)
    warnings: List[str] = []

    if target_column not in df.columns:
        return {"error": f"Target column '{target_column}' not found in dataset."}, [f"Target {target_column} missing."]

    clean_df = df.dropna(subset=[target_column]).copy()
    y = clean_df[target_column]

    # Auto-detect task
    is_classification = False
    if model_type.lower() == "classification":
        is_classification = True
    elif model_type.lower() == "regression":
        is_classification = False
    else:
        if pd.api.types.is_numeric_dtype(y):
            is_classification = (y.nunique() <= 10)
        else:
            is_classification = True

    # Select features
    if feature_columns:
        feat_cols = [c for c in feature_columns if c in clean_df.columns and c != target_column]
    else:
        feat_cols = [c for c in clean_df.columns if c != target_column]

    if not feat_cols:
        return {"error": "No valid feature columns available."}, ["No features available."]

    X = clean_df[feat_cols]
    num_cols = list(X.select_dtypes(include=[np.number]).columns)
    cat_cols = list(X.select_dtypes(include=[object, "category"]).columns)

    # Preprocessing pipelines
    transformers = []
    if num_cols:
        num_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler())
        ])
        transformers.append(("num", num_pipeline, num_cols))

    if cat_cols:
        cat_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])
        transformers.append(("cat", cat_pipeline, cat_cols))

    preprocessor = ColumnTransformer(transformers=transformers)

    # Train-test split
    try:
        stratify = y if (is_classification and y.value_counts().min() >= 2) else None
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=stratify
        )
    except Exception as e:
        warnings.append(f"Split fallback without stratification: {str(e)}")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

    if is_classification:
        model = RandomForestClassifier(n_estimators=50, random_state=random_state, max_depth=6)
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("classifier", model)
        ])
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        acc = float(accuracy_score(y_test, y_pred))
        f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
        prec = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
        rec = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))

        # Extract feature importances
        feature_names = []
        if num_cols:
            feature_names.extend(num_cols)
        if cat_cols and hasattr(pipeline.named_steps["preprocessor"].named_transformers_["cat"].named_steps["onehot"], "get_feature_names_out"):
            feature_names.extend(list(pipeline.named_steps["preprocessor"].named_transformers_["cat"].named_steps["onehot"].get_feature_names_out(cat_cols)))

        importances = {}
        if hasattr(model, "feature_importances_") and len(feature_names) == len(model.feature_importances_):
            top_indices = np.argsort(model.feature_importances_)[::-1][:10]
            importances = {feature_names[i]: round(float(model.feature_importances_[i]), 4) for i in top_indices}

        return {
            "model_type": "classification",
            "algorithm": "RandomForestClassifier",
            "target": target_column,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "features_used": feat_cols,
            "held_out_metrics": {
                "accuracy": round(acc, 4),
                "f1_weighted": round(f1, 4),
                "precision_weighted": round(prec, 4),
                "recall_weighted": round(rec, 4)
            },
            "feature_importances": importances
        }, warnings

    else:
        y_train_num = pd.to_numeric(y_train, errors="coerce").fillna(0)
        y_test_num = pd.to_numeric(y_test, errors="coerce").fillna(0)

        model = RandomForestRegressor(n_estimators=50, random_state=random_state, max_depth=6)
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("regressor", model)
        ])
        pipeline.fit(X_train, y_train_num)
        y_pred = pipeline.predict(X_test)

        r2 = float(r2_score(y_test_num, y_pred))
        mae = float(mean_absolute_error(y_test_num, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test_num, y_pred)))

        return {
            "model_type": "regression",
            "algorithm": "RandomForestRegressor",
            "target": target_column,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "features_used": feat_cols,
            "held_out_metrics": {
                "r2_score": round(r2, 4),
                "mae": round(mae, 4),
                "rmse": round(rmse, 4)
            }
        }, warnings
