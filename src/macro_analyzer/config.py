"""Configuration for Macroeconomic Trade Analyzer."""

# Countries/regions to analyze
ANALYSIS_COUNTRIES = [
    {"code": "US", "name": "United States", "currency": "USD"},
    {"code": "CN", "name": "China", "currency": "CNY"},
    {"code": "GB", "name": "United Kingdom", "currency": "GBP"},
    {"code": "DE", "name": "Germany", "currency": "EUR"},
    {"code": "FR", "name": "France", "currency": "EUR"},
    {"code": "JP", "name": "Japan", "currency": "JPY"},
    {"code": "KR", "name": "South Korea", "currency": "KRW"},
    {"code": "IN", "name": "India", "currency": "INR"},
    {"code": "VN", "name": "Vietnam", "currency": "VND"},
    {"code": "BD", "name": "Bangladesh", "currency": "BDT"},
    {"code": "IT", "name": "Italy", "currency": "EUR"},
    {"code": "ES", "name": "Spain", "currency": "EUR"},
    {"code": "MX", "name": "Mexico", "currency": "MXN"},
    {"code": "TR", "name": "Turkey", "currency": "TRY"},
    {"code": "ID", "name": "Indonesia", "currency": "IDR"},
    {"code": "TH", "name": "Thailand", "currency": "THB"},
    {"code": "PK", "name": "Pakistan", "currency": "PKR"},
    {"code": "HK", "name": "Hong Kong", "currency": "HKD"},
    {"code": "SG", "name": "Singapore", "currency": "SGD"},
    {"code": "AU", "name": "Australia", "currency": "AUD"},
]

# Macroeconomic indicators
MACRO_INDICATORS = {
    # General Economic
    "gdp": {
        "name": "GDP",
        "description": "Gross Domestic Product",
        "unit": "billion USD",
        "expected_impact": "positive",  # Higher GDP → more imports
    },
    "gdp_growth": {
        "name": "GDP Growth Rate",
        "description": "Annual GDP growth percentage",
        "unit": "%",
        "expected_impact": "positive",
    },
    "inflation": {
        "name": "Inflation Rate",
        "description": "General inflation rate",
        "unit": "%",
        "expected_impact": "negative",  # Higher inflation → less purchasing power
    },
    "unemployment": {
        "name": "Unemployment Rate",
        "description": "Unemployment percentage",
        "unit": "%",
        "expected_impact": "negative",
    },
    "exchange_rate": {
        "name": "Exchange Rate",
        "description": "Exchange rate vs USD",
        "unit": "local/USD",
        "expected_impact": "mixed",
    },
    "interest_rate": {
        "name": "Interest Rate",
        "description": "Central bank interest rate",
        "unit": "%",
        "expected_impact": "negative",
    },
    
    # Consumer Related
    "consumer_confidence": {
        "name": "Consumer Confidence Index",
        "description": "Consumer confidence measure",
        "unit": "index",
        "expected_impact": "positive",
    },
    "retail_sales_growth": {
        "name": "Retail Sales Growth",
        "description": "Retail sales growth rate",
        "unit": "%",
        "expected_impact": "positive",
    },
    "disposable_income": {
        "name": "Disposable Income per Capita",
        "description": "Average disposable income",
        "unit": "USD",
        "expected_impact": "positive",
    },
    
    # Clothing & Apparel Specific
    "clothing_cpi": {
        "name": "Clothing CPI",
        "description": "Consumer Price Index for Clothing",
        "unit": "index",
        "expected_impact": "negative",
    },
    "clothing_inflation": {
        "name": "Clothing Inflation",
        "description": "Year-over-year clothing price change",
        "unit": "%",
        "expected_impact": "negative",
    },
    "apparel_retail_sales": {
        "name": "Apparel Retail Sales",
        "description": "Total apparel retail sales",
        "unit": "billion USD",
        "expected_impact": "positive",
    },
    
    # Trade Related
    "import_volume": {
        "name": "Apparel Import Volume",
        "description": "Total apparel import value",
        "unit": "billion USD",
        "expected_impact": "target",
    },
    "export_volume": {
        "name": "Apparel Export Volume",
        "description": "Total apparel export value",
        "unit": "billion USD",
        "expected_impact": "target",
    },
    "trade_balance": {
        "name": "Apparel Trade Balance",
        "description": "Exports minus imports",
        "unit": "billion USD",
        "expected_impact": "target",
    },
    "tariff_rate": {
        "name": "Average Tariff Rate",
        "description": "Average import tariff on apparel",
        "unit": "%",
        "expected_impact": "negative",
    },
    
    # Demographics
    "population": {
        "name": "Total Population",
        "description": "Total population",
        "unit": "million",
        "expected_impact": "positive",
    },
    "female_population": {
        "name": "Female Population",
        "description": "Female population count",
        "unit": "million",
        "expected_impact": "positive",
    },
    "female_population_ratio": {
        "name": "Female Population Ratio",
        "description": "Percentage of female population",
        "unit": "%",
        "expected_impact": "positive",
    },
    "urbanization_rate": {
        "name": "Urbanization Rate",
        "description": "Percentage of urban population",
        "unit": "%",
        "expected_impact": "positive",
    },
    "median_age": {
        "name": "Median Age",
        "description": "Median population age",
        "unit": "years",
        "expected_impact": "mixed",
    },
    "working_age_female": {
        "name": "Working Age Female Population",
        "description": "Female population 15-64 years",
        "unit": "million",
        "expected_impact": "positive",
    },
    
    # Industry Specific
    "textile_production_index": {
        "name": "Textile Production Index",
        "description": "Industrial production of textiles",
        "unit": "index",
        "expected_impact": "positive",
    },
    "fashion_ecommerce_penetration": {
        "name": "Fashion E-commerce Penetration",
        "description": "Online fashion sales share",
        "unit": "%",
        "expected_impact": "positive",
    },
    "fast_fashion_index": {
        "name": "Fast Fashion Index",
        "description": "Fast fashion market activity",
        "unit": "index",
        "expected_impact": "positive",
    },
    "cotton_price_index": {
        "name": "Cotton Price Index",
        "description": "Raw cotton price index",
        "unit": "index",
        "expected_impact": "negative",
    },
    "labor_cost_index": {
        "name": "Manufacturing Labor Cost",
        "description": "Apparel manufacturing labor cost",
        "unit": "USD/hour",
        "expected_impact": "negative",
    },
}

# Apparel product categories for trade analysis
APPAREL_HS_CODES = {
    "6104": {"name": "Women's Knitted Suits & Ensembles", "category": "formal"},
    "6106": {"name": "Women's Knitted Blouses & Shirts", "category": "tops"},
    "6108": {"name": "Women's Knitted Underwear", "category": "underwear"},
    "6109": {"name": "T-shirts & Singlets (Knitted)", "category": "casual"},
    "6110": {"name": "Sweaters & Pullovers", "category": "knitwear"},
    "6204": {"name": "Women's Woven Suits & Ensembles", "category": "formal"},
    "6206": {"name": "Women's Woven Blouses & Shirts", "category": "tops"},
    "6208": {"name": "Women's Woven Underwear", "category": "underwear"},
    "6211": {"name": "Track Suits & Swimwear", "category": "activewear"},
    "6214": {"name": "Shawls & Scarves", "category": "accessories"},
}

# Data sources
DATA_SOURCES = {
    "world_bank": "World Bank Open Data API",
    "imf": "IMF Data API",
    "un_comtrade": "UN Comtrade Database",
    "fred": "Federal Reserve Economic Data",
    "oecd": "OECD Data",
    "wto": "WTO Trade Statistics",
}
