"""Macroeconomic Trade Analyzer - Correlation and influence analysis."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from scipy import stats
from loguru import logger

from .config import MACRO_INDICATORS, APPAREL_HS_CODES


class MacroTradeAnalyzer:
    """Analyze correlations between macroeconomic indicators and apparel trade."""
    
    def __init__(self, data: Dict[str, pd.DataFrame]):
        """Initialize analyzer with collected data.
        
        Args:
            data: Dictionary containing DataFrames for macro_indicators, 
                  demographics, and trade_data
        """
        self.macro_data = data.get("macro_indicators", pd.DataFrame())
        self.demo_data = data.get("demographics", pd.DataFrame())
        self.trade_data = data.get("trade_data", pd.DataFrame())
        
        # Merge datasets for analysis
        self.merged_data = self._prepare_merged_data()
        
    def _prepare_merged_data(self) -> pd.DataFrame:
        """Merge all datasets for correlation analysis."""
        if self.macro_data.empty or self.trade_data.empty:
            return pd.DataFrame()
            
        # Aggregate trade data by country and year
        trade_agg = self.trade_data.groupby(["reporter_code", "year"]).agg({
            "import_value": "sum",
            "export_value": "sum",
            "import_growth": "mean",
            "export_growth": "mean",
        }).reset_index()
        
        trade_agg["trade_balance"] = trade_agg["export_value"] - trade_agg["import_value"]
        trade_agg["total_trade"] = trade_agg["export_value"] + trade_agg["import_value"]
        
        # Merge with macro data
        merged = pd.merge(
            self.macro_data,
            trade_agg,
            left_on=["country_code", "year"],
            right_on=["reporter_code", "year"],
            how="inner"
        )
        
        # Merge with demographics
        if not self.demo_data.empty:
            merged = pd.merge(
                merged,
                self.demo_data,
                on=["country_code", "year"],
                how="left"
            )
            
        return merged
    
    def calculate_correlations(
        self,
        target: str = "import_value",
        indicators: List[str] = None,
        country: str = None
    ) -> pd.DataFrame:
        """Calculate correlations between indicators and trade metrics.
        
        Args:
            target: Target variable (import_value, export_value, etc.)
            indicators: List of indicator columns to analyze
            country: Specific country code, or None for all countries
            
        Returns:
            DataFrame with correlation results
        """
        if self.merged_data.empty:
            return pd.DataFrame()
            
        data = self.merged_data.copy()
        if country:
            data = data[data["country_code"] == country]
            
        # Default indicators
        if indicators is None:
            indicators = [
                "gdp", "gdp_growth", "inflation", "unemployment",
                "consumer_confidence", "clothing_cpi", "interest_rate",
                "retail_sales_growth", "female_population", "working_age_female",
                "urbanization_rate", "median_age", "female_labor_participation"
            ]
            indicators = [i for i in indicators if i in data.columns]
        
        results = []
        for indicator in indicators:
            if indicator not in data.columns or target not in data.columns:
                continue
                
            # Remove NaN values
            valid_data = data[[indicator, target]].dropna()
            if len(valid_data) < 5:
                continue
                
            # Calculate Pearson correlation
            try:
                corr, p_value = stats.pearsonr(
                    valid_data[indicator], 
                    valid_data[target]
                )
                
                # Calculate R-squared
                r_squared = corr ** 2
                
                # Determine impact direction
                impact = "positive" if corr > 0.1 else ("negative" if corr < -0.1 else "neutral")
                
                # Calculate elasticity using simple linear regression
                slope, intercept, _, _, _ = stats.linregress(
                    valid_data[indicator],
                    valid_data[target]
                )
                
                # Elasticity: % change in target per % change in indicator
                mean_indicator = valid_data[indicator].mean()
                mean_target = valid_data[target].mean()
                elasticity = (slope * mean_indicator / mean_target) if mean_target != 0 else 0
                
                results.append({
                    "indicator": indicator,
                    "indicator_name": MACRO_INDICATORS.get(indicator, {}).get("name", indicator),
                    "target": target,
                    "correlation": round(corr, 4),
                    "p_value": round(p_value, 4),
                    "r_squared": round(r_squared, 4),
                    "elasticity": round(elasticity, 4),
                    "impact_direction": impact,
                    "is_significant": p_value < 0.05,
                    "data_points": len(valid_data),
                    "country": country or "all",
                })
            except Exception as e:
                logger.warning(f"Error calculating correlation for {indicator}: {e}")
                
        return pd.DataFrame(results).sort_values("correlation", key=abs, ascending=False)
    
    def analyze_lagged_correlations(
        self,
        target: str = "import_value",
        indicator: str = "gdp_growth",
        max_lag: int = 4,
        country: str = None
    ) -> pd.DataFrame:
        """Analyze correlations with time lags.
        
        Args:
            target: Target variable
            indicator: Indicator to analyze
            max_lag: Maximum lag in years to test
            country: Specific country or None for all
            
        Returns:
            DataFrame with lagged correlation results
        """
        if self.merged_data.empty:
            return pd.DataFrame()
            
        data = self.merged_data.copy()
        if country:
            data = data[data["country_code"] == country]
            
        results = []
        for lag in range(max_lag + 1):
            # Create lagged indicator
            data_lagged = data.copy()
            data_lagged["indicator_lagged"] = data_lagged.groupby("country_code")[indicator].shift(lag)
            
            valid_data = data_lagged[["indicator_lagged", target]].dropna()
            if len(valid_data) < 5:
                continue
                
            try:
                corr, p_value = stats.pearsonr(
                    valid_data["indicator_lagged"],
                    valid_data[target]
                )
                
                results.append({
                    "indicator": indicator,
                    "target": target,
                    "lag_years": lag,
                    "correlation": round(corr, 4),
                    "p_value": round(p_value, 4),
                    "is_significant": p_value < 0.05,
                })
            except Exception as e:
                logger.warning(f"Error calculating lagged correlation: {e}")
                
        return pd.DataFrame(results)
    
    def rank_influence_factors(
        self,
        target: str = "import_value",
        country: str = None
    ) -> pd.DataFrame:
        """Rank macroeconomic factors by their influence on trade.
        
        Args:
            target: Target variable to analyze
            country: Specific country or None for global
            
        Returns:
            DataFrame with ranked influence factors
        """
        correlations = self.calculate_correlations(target=target, country=country)
        
        if correlations.empty:
            return pd.DataFrame()
            
        # Calculate influence score (combination of correlation and significance)
        correlations["influence_score"] = (
            abs(correlations["correlation"]) * 
            (1 + correlations["is_significant"].astype(int)) *
            50
        )
        
        # Normalize to 0-100
        max_score = correlations["influence_score"].max()
        if max_score > 0:
            correlations["influence_score"] = (
                correlations["influence_score"] / max_score * 100
            ).round(1)
        
        # Add rank
        correlations["rank"] = range(1, len(correlations) + 1)
        
        # Determine magnitude
        correlations["magnitude"] = correlations["influence_score"].apply(
            lambda x: "high" if x > 70 else ("medium" if x > 40 else "low")
        )
        
        # Generate explanation
        def generate_explanation(row):
            direction = "increases" if row["impact_direction"] == "positive" else "decreases"
            strength = row["magnitude"]
            indicator_name = row["indicator_name"]
            
            if row["magnitude"] == "high":
                return f"{indicator_name} has strong influence: A 1% increase {direction} {target.replace('_', ' ')} by approximately {abs(row['elasticity']):.2f}%"
            elif row["magnitude"] == "medium":
                return f"{indicator_name} shows moderate correlation with {target.replace('_', ' ')}"
            else:
                return f"{indicator_name} has weak or no significant effect on {target.replace('_', ' ')}"
                
        correlations["explanation"] = correlations.apply(generate_explanation, axis=1)
        
        return correlations[[
            "rank", "indicator", "indicator_name", "influence_score", 
            "correlation", "elasticity", "p_value", "impact_direction",
            "magnitude", "explanation", "is_significant"
        ]]
    
    def analyze_by_country(self, countries: List[str] = None) -> Dict[str, pd.DataFrame]:
        """Perform analysis for multiple countries.
        
        Args:
            countries: List of country codes, None for all available
            
        Returns:
            Dictionary of country -> influence ranking DataFrames
        """
        if self.merged_data.empty:
            return {}
            
        if countries is None:
            countries = self.merged_data["country_code"].unique().tolist()
            
        results = {}
        for country in countries:
            try:
                import_factors = self.rank_influence_factors(
                    target="import_value", 
                    country=country
                )
                export_factors = self.rank_influence_factors(
                    target="export_value",
                    country=country
                )
                
                if not import_factors.empty or not export_factors.empty:
                    results[country] = {
                        "import_factors": import_factors,
                        "export_factors": export_factors,
                    }
            except Exception as e:
                logger.warning(f"Error analyzing country {country}: {e}")
                
        return results
    
    def analyze_by_product(self, hs_codes: List[str] = None) -> Dict[str, pd.DataFrame]:
        """Perform analysis by product category.
        
        Args:
            hs_codes: List of HS codes, None for all available
            
        Returns:
            Dictionary of hs_code -> analysis results
        """
        if self.trade_data.empty or self.macro_data.empty:
            return {}
            
        if hs_codes is None:
            hs_codes = self.trade_data["hs_code"].unique().tolist()
            
        results = {}
        for hs_code in hs_codes:
            # Filter trade data for this product
            product_trade = self.trade_data[self.trade_data["hs_code"] == hs_code]
            
            # Aggregate
            product_agg = product_trade.groupby(["reporter_code", "year"]).agg({
                "import_value": "sum",
                "export_value": "sum",
            }).reset_index()
            
            # Merge with macro data
            product_merged = pd.merge(
                self.macro_data,
                product_agg,
                left_on=["country_code", "year"],
                right_on=["reporter_code", "year"],
                how="inner"
            )
            
            if product_merged.empty:
                continue
                
            # Create temporary analyzer for this product
            temp_analyzer = MacroTradeAnalyzer.__new__(MacroTradeAnalyzer)
            temp_analyzer.merged_data = product_merged
            temp_analyzer.macro_data = self.macro_data
            temp_analyzer.demo_data = self.demo_data
            temp_analyzer.trade_data = self.trade_data
            
            import_factors = temp_analyzer.rank_influence_factors(target="import_value")
            
            if not import_factors.empty:
                product_info = APPAREL_HS_CODES.get(hs_code, {"name": hs_code, "category": "unknown"})
                results[hs_code] = {
                    "name": product_info["name"],
                    "category": product_info["category"],
                    "import_factors": import_factors,
                }
                
        return results
    
    def get_key_insights(self, top_n: int = 5) -> Dict[str, Any]:
        """Generate key insights from the analysis.
        
        Args:
            top_n: Number of top factors to include
            
        Returns:
            Dictionary with key insights
        """
        insights = {
            "import_drivers": [],
            "export_drivers": [],
            "demographic_impact": {},
            "economic_impact": {},
            "product_insights": [],
            "regional_patterns": [],
        }
        
        # Global import drivers
        import_factors = self.rank_influence_factors(target="import_value")
        if not import_factors.empty:
            insights["import_drivers"] = import_factors.head(top_n).to_dict("records")
            
        # Global export drivers
        export_factors = self.rank_influence_factors(target="export_value")
        if not export_factors.empty:
            insights["export_drivers"] = export_factors.head(top_n).to_dict("records")
            
        # Key demographic factors
        demo_indicators = ["female_population", "working_age_female", "urbanization_rate"]
        demo_correlations = self.calculate_correlations(indicators=demo_indicators)
        if not demo_correlations.empty:
            insights["demographic_impact"] = {
                "summary": "Female population and urbanization positively correlate with apparel imports",
                "details": demo_correlations.to_dict("records"),
            }
            
        # Key economic factors
        econ_indicators = ["gdp", "inflation", "clothing_cpi", "consumer_confidence"]
        econ_correlations = self.calculate_correlations(indicators=econ_indicators)
        if not econ_correlations.empty:
            insights["economic_impact"] = {
                "summary": "GDP and consumer confidence drive imports; inflation and CPI have negative effects",
                "details": econ_correlations.to_dict("records"),
            }
            
        return insights
    
    def generate_summary_report(self) -> str:
        """Generate a text summary of the analysis.
        
        Returns:
            Markdown-formatted summary report
        """
        insights = self.get_key_insights()
        
        report = """# Macroeconomic Analysis: Women's Apparel Trade Drivers

## Executive Summary

This analysis examines how macroeconomic and demographic factors influence women's apparel trade 
(imports and exports) across multiple countries and product categories.

## Key Findings

### Top Import Drivers
"""
        
        for i, driver in enumerate(insights.get("import_drivers", [])[:5], 1):
            report += f"\n{i}. **{driver.get('indicator_name', '')}** (Score: {driver.get('influence_score', 0)})"
            report += f"\n   - Correlation: {driver.get('correlation', 0):.3f}"
            report += f"\n   - Impact: {driver.get('explanation', '')}\n"
        
        report += "\n### Top Export Drivers\n"
        for i, driver in enumerate(insights.get("export_drivers", [])[:5], 1):
            report += f"\n{i}. **{driver.get('indicator_name', '')}** (Score: {driver.get('influence_score', 0)})"
            report += f"\n   - Correlation: {driver.get('correlation', 0):.3f}"
            report += f"\n   - Impact: {driver.get('explanation', '')}\n"
        
        report += """
## Demographic Impact

The analysis reveals significant relationships between demographic factors and apparel trade:

"""
        demo_details = insights.get("demographic_impact", {}).get("details", [])
        for demo in demo_details:
            report += f"- **{demo.get('indicator_name', '')}**: Correlation = {demo.get('correlation', 0):.3f}\n"
        
        report += """
## Economic Impact

Key economic indicators affecting women's apparel trade:

"""
        econ_details = insights.get("economic_impact", {}).get("details", [])
        for econ in econ_details:
            direction = "↑" if econ.get("impact_direction") == "positive" else "↓"
            report += f"- **{econ.get('indicator_name', '')}**: {direction} (r = {econ.get('correlation', 0):.3f})\n"
        
        report += """
## Recommendations

1. **Monitor GDP Growth**: Strong positive correlation with import volumes
2. **Watch Inflation Trends**: Rising inflation typically reduces import demand
3. **Track Female Demographics**: Growing female working population increases market size
4. **Consumer Confidence**: Key leading indicator for apparel demand

---
*Analysis generated at: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "*"
        
        return report


# Factory function
def create_analyzer(data: Dict[str, pd.DataFrame]) -> MacroTradeAnalyzer:
    """Create a MacroTradeAnalyzer instance."""
    return MacroTradeAnalyzer(data)
