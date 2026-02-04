"""Trade Predictor - Predict apparel trade based on macroeconomic indicators."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date
from loguru import logger
from scipy import stats

try:
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge, Lasso, ElasticNet
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available. Using simple linear regression.")

from .config import MACRO_INDICATORS, APPAREL_HS_CODES, ANALYSIS_COUNTRIES


class TradePredictor:
    """Predict women's apparel trade volumes based on macroeconomic factors."""
    
    def __init__(self, data: Dict[str, pd.DataFrame]):
        """Initialize predictor with historical data.
        
        Args:
            data: Dictionary containing DataFrames for macro_indicators,
                  demographics, and trade_data
        """
        self.macro_data = data.get("macro_indicators", pd.DataFrame())
        self.demo_data = data.get("demographics", pd.DataFrame())
        self.trade_data = data.get("trade_data", pd.DataFrame())
        
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        
        # Prepare training data
        self.training_data = self._prepare_training_data()
        
    def _prepare_training_data(self) -> pd.DataFrame:
        """Prepare merged training data."""
        if self.macro_data.empty or self.trade_data.empty:
            return pd.DataFrame()
            
        # Aggregate trade data
        trade_agg = self.trade_data.groupby(["reporter_code", "year"]).agg({
            "import_value": "sum",
            "export_value": "sum",
        }).reset_index()
        
        # Calculate year-over-year growth
        trade_agg = trade_agg.sort_values(["reporter_code", "year"])
        trade_agg["import_growth"] = trade_agg.groupby("reporter_code")["import_value"].pct_change() * 100
        trade_agg["export_growth"] = trade_agg.groupby("reporter_code")["export_value"].pct_change() * 100
        
        # Merge all data
        merged = pd.merge(
            self.macro_data,
            trade_agg,
            left_on=["country_code", "year"],
            right_on=["reporter_code", "year"],
            how="inner"
        )
        
        if not self.demo_data.empty:
            merged = pd.merge(
                merged,
                self.demo_data,
                on=["country_code", "year"],
                how="left"
            )
            
        return merged.dropna()
    
    def get_feature_columns(self) -> List[str]:
        """Get list of feature columns for training."""
        potential_features = [
            "gdp", "gdp_growth", "inflation", "unemployment",
            "consumer_confidence", "clothing_cpi", "interest_rate",
            "retail_sales_growth", "female_population", "working_age_female",
            "urbanization_rate", "median_age", "female_labor_participation",
            "total_population", "female_ratio"
        ]
        
        available = [f for f in potential_features if f in self.training_data.columns]
        return available
    
    def train_model(
        self,
        target: str = "import_value",
        model_type: str = "gradient_boosting",
        country: str = None
    ) -> Dict[str, Any]:
        """Train a prediction model.
        
        Args:
            target: Target variable (import_value, export_value, import_growth, export_growth)
            model_type: Type of model (linear, ridge, random_forest, gradient_boosting)
            country: Specific country or None for global model
            
        Returns:
            Dictionary with training results
        """
        if self.training_data.empty:
            return {"error": "No training data available"}
            
        data = self.training_data.copy()
        if country:
            data = data[data["country_code"] == country]
            
        if len(data) < 10:
            return {"error": f"Insufficient data points: {len(data)}"}
            
        # Prepare features
        feature_cols = self.get_feature_columns()
        X = data[feature_cols].fillna(data[feature_cols].mean())
        y = data[target]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Select and train model
        if not SKLEARN_AVAILABLE:
            model_type = "simple_linear"
            
        if model_type == "linear":
            from sklearn.linear_model import LinearRegression
            model = LinearRegression()
        elif model_type == "ridge":
            model = Ridge(alpha=1.0)
        elif model_type == "lasso":
            model = Lasso(alpha=0.1)
        elif model_type == "random_forest":
            model = RandomForestRegressor(n_estimators=100, random_state=42)
        elif model_type == "gradient_boosting":
            model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        else:
            model = Ridge(alpha=1.0)
            
        # Train
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred_train = model.predict(X_train_scaled)
        y_pred_test = model.predict(X_test_scaled)
        
        train_r2 = r2_score(y_train, y_pred_train)
        test_r2 = r2_score(y_test, y_pred_test)
        test_mae = mean_absolute_error(y_test, y_pred_test)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        
        # MAPE (avoiding division by zero)
        mape = np.mean(np.abs((y_test - y_pred_test) / y_test.replace(0, np.nan).dropna())) * 100
        
        # Feature importance
        if hasattr(model, "feature_importances_"):
            importance = dict(zip(feature_cols, model.feature_importances_))
        elif hasattr(model, "coef_"):
            importance = dict(zip(feature_cols, np.abs(model.coef_)))
        else:
            importance = {}
            
        # Sort by importance
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        
        # Store model
        model_key = f"{target}_{country or 'global'}_{model_type}"
        self.models[model_key] = model
        self.scalers[model_key] = scaler
        self.feature_importance[model_key] = importance
        
        return {
            "model_key": model_key,
            "model_type": model_type,
            "target": target,
            "country": country or "global",
            "metrics": {
                "train_r2": round(train_r2, 4),
                "test_r2": round(test_r2, 4),
                "test_mae": round(test_mae, 2),
                "test_rmse": round(test_rmse, 2),
                "mape": round(mape, 2),
            },
            "feature_importance": importance,
            "data_points": len(data),
            "features_used": feature_cols,
        }
    
    def predict(
        self,
        model_key: str,
        input_data: Dict[str, float]
    ) -> Dict[str, Any]:
        """Make prediction using trained model.
        
        Args:
            model_key: Key of trained model
            input_data: Dictionary of feature values
            
        Returns:
            Prediction result with confidence intervals
        """
        if model_key not in self.models:
            return {"error": f"Model not found: {model_key}"}
            
        model = self.models[model_key]
        scaler = self.scalers[model_key]
        
        # Prepare input
        feature_cols = self.get_feature_columns()
        input_df = pd.DataFrame([input_data])
        
        # Fill missing features with mean values from training data
        for col in feature_cols:
            if col not in input_df.columns:
                input_df[col] = self.training_data[col].mean()
                
        X = input_df[feature_cols]
        X_scaled = scaler.transform(X)
        
        # Predict
        prediction = model.predict(X_scaled)[0]
        
        # Estimate confidence interval (simplified)
        # Using historical standard deviation
        target = model_key.split("_")[0]
        if target in self.training_data.columns:
            std = self.training_data[target].std()
            ci_lower = prediction - 1.96 * std * 0.2  # Simplified CI
            ci_upper = prediction + 1.96 * std * 0.2
        else:
            ci_lower = prediction * 0.85
            ci_upper = prediction * 1.15
        
        return {
            "prediction": round(prediction, 2),
            "confidence_interval": {
                "lower": round(ci_lower, 2),
                "upper": round(ci_upper, 2),
            },
            "model_key": model_key,
            "input_features": input_data,
        }
    
    def predict_by_country(
        self,
        country: str,
        scenario: Dict[str, float],
        targets: List[str] = None
    ) -> Dict[str, Any]:
        """Make predictions for a specific country given economic scenario.
        
        Args:
            country: Country code
            scenario: Dictionary of predicted/assumed macro indicators
            targets: List of targets to predict
            
        Returns:
            Predictions for all targets
        """
        if targets is None:
            targets = ["import_value", "export_value", "import_growth", "export_growth"]
            
        results = {"country": country, "scenario": scenario, "predictions": {}}
        
        for target in targets:
            # Try country-specific model first
            model_key = f"{target}_{country}_gradient_boosting"
            if model_key not in self.models:
                # Train if not exists
                train_result = self.train_model(target=target, country=country)
                if "error" in train_result:
                    # Try global model
                    model_key = f"{target}_global_gradient_boosting"
                    if model_key not in self.models:
                        self.train_model(target=target, country=None)
                        
            if model_key in self.models:
                pred = self.predict(model_key, scenario)
                results["predictions"][target] = pred
                
        return results
    
    def scenario_analysis(
        self,
        base_scenario: Dict[str, float],
        changes: Dict[str, List[float]],
        target: str = "import_value"
    ) -> pd.DataFrame:
        """Analyze impact of changing one variable at a time.
        
        Args:
            base_scenario: Base case values for all features
            changes: Dictionary of feature -> list of values to test
            target: Target variable to predict
            
        Returns:
            DataFrame with scenario analysis results
        """
        model_key = f"{target}_global_gradient_boosting"
        if model_key not in self.models:
            self.train_model(target=target)
            
        results = []
        
        # Base prediction
        base_pred = self.predict(model_key, base_scenario)
        results.append({
            "scenario": "Base",
            "changed_variable": None,
            "value": None,
            "prediction": base_pred.get("prediction", 0),
            "change_from_base": 0,
            "pct_change": 0,
        })
        
        # Analyze each change
        for feature, values in changes.items():
            for value in values:
                scenario = base_scenario.copy()
                scenario[feature] = value
                
                pred = self.predict(model_key, scenario)
                pred_value = pred.get("prediction", 0)
                base_value = base_pred.get("prediction", 0)
                
                change = pred_value - base_value
                pct_change = (change / base_value * 100) if base_value != 0 else 0
                
                results.append({
                    "scenario": f"{feature}={value}",
                    "changed_variable": feature,
                    "value": value,
                    "prediction": pred_value,
                    "change_from_base": round(change, 2),
                    "pct_change": round(pct_change, 2),
                })
                
        return pd.DataFrame(results)
    
    def forecast_growth(
        self,
        years_ahead: int = 3,
        countries: List[str] = None,
        gdp_growth_assumption: float = 2.5,
        inflation_assumption: float = 2.0
    ) -> pd.DataFrame:
        """Forecast trade growth for upcoming years.
        
        Args:
            years_ahead: Number of years to forecast
            countries: List of countries, None for all
            gdp_growth_assumption: Assumed annual GDP growth
            inflation_assumption: Assumed inflation rate
            
        Returns:
            DataFrame with forecasts
        """
        if countries is None:
            countries = self.training_data["country_code"].unique().tolist()
            
        current_year = datetime.now().year
        forecasts = []
        
        for country in countries:
            # Get latest data for country
            country_data = self.training_data[
                self.training_data["country_code"] == country
            ].sort_values("year")
            
            if country_data.empty:
                continue
                
            latest = country_data.iloc[-1]
            
            for year_offset in range(1, years_ahead + 1):
                forecast_year = current_year + year_offset
                
                # Project forward (simplified)
                scenario = {
                    "gdp": latest["gdp"] * (1 + gdp_growth_assumption/100) ** year_offset,
                    "gdp_growth": gdp_growth_assumption,
                    "inflation": inflation_assumption,
                    "unemployment": latest.get("unemployment", 5),
                    "consumer_confidence": latest.get("consumer_confidence", 100),
                    "clothing_cpi": latest.get("clothing_cpi", 100) * (1 + inflation_assumption/100) ** year_offset,
                    "interest_rate": latest.get("interest_rate", 3),
                    "female_population": latest.get("female_population", 50) * 1.008 ** year_offset,
                    "working_age_female": latest.get("working_age_female", 30) * 1.005 ** year_offset,
                    "urbanization_rate": min(90, latest.get("urbanization_rate", 70) + 0.5 * year_offset),
                }
                
                # Get predictions
                predictions = self.predict_by_country(country, scenario)
                
                forecasts.append({
                    "country_code": country,
                    "year": forecast_year,
                    "gdp_growth_assumption": gdp_growth_assumption,
                    "inflation_assumption": inflation_assumption,
                    "predicted_import_value": predictions.get("predictions", {}).get("import_value", {}).get("prediction"),
                    "predicted_export_value": predictions.get("predictions", {}).get("export_value", {}).get("prediction"),
                    "predicted_import_growth": predictions.get("predictions", {}).get("import_growth", {}).get("prediction"),
                    "predicted_export_growth": predictions.get("predictions", {}).get("export_growth", {}).get("prediction"),
                })
                
        return pd.DataFrame(forecasts)
    
    def get_prediction_summary(self) -> Dict[str, Any]:
        """Get summary of all trained models and their performance.
        
        Returns:
            Summary of models and key metrics
        """
        summary = {
            "models_trained": list(self.models.keys()),
            "feature_importance_summary": {},
            "best_performing_models": [],
        }
        
        # Aggregate feature importance across all models
        all_importance = {}
        for model_key, importance in self.feature_importance.items():
            for feature, score in importance.items():
                if feature not in all_importance:
                    all_importance[feature] = []
                all_importance[feature].append(score)
                
        # Average importance
        summary["feature_importance_summary"] = {
            feature: round(np.mean(scores), 4)
            for feature, scores in all_importance.items()
        }
        summary["feature_importance_summary"] = dict(
            sorted(summary["feature_importance_summary"].items(), 
                   key=lambda x: x[1], reverse=True)
        )
        
        return summary


class SimpleLinearPredictor:
    """Fallback predictor using simple linear regression."""
    
    def __init__(self, data: Dict[str, pd.DataFrame]):
        self.data = data
        self.coefficients = {}
        
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train using simple linear regression."""
        # Add intercept
        X_with_intercept = np.column_stack([np.ones(len(X)), X])
        
        # Solve normal equation
        try:
            coeffs = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
            return {
                "intercept": coeffs[0],
                "coefficients": coeffs[1:].tolist(),
            }
        except Exception as e:
            logger.error(f"Error in linear regression: {e}")
            return {}
    
    def predict(self, X: np.ndarray, coeffs: Dict) -> np.ndarray:
        """Make predictions."""
        intercept = coeffs.get("intercept", 0)
        coef = np.array(coeffs.get("coefficients", []))
        return intercept + X @ coef


# Factory function
def create_predictor(data: Dict[str, pd.DataFrame]) -> TradePredictor:
    """Create a TradePredictor instance."""
    return TradePredictor(data)
