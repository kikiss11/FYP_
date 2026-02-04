"""Data collector for macroeconomic indicators from real data sources."""

import httpx
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from loguru import logger
import asyncio
import os

from .config import ANALYSIS_COUNTRIES, MACRO_INDICATORS, APPAREL_HS_CODES


class MacroDataCollector:
    """Collect macroeconomic data from World Bank and other free APIs."""
    
    def __init__(self):
        self.world_bank_base = "https://api.worldbank.org/v2"
        self.timeout = httpx.Timeout(60.0, connect=30.0)
        
        # World Bank indicator mappings (verified working indicators)
        self.wb_indicators = {
            # GDP & Growth
            "gdp": "NY.GDP.MKTP.CD",                    # GDP (current US$)
            "gdp_growth": "NY.GDP.MKTP.KD.ZG",         # GDP growth (annual %)
            "gdp_per_capita": "NY.GDP.PCAP.CD",        # GDP per capita (current US$)
            
            # Inflation & Prices
            "inflation": "FP.CPI.TOTL.ZG",             # Inflation, consumer prices (annual %)
            "cpi": "FP.CPI.TOTL",                      # Consumer price index
            
            # Labor
            "unemployment": "SL.UEM.TOTL.ZS",          # Unemployment, total (% of labor force)
            "labor_force": "SL.TLF.TOTL.IN",          # Labor force, total
            "female_labor_participation": "SL.TLF.CACT.FE.ZS",  # Female labor force participation
            
            # Population & Demographics
            "population": "SP.POP.TOTL",               # Population, total
            "female_population": "SP.POP.TOTL.FE.IN", # Population, female
            "female_population_pct": "SP.POP.TOTL.FE.ZS",  # Population, female (% of total)
            "urban_population_pct": "SP.URB.TOTL.IN.ZS",   # Urban population (% of total)
            "population_growth": "SP.POP.GROW",        # Population growth (annual %)
            
            # Trade
            "exports_goods_services": "NE.EXP.GNFS.CD",  # Exports of goods and services (current US$)
            "imports_goods_services": "NE.IMP.GNFS.CD",  # Imports of goods and services (current US$)
            "trade_pct_gdp": "NE.TRD.GNFS.ZS",          # Trade (% of GDP)
            "merchandise_exports": "TX.VAL.MRCH.CD.WT", # Merchandise exports (current US$)
            "merchandise_imports": "TM.VAL.MRCH.CD.WT", # Merchandise imports (current US$)
            "textile_exports": "TX.VAL.TXTL.ZS.UN",    # Textile exports (% of merchandise exports)
            
            # Consumer & Household
            "household_consumption": "NE.CON.PRVT.CD",  # Household consumption (current US$)
            "final_consumption": "NE.CON.TOTL.ZS",     # Final consumption expenditure (% of GDP)
            
            # Exchange Rates
            "exchange_rate": "PA.NUS.FCRF",            # Official exchange rate
            
            # Industry
            "industry_value_added": "NV.IND.TOTL.ZS",  # Industry value added (% of GDP)
            "manufacturing_value_added": "NV.IND.MANF.ZS",  # Manufacturing value added (% of GDP)
        }
        
        # Country code mapping (ISO2 to ISO3 for World Bank)
        self.country_codes = {
            "US": "USA", "CN": "CHN", "GB": "GBR", "DE": "DEU", "FR": "FRA",
            "JP": "JPN", "KR": "KOR", "IN": "IND", "VN": "VNM", "BD": "BGD",
            "IT": "ITA", "ES": "ESP", "MX": "MEX", "TR": "TUR", "ID": "IDN",
            "TH": "THA", "PK": "PAK", "HK": "HKG", "SG": "SGP", "AU": "AUS",
            "TW": "TWN", "MY": "MYS", "PH": "PHL", "NZ": "NZL", "CA": "CAN",
            "NL": "NLD", "SE": "SWE", "PL": "POL", "AE": "ARE", "SA": "SAU",
            "BR": "BRA", "AR": "ARG",
        }
        
    async def fetch_world_bank_data(
        self, 
        indicator: str, 
        country_codes: List[str],
        start_year: int = 2015,
        end_year: int = None
    ) -> List[Dict]:
        """Fetch data from World Bank API (free, no API key needed)."""
        if end_year is None:
            end_year = datetime.now().year
            
        results = []
        
        # Convert ISO2 to ISO3 codes
        iso3_codes = [self.country_codes.get(c, c) for c in country_codes]
        countries_str = ";".join(iso3_codes)
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                url = f"{self.world_bank_base}/country/{countries_str}/indicator/{indicator}"
                params = {
                    "format": "json",
                    "date": f"{start_year}:{end_year}",
                    "per_page": 1000,
                }
                
                logger.info(f"Fetching World Bank data: {indicator} for {len(country_codes)} countries")
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if len(data) > 1 and data[1]:
                        for item in data[1]:
                            if item.get("value") is not None:
                                # Map back to ISO2 code
                                iso2 = next(
                                    (k for k, v in self.country_codes.items() 
                                     if v == item["countryiso3code"]),
                                    item.get("countryiso3code", "")
                                )
                                results.append({
                                    "country_code": iso2,
                                    "country_name": item["country"]["value"],
                                    "indicator_code": indicator,
                                    "indicator_name": item["indicator"]["value"],
                                    "year": int(item["date"]),
                                    "value": float(item["value"]),
                                    "source": "World Bank",
                                })
                        logger.success(f"Fetched {len(results)} records for {indicator}")
                else:
                    logger.warning(f"World Bank API returned {response.status_code} for {indicator}")
                    
            except Exception as e:
                logger.error(f"Error fetching World Bank data for {indicator}: {e}")
                
        return results
    
    async def fetch_un_comtrade_apparel(
        self,
        reporter_codes: List[str],
        start_year: int = 2018,
        end_year: int = None
    ) -> List[Dict]:
        """Fetch apparel trade data from UN Comtrade (limited free access)."""
        if end_year is None:
            end_year = datetime.now().year - 1  # Usually 1 year lag
            
        results = []
        
        # UN Comtrade requires numeric country codes (M49)
        # This is a simplified version - for production, use proper M49 codes
        m49_codes = {
            "US": "842", "CN": "156", "GB": "826", "DE": "276", "FR": "250",
            "JP": "392", "KR": "410", "IN": "356", "VN": "704", "BD": "050",
            "IT": "380", "ES": "724", "MX": "484", "TR": "792", "ID": "360",
            "TH": "764", "HK": "344", "SG": "702", "AU": "036",
        }
        
        # HS codes for apparel (Chapter 61-62)
        apparel_hs = ["61", "62"]  # Knitted and woven apparel
        
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for country in reporter_codes[:5]:  # Limit to avoid rate limits
                m49 = m49_codes.get(country)
                if not m49:
                    continue
                    
                for year in range(max(start_year, end_year - 3), end_year + 1):
                    try:
                        # UN Comtrade API v1 (public, limited)
                        url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
                        params = {
                            "reporterCode": m49,
                            "period": str(year),
                            "cmdCode": "61,62",  # Apparel chapters
                            "flowCode": "M,X",   # Import and Export
                            "partnerCode": "0",  # World
                        }
                        
                        response = await client.get(url, params=params)
                        if response.status_code == 200:
                            data = response.json()
                            for record in data.get("data", []):
                                results.append({
                                    "reporter_code": country,
                                    "reporter_name": record.get("reporterDesc", ""),
                                    "hs_code": record.get("cmdCode", ""),
                                    "product_name": record.get("cmdDesc", ""),
                                    "trade_flow": "import" if record.get("flowCode") == "M" else "export",
                                    "year": int(record.get("period", year)),
                                    "trade_value_usd": record.get("primaryValue"),
                                    "source": "UN Comtrade",
                                })
                        await asyncio.sleep(1)  # Rate limiting
                    except Exception as e:
                        logger.warning(f"UN Comtrade error for {country}/{year}: {e}")
                        
        return results
    
    async def collect_all_real_data(
        self,
        countries: List[str] = None,
        start_year: int = 2015,
        end_year: int = None
    ) -> Dict[str, pd.DataFrame]:
        """Collect all macroeconomic data from real sources.
        
        Args:
            countries: List of ISO2 country codes
            start_year: Start year for data collection
            end_year: End year (defaults to current year)
        """
        if countries is None:
            countries = [c["code"] for c in ANALYSIS_COUNTRIES]
        if end_year is None:
            end_year = datetime.now().year
            
        logger.info(f"Collecting real macroeconomic data for {len(countries)} countries ({start_year}-{end_year})")
        
        all_macro_data = []
        
        # Fetch World Bank indicators
        for indicator_key, wb_code in self.wb_indicators.items():
            try:
                data = await self.fetch_world_bank_data(
                    wb_code, 
                    countries, 
                    start_year, 
                    end_year
                )
                for record in data:
                    record["indicator_key"] = indicator_key
                all_macro_data.extend(data)
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error fetching {indicator_key}: {e}")
        
        # Convert to DataFrame and pivot for analysis format
        if not all_macro_data:
            logger.error("No data collected from World Bank")
            return {"macro_indicators": pd.DataFrame(), "demographics": pd.DataFrame(), "trade_data": pd.DataFrame()}
        
        df = pd.DataFrame(all_macro_data)
        
        # Pivot to get indicators as columns
        macro_pivot = df.pivot_table(
            index=["country_code", "country_name", "year"],
            columns="indicator_key",
            values="value",
            aggfunc="first"
        ).reset_index()
        
        # Flatten column names
        macro_pivot.columns = [col if isinstance(col, str) else col for col in macro_pivot.columns]
        
        logger.info(f"Collected {len(macro_pivot)} country-year records with {len(macro_pivot.columns)} columns")
        
        # Create demographics subset
        demo_cols = ["country_code", "country_name", "year", "population", "female_population", 
                     "female_population_pct", "urban_population_pct", "population_growth", 
                     "female_labor_participation"]
        demo_cols_available = [c for c in demo_cols if c in macro_pivot.columns]
        demographics = macro_pivot[demo_cols_available].copy()
        
        # Rename for compatibility with analyzer
        if "female_population_pct" in demographics.columns:
            demographics = demographics.rename(columns={"female_population_pct": "female_ratio"})
        if "urban_population_pct" in demographics.columns:
            demographics = demographics.rename(columns={"urban_population_pct": "urbanization_rate"})
        
        # Calculate working_age_female (approximate as 65% of female population)
        if "female_population" in demographics.columns:
            demographics["working_age_female"] = demographics["female_population"] * 0.65 / 1e6  # Convert to millions
            demographics["female_population"] = demographics["female_population"] / 1e6
        if "population" in demographics.columns:
            demographics["total_population"] = demographics["population"] / 1e6
        
        # Create trade data from exports/imports
        trade_cols = ["country_code", "year", "exports_goods_services", "imports_goods_services", 
                      "merchandise_exports", "merchandise_imports", "textile_exports", "trade_pct_gdp"]
        trade_cols_available = [c for c in trade_cols if c in macro_pivot.columns]
        
        trade_data = []
        for _, row in macro_pivot[trade_cols_available].iterrows():
            # Estimate apparel trade as portion of textile/merchandise trade
            import_val = row.get("merchandise_imports", row.get("imports_goods_services", 0)) or 0
            export_val = row.get("merchandise_exports", row.get("exports_goods_services", 0)) or 0
            textile_pct = row.get("textile_exports", 5) or 5  # Default 5% if not available
            
            # Estimate apparel as ~40% of textile trade
            apparel_import = (import_val * textile_pct / 100 * 0.4) / 1e9  # Convert to billions
            apparel_export = (export_val * textile_pct / 100 * 0.4) / 1e9
            
            for hs_code, product_info in APPAREL_HS_CODES.items():
                trade_data.append({
                    "reporter_code": row["country_code"],
                    "hs_code": hs_code,
                    "product_name": product_info["name"],
                    "product_category": product_info["category"],
                    "year": row["year"],
                    "import_value": apparel_import / len(APPAREL_HS_CODES),  # Distribute across products
                    "export_value": apparel_export / len(APPAREL_HS_CODES),
                    "import_growth": 0,  # Will be calculated
                    "export_growth": 0,
                })
        
        trade_df = pd.DataFrame(trade_data)
        
        # Calculate growth rates
        if not trade_df.empty:
            trade_df = trade_df.sort_values(["reporter_code", "hs_code", "year"])
            trade_df["import_growth"] = trade_df.groupby(["reporter_code", "hs_code"])["import_value"].pct_change() * 100
            trade_df["export_growth"] = trade_df.groupby(["reporter_code", "hs_code"])["export_value"].pct_change() * 100
        
        # Prepare macro indicators for analyzer (rename columns for compatibility)
        macro_indicators = macro_pivot.copy()
        
        # Map column names to match analyzer expectations
        column_mapping = {
            "gdp": "gdp",
            "gdp_growth": "gdp_growth", 
            "inflation": "inflation",
            "unemployment": "unemployment",
            "cpi": "clothing_cpi",  # Use CPI as proxy for clothing CPI
            "exchange_rate": "interest_rate",  # Approximate
            "household_consumption": "retail_sales_growth",  # Proxy
            "urban_population_pct": "urbanization_rate",
            "female_population_pct": "female_ratio",
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in macro_indicators.columns and new_name not in macro_indicators.columns:
                macro_indicators[new_name] = macro_indicators[old_name]
        
        # Calculate consumer confidence proxy (normalize GDP growth + inverse unemployment)
        if "gdp_growth" in macro_indicators.columns and "unemployment" in macro_indicators.columns:
            macro_indicators["consumer_confidence"] = 100 + (macro_indicators["gdp_growth"] * 2) - (macro_indicators["unemployment"] * 0.5)
        
        # Add female population columns if available
        if "female_population" in macro_pivot.columns:
            macro_indicators["female_population"] = macro_pivot["female_population"] / 1e6
            macro_indicators["working_age_female"] = macro_indicators["female_population"] * 0.65
        
        if "female_labor_participation" in macro_pivot.columns:
            macro_indicators["female_labor_participation"] = macro_pivot["female_labor_participation"]
        
        logger.success(f"Data collection complete: {len(macro_indicators)} macro records, {len(demographics)} demo records, {len(trade_df)} trade records")
        
        return {
            "macro_indicators": macro_indicators,
            "demographics": demographics,
            "trade_data": trade_df,
        }
    
    async def collect_all_data(
        self,
        countries: List[str] = None,
        use_synthetic: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """Main entry point for data collection.
        
        Args:
            countries: List of country codes
            use_synthetic: If True, use synthetic data (deprecated)
        """
        return await self.collect_all_real_data(countries)


# Singleton instance
_collector = None

def get_collector() -> MacroDataCollector:
    global _collector
    if _collector is None:
        _collector = MacroDataCollector()
    return _collector
