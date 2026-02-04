"""FastAPI endpoints for Macroeconomic Trade Analyzer."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
import asyncio

from .data_collector import get_collector, MacroDataCollector
from .analyzer import MacroTradeAnalyzer, create_analyzer
from .predictor import TradePredictor, create_predictor
from .llm_insights import MacroInsightsGenerator, create_insights_generator
from .config import ANALYSIS_COUNTRIES, MACRO_INDICATORS, APPAREL_HS_CODES


router = APIRouter(prefix="/macro", tags=["Macroeconomic Analysis"])

# Global state
_data_cache: Dict[str, Any] = {}
_analyzer: Optional[MacroTradeAnalyzer] = None
_predictor: Optional[TradePredictor] = None
_insights_generator: Optional[MacroInsightsGenerator] = None


class ScenarioInput(BaseModel):
    """Input for scenario analysis."""
    gdp: float = Field(default=1000, description="GDP in billion USD")
    gdp_growth: float = Field(default=2.5, description="GDP growth rate %")
    inflation: float = Field(default=2.0, description="Inflation rate %")
    unemployment: float = Field(default=5.0, description="Unemployment rate %")
    consumer_confidence: float = Field(default=100, description="Consumer confidence index")
    clothing_cpi: float = Field(default=100, description="Clothing CPI index")
    interest_rate: float = Field(default=3.0, description="Interest rate %")
    female_population: float = Field(default=50, description="Female population in millions")
    working_age_female: float = Field(default=30, description="Working age female population in millions")
    urbanization_rate: float = Field(default=70, description="Urbanization rate %")


class ForecastRequest(BaseModel):
    """Request for trade forecast."""
    years_ahead: int = Field(default=3, ge=1, le=10)
    countries: Optional[List[str]] = None
    gdp_growth_assumption: float = Field(default=2.5, ge=-10, le=20)
    inflation_assumption: float = Field(default=2.0, ge=-5, le=30)


def get_analyzer() -> MacroTradeAnalyzer:
    """Get or create analyzer instance (requires data to be collected first)."""
    global _analyzer, _data_cache
    
    if _analyzer is None and _data_cache:
        _analyzer = create_analyzer(_data_cache)
        
    return _analyzer


def get_predictor() -> TradePredictor:
    """Get or create predictor instance."""
    global _predictor, _data_cache
    
    if _predictor is None:
        if not _data_cache:
            get_analyzer()  # This will populate _data_cache
        _predictor = create_predictor(_data_cache)
        
    return _predictor


def get_insights() -> MacroInsightsGenerator:
    """Get or create insights generator."""
    global _insights_generator
    
    if _insights_generator is None:
        _insights_generator = create_insights_generator()
        
    return _insights_generator


@router.get("/status")
async def get_status():
    """Get analyzer status and configuration."""
    return {
        "status": "ready",
        "countries_available": len(ANALYSIS_COUNTRIES),
        "indicators_available": len(MACRO_INDICATORS),
        "product_categories": len(APPAREL_HS_CODES),
        "data_loaded": bool(_data_cache),
        "analyzer_ready": _analyzer is not None,
        "predictor_ready": _predictor is not None,
    }


@router.post("/collect")
async def collect_data(
    countries: Optional[List[str]] = None,
    start_year: int = 2015,
    end_year: Optional[int] = None
):
    """Collect real macroeconomic data from World Bank API.
    
    Data Sources:
    - World Bank Open Data API (free, no API key required)
    - UN Comtrade (limited free access)
    
    This fetches real economic indicators including GDP, inflation,
    population, trade data, and more for the specified countries.
    """
    global _data_cache, _analyzer, _predictor
    
    try:
        collector = get_collector()
        
        logger.info(f"Starting real data collection from World Bank API...")
        data = await collector.collect_all_real_data(
            countries=countries,
            start_year=start_year,
            end_year=end_year
        )
        
        _data_cache = data
        _analyzer = create_analyzer(data)
        _predictor = create_predictor(data)
        
        # Get summary stats
        macro_df = data.get("macro_indicators")
        demo_df = data.get("demographics")
        trade_df = data.get("trade_data")
        
        macro_count = len(macro_df) if macro_df is not None and not macro_df.empty else 0
        demo_count = len(demo_df) if demo_df is not None and not demo_df.empty else 0
        trade_count = len(trade_df) if trade_df is not None and not trade_df.empty else 0
        
        # Get list of countries and years actually collected
        countries_collected = []
        years_collected = []
        if macro_df is not None and not macro_df.empty:
            countries_collected = macro_df["country_code"].unique().tolist()
            years_collected = sorted(macro_df["year"].unique().tolist())
        
        return {
            "status": "success",
            "message": "Real data collected from World Bank API",
            "data_source": "World Bank Open Data (api.worldbank.org)",
            "summary": {
                "macro_indicators_records": macro_count,
                "demographics_records": demo_count,
                "trade_data_records": trade_count,
                "countries_collected": countries_collected,
                "years_collected": years_collected,
                "indicators_available": list(macro_df.columns) if macro_df is not None and not macro_df.empty else [],
            }
        }
    except Exception as e:
        logger.error(f"Error collecting data: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-sources")
async def list_data_sources():
    """List available data sources and their status."""
    return {
        "sources": [
            {
                "name": "World Bank Open Data",
                "url": "https://api.worldbank.org/v2",
                "status": "active",
                "api_key_required": False,
                "indicators": [
                    "GDP (NY.GDP.MKTP.CD)",
                    "GDP Growth (NY.GDP.MKTP.KD.ZG)",
                    "Inflation (FP.CPI.TOTL.ZG)",
                    "Unemployment (SL.UEM.TOTL.ZS)",
                    "Population (SP.POP.TOTL)",
                    "Female Population (SP.POP.TOTL.FE.IN)",
                    "Urban Population % (SP.URB.TOTL.IN.ZS)",
                    "Trade % of GDP (NE.TRD.GNFS.ZS)",
                    "Merchandise Exports (TX.VAL.MRCH.CD.WT)",
                    "Merchandise Imports (TM.VAL.MRCH.CD.WT)",
                    "And more..."
                ]
            },
            {
                "name": "UN Comtrade",
                "url": "https://comtradeapi.un.org",
                "status": "limited",
                "api_key_required": False,
                "note": "Free tier has rate limits"
            },
            {
                "name": "FRED (Federal Reserve)",
                "url": "https://api.stlouisfed.org/fred",
                "status": "available",
                "api_key_required": True,
                "env_var": "FRED_API_KEY"
            }
        ]
    }


@router.get("/indicators")
async def list_indicators():
    """List all available macroeconomic indicators."""
    return {
        "indicators": [
            {
                "code": code,
                **info
            }
            for code, info in MACRO_INDICATORS.items()
        ]
    }


@router.get("/countries")
async def list_countries():
    """List all countries available for analysis."""
    return {"countries": ANALYSIS_COUNTRIES}


@router.get("/products")
async def list_products():
    """List all apparel product categories."""
    return {
        "products": [
            {"hs_code": code, **info}
            for code, info in APPAREL_HS_CODES.items()
        ]
    }


@router.get("/correlations")
async def get_correlations(
    target: str = Query(default="import_value", description="Target variable"),
    country: Optional[str] = Query(default=None, description="Country code"),
):
    """Calculate correlations between indicators and trade metrics."""
    try:
        analyzer = get_analyzer()
        correlations = analyzer.calculate_correlations(target=target, country=country)
        
        return {
            "target": target,
            "country": country or "global",
            "correlations": correlations.to_dict("records") if not correlations.empty else []
        }
    except Exception as e:
        logger.error(f"Error calculating correlations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/influence-factors")
async def get_influence_factors(
    target: str = Query(default="import_value", description="Target: import_value, export_value"),
    country: Optional[str] = Query(default=None, description="Country code"),
    top_n: int = Query(default=10, ge=1, le=50, description="Number of factors to return"),
):
    """Get ranked influence factors for trade."""
    try:
        analyzer = get_analyzer()
        factors = analyzer.rank_influence_factors(target=target, country=country)
        
        result = factors.head(top_n).to_dict("records") if not factors.empty else []
        
        return {
            "target": target,
            "country": country or "global",
            "influence_factors": result,
            "total_factors": len(factors),
        }
    except Exception as e:
        logger.error(f"Error getting influence factors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/country/{country_code}")
async def analyze_country(country_code: str):
    """Get detailed analysis for a specific country."""
    try:
        analyzer = get_analyzer()
        
        # Get correlations for both import and export
        import_factors = analyzer.rank_influence_factors(
            target="import_value", 
            country=country_code
        )
        export_factors = analyzer.rank_influence_factors(
            target="export_value",
            country=country_code
        )
        
        return {
            "country_code": country_code,
            "import_analysis": {
                "top_drivers": import_factors.head(5).to_dict("records") if not import_factors.empty else [],
                "total_factors": len(import_factors),
            },
            "export_analysis": {
                "top_drivers": export_factors.head(5).to_dict("records") if not export_factors.empty else [],
                "total_factors": len(export_factors),
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing country {country_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/product/{hs_code}")
async def analyze_product(hs_code: str):
    """Get analysis for a specific product category."""
    try:
        analyzer = get_analyzer()
        product_analysis = analyzer.analyze_by_product([hs_code])
        
        if hs_code not in product_analysis:
            raise HTTPException(status_code=404, detail=f"Product {hs_code} not found")
            
        return {
            "hs_code": hs_code,
            "analysis": product_analysis[hs_code]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing product {hs_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_key_insights(top_n: int = Query(default=5, ge=1, le=20)):
    """Get key insights from the analysis."""
    try:
        analyzer = get_analyzer()
        insights = analyzer.get_key_insights(top_n=top_n)
        
        return insights
    except Exception as e:
        logger.error(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def generate_report():
    """Generate summary analysis report."""
    try:
        analyzer = get_analyzer()
        report = analyzer.generate_summary_report()
        
        return {
            "report": report,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/scenario")
async def predict_scenario(scenario: ScenarioInput):
    """Make trade prediction based on economic scenario."""
    try:
        predictor = get_predictor()
        
        # Train models if not already trained
        predictor.train_model(target="import_value")
        predictor.train_model(target="export_value")
        
        input_data = scenario.model_dump()
        
        import_pred = predictor.predict("import_value_global_gradient_boosting", input_data)
        export_pred = predictor.predict("export_value_global_gradient_boosting", input_data)
        
        return {
            "scenario": input_data,
            "predictions": {
                "import_value": import_pred,
                "export_value": export_pred,
            }
        }
    except Exception as e:
        logger.error(f"Error in scenario prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict/country/{country_code}")
async def predict_country(country_code: str, scenario: ScenarioInput):
    """Make trade prediction for a specific country."""
    try:
        predictor = get_predictor()
        input_data = scenario.model_dump()
        
        result = predictor.predict_by_country(country_code, input_data)
        
        return result
    except Exception as e:
        logger.error(f"Error predicting for country {country_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forecast")
async def forecast_trade(request: ForecastRequest):
    """Generate trade forecasts for upcoming years."""
    try:
        predictor = get_predictor()
        
        forecasts = predictor.forecast_growth(
            years_ahead=request.years_ahead,
            countries=request.countries,
            gdp_growth_assumption=request.gdp_growth_assumption,
            inflation_assumption=request.inflation_assumption,
        )
        
        return {
            "assumptions": {
                "gdp_growth": request.gdp_growth_assumption,
                "inflation": request.inflation_assumption,
                "years_ahead": request.years_ahead,
            },
            "forecasts": forecasts.to_dict("records") if not forecasts.empty else [],
        }
    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-summary")
async def get_model_summary():
    """Get summary of trained prediction models."""
    try:
        predictor = get_predictor()
        summary = predictor.get_prediction_summary()
        
        return summary
    except Exception as e:
        logger.error(f"Error getting model summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm/insights")
async def get_llm_insights(
    analysis_type: str = Query(default="correlation", description="Type: correlation, forecast, executive")
):
    """Generate LLM-powered insights."""
    try:
        analyzer = get_analyzer()
        insights_gen = get_insights()
        
        if analysis_type == "correlation":
            correlations = analyzer.get_key_insights()
            insight = insights_gen.generate_correlation_insights(correlations)
        elif analysis_type == "executive":
            full_analysis = {
                "countries_analyzed": len(ANALYSIS_COUNTRIES),
                "time_period": "2018-2025",
                "data_points": len(_data_cache.get("macro_indicators", [])),
                "top_import_drivers": analyzer.rank_influence_factors("import_value").head(3).to_dict("records"),
                "top_export_drivers": analyzer.rank_influence_factors("export_value").head(3).to_dict("records"),
            }
            insight = insights_gen.generate_executive_summary(full_analysis)
        else:
            insight = insights_gen._rule_based_insights("")
            
        return {
            "analysis_type": analysis_type,
            "insight": insight,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating LLM insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def clean_dataframe_for_json(df):
    """Clean DataFrame to be JSON serializable (handle NaN, inf values)."""
    import numpy as np
    # Replace NaN and inf with None
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.where(df.notna(), None)
    return df


@router.get("/data/macro")
async def get_macro_data(
    country: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get raw macroeconomic data from World Bank."""
    try:
        import pandas as pd
        
        if not _data_cache:
            raise HTTPException(status_code=400, detail="Data not loaded. Call POST /macro/collect first.")
            
        data = _data_cache.get("macro_indicators")
        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            return {"data": [], "total": 0, "message": "No data available. Call POST /macro/collect first."}
            
        if isinstance(data, list):
            data = pd.DataFrame(data)
            
        if country and "country_code" in data.columns:
            data = data[data["country_code"] == country]
        if year and "year" in data.columns:
            data = data[data["year"] == year]
        
        # Clean for JSON
        data = clean_dataframe_for_json(data)
            
        return {
            "data": data.head(limit).to_dict("records") if not data.empty else [],
            "total": len(data),
            "source": "World Bank Open Data API"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting macro data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/demographics")
async def get_demographic_data(
    country: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get demographic data from World Bank."""
    try:
        import pandas as pd
        
        if not _data_cache:
            raise HTTPException(status_code=400, detail="Data not loaded. Call POST /macro/collect first.")
            
        data = _data_cache.get("demographics")
        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            return {"data": [], "total": 0, "message": "No data available. Call POST /macro/collect first."}
            
        if isinstance(data, list):
            data = pd.DataFrame(data)
            
        if country and "country_code" in data.columns:
            data = data[data["country_code"] == country]
        if year and "year" in data.columns:
            data = data[data["year"] == year]
        
        # Clean for JSON
        data = clean_dataframe_for_json(data)
            
        return {
            "data": data.head(limit).to_dict("records") if not data.empty else [],
            "total": len(data),
            "source": "World Bank Open Data API"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting demographic data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data/trade")
async def get_trade_data(
    country: Optional[str] = None,
    hs_code: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Get trade data derived from World Bank merchandise trade statistics."""
    try:
        import pandas as pd
        
        if not _data_cache:
            raise HTTPException(status_code=400, detail="Data not loaded. Call POST /macro/collect first.")
            
        data = _data_cache.get("trade_data")
        if data is None or (isinstance(data, pd.DataFrame) and data.empty):
            return {"data": [], "total": 0, "message": "No data available. Call POST /macro/collect first."}
            
        if isinstance(data, list):
            data = pd.DataFrame(data)
            
        if country and "reporter_code" in data.columns:
            data = data[data["reporter_code"] == country]
        if hs_code and "hs_code" in data.columns:
            data = data[data["hs_code"] == hs_code]
        if year and "year" in data.columns:
            data = data[data["year"] == year]
        
        # Clean for JSON
        data = clean_dataframe_for_json(data)
            
        return {
            "data": data.head(limit).to_dict("records") if not data.empty else [],
            "total": len(data),
            "source": "Derived from World Bank merchandise trade statistics"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
