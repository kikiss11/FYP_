# 🔍 Google Trends & Trade Intelligence Platform

A modern, production-ready solution for:
1. **Google Trends Data Extraction** - Automated scraping with multi-region and keyword support
2. **Tariff News Analysis** - Automated news scraping with NLP-powered trade tension analysis
3. **Macroeconomic Trade Analyzer** - ML-powered analysis of economic factors affecting women's apparel trade

## 📋 Features

### Google Trends Scraper
- **Weekly Automated Scraping** - Configurable scheduling via APScheduler
- **Multi-Region Support** - 30+ countries (HK, TW, SG, JP, KR, CN, MY, TH, VN, PH, ID, IN, US, CA, MX, GB, DE, FR, IT, ES, NL, SE, PL, AU, NZ, AE, SA, BR, AR)
- **Keyword Analysis** - Track multiple keywords (fashion, products, etc.)
- **Related Data Extraction** - Related searches and related topics/themes
- **Interest Over Time** - Historical trend data
- **Interest by Region** - Geographic breakdown

### Tariff News Analyzer
- **Multi-Source News Scraping** - NewsAPI, GNews, Google News RSS
- **Sentiment Analysis** - FinBERT financial sentiment model
- **Trade Tension Analysis** - Score and track trade tensions by region
- **Trade Effectiveness Analysis** - Measure trade policy impacts
- **Entity Extraction** - Identify key organizations, countries, and topics
- **Bilateral Relationship Tracking** - Analyze relations between country pairs
- **Daily Reports** - Automated trend reports

### Macroeconomic Trade Analyzer
- **Economic Indicator Analysis** - GDP, inflation, unemployment correlation with trade
- **Demographic Impact Analysis** - Female population, urbanization effects on demand
- **Influence Factor Ranking** - Identify what drives imports/exports
- **ML Predictions** - Forecast trade volumes using Random Forest & Gradient Boosting
- **Scenario Analysis** - What-if economic simulations
- **Country Comparison** - Cross-market trade driver comparison
- **Product Category Analysis** - HS code level trade insights
- **LLM Insights** - AI-generated executive summaries

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Google Trends & Tariff News Platform                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────┐    ┌────────────────────────────┐           │
│  │     Google Trends          │    │     News Analyzer          │           │
│  │  ┌──────────────────────┐  │    │  ┌──────────────────────┐  │           │
│  │  │   Scheduler          │  │    │  │   News Scraper       │  │           │
│  │  │   (APScheduler)      │  │    │  │   (Multi-source)     │  │           │
│  │  └──────────────────────┘  │    │  └──────────────────────┘  │           │
│  │           │                │    │           │                │           │
│  │           ▼                │    │           ▼                │           │
│  │  ┌──────────────────────┐  │    │  ┌──────────────────────┐  │           │
│  │  │   Trends Client      │  │    │  │   Text Analyzer      │  │           │
│  │  │   (pytrends)         │  │    │  │   (FinBERT/spaCy)    │  │           │
│  │  └──────────────────────┘  │    │  └──────────────────────┘  │           │
│  │           │                │    │           │                │           │
│  │           ▼                │    │           ▼                │           │
│  │  ┌──────────────────────┐  │    │  ┌──────────────────────┐  │           │
│  │  │   Trends Dashboard   │  │    │  │   Trade Analyzer     │  │           │
│  │  │   (Port 8501)        │  │    │  │   News Dashboard     │  │           │
│  │  └──────────────────────┘  │    │  │   (Port 8502)        │  │           │
│  └────────────────────────────┘    │  └──────────────────────┘  │           │
│                                    └────────────────────────────┘           │
│                                                                              │
│                         ┌──────────────────────┐                            │
│                         │     REST API         │                            │
│                         │     (FastAPI)        │                            │
│                         │     Port 8000        │                            │
│                         └──────────────────────┘                            │
│                                    │                                         │
│                                    ▼                                         │
│                         ┌──────────────────────┐                            │
│                         │     PostgreSQL       │                            │
│                         │     Database         │                            │
│                         └──────────────────────┘                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.11+ | Core development |
| Trends API | pytrends | Google Trends data extraction |
| Web Framework | FastAPI | REST API endpoints |
| Database | PostgreSQL | Persistent data storage |
| ORM | SQLAlchemy | Database abstraction |
| Scheduler | APScheduler | Automated jobs |
| Dashboard | Streamlit | Data visualization |
| NLP | Transformers (FinBERT) | Financial sentiment analysis |
| NER | spaCy | Entity extraction |
| ML | scikit-learn | Trade predictions |
| Charts | Plotly | Interactive visualizations |
| Containerization | Docker | Deployment |

## 📁 Project Structure

```
google-trends-scraper/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── models.py              # Database models
│   ├── scraper/               # Google Trends module
│   │   ├── __init__.py
│   │   ├── trends_client.py   # Google Trends client
│   │   ├── extractor.py       # Data extraction logic
│   │   └── scheduler.py       # Job scheduling
│   ├── api/                   # REST API
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI application
│   │   ├── routes.py          # API endpoints
│   │   └── schemas.py         # Pydantic models
│   ├── dashboard/             # Trends dashboard
│   │   └── app.py             # Streamlit app
│   ├── news_analyzer/         # Tariff News module
│   │   ├── __init__.py
│   │   ├── config.py          # News analyzer config
│   │   ├── models.py          # News database models
│   │   ├── news_scraper.py    # Multi-source news scraper
│   │   ├── text_analyzer.py   # NLP text analysis
│   │   ├── trade_analyzer.py  # Trade tension analysis
│   │   ├── llm_analyzer.py    # LLM trade impact summaries
│   │   ├── api.py             # News API routes
│   │   └── dashboard.py       # News dashboard
│   └── macro_analyzer/        # Macroeconomic Trade module
│       ├── __init__.py
│       ├── config.py          # Countries, indicators config
│       ├── models.py          # Database models
│       ├── data_collector.py  # Economic data collection
│       ├── analyzer.py        # Correlation analysis
│       ├── predictor.py       # ML trade predictions
│       ├── llm_insights.py    # AI-generated insights
│       ├── api.py             # Macro API routes
│       └── dashboard.py       # Macro dashboard (Port 8504)
├── data/                      # Data exports
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🚀 Quick Start with Docker

### 1. Clone & Configure

```bash
cd google-trends-scraper

# Optional: Set API keys for more news sources
export NEWSAPI_KEY=your_newsapi_key       # Get from https://newsapi.org
export GNEWS_API_KEY=your_gnews_key       # Get from https://gnews.io
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Access Dashboards

| Service | URL | Description |
|---------|-----|-------------|
| API Docs | http://localhost:8000/docs | Swagger API documentation |
| Trends Dashboard | http://localhost:8501 | Google Trends visualization |
| News Dashboard | http://localhost:8502 | Tariff News analysis |
| Ecommerce Dashboard | http://localhost:8503 | E-commerce analysis |
| Macro Dashboard | http://localhost:8504 | Macroeconomic trade analysis |

## 📰 News Analyzer API Endpoints

### Fetch News
```bash
# Fetch tariff news (uses Google News RSS - no API key needed)
curl -X POST http://localhost:8000/news/fetch \
  -H "Content-Type: application/json" \
  -d '{"days_back": 7}'

# Fetch with specific queries and regions
curl -X POST http://localhost:8000/news/fetch \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["tariff trade war", "US China trade"],
    "regions": ["US", "CN", "EU"],
    "days_back": 7
  }'
```

### Analyze Articles
```bash
# Analyze unprocessed articles
curl -X POST http://localhost:8000/news/analyze \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 50}'
```

### Get Analysis Results
```bash
# Get summary statistics
curl http://localhost:8000/news/summary

# Get region-specific analysis
curl http://localhost:8000/news/region/US?days_back=30

# Get bilateral relations
curl "http://localhost:8000/news/bilateral?country_a=US&country_b=CN&days_back=30"

# Get tension trend
curl http://localhost:8000/news/tension/trend?days_back=30

# Get top tension articles
curl http://localhost:8000/news/tension/top?limit=20
```

## 📊 Trade Analysis Metrics

### Sentiment Analysis
- Uses **FinBERT** (financial BERT) for accurate financial sentiment
- Classifies news as: positive, negative, neutral
- Confidence scores (0-1)

### Trade Tension Score
| Score | Level | Indicators |
|-------|-------|------------|
| 0.7-1.0 | High | trade war, sanctions, retaliation, ban |
| 0.4-0.7 | Moderate | tariff increase, investigation, tension |
| 0.0-0.4 | Low | negotiation, talks, discussion |
| < 0 | Positive | agreement, deal, cooperation |

### Trade Effectiveness Score
- **Positive (+)**: export growth, market access, investment
- **Negative (-)**: export decline, cost increase, job loss
- **Neutral (0)**: mixed or no clear indicators

## ⚙️ Configuration

### config.yaml (Google Trends)
```yaml
keywords:
  - pant
  - dress
  - t-shirt

regions:
  - HK  # Hong Kong
  - TW  # Taiwan
  - US  # United States
  # ... more regions

timeframe: "now 7-d"  # Last 7 days
category: 68  # Fashion category
```

### Environment Variables (News Analyzer)
```bash
# Optional API keys (Google News RSS works without keys)
NEWSAPI_KEY=your_key        # NewsAPI.org (100 req/day free)
GNEWS_API_KEY=your_key      # GNews.io (100 req/day free)

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
```

## 📈 Dashboards

### Trends Dashboard (Port 8501)
- Interest over time charts
- Regional comparison
- Related queries & topics
- Keyword comparison

### News Dashboard (Port 8502)
- Trade tension trend over time
- Sentiment distribution
- Region-by-region analysis
- Key organizations & countries
- Recent high-tension articles
- LLM-generated trade impact summaries

### Macro Dashboard (Port 8504)
- Key influence factor rankings
- Correlation analysis heatmaps
- Trade growth forecasts
- Scenario analysis simulator
- Country comparison
- Product category analysis
- AI-generated executive summaries

## 🔄 Scheduled Jobs

| Job | Frequency | Description |
|-----|-----------|-------------|
| Trends Extraction | Weekly (Sunday 2 AM) | Fetch Google Trends data |
| News Fetch | Daily (6 AM) | Scrape tariff news |
| News Analysis | Daily (7 AM) | Analyze new articles |
| Report Generation | Daily (8 AM) | Generate tension reports |

## 📈 Macroeconomic Analyzer API

### Initialize Data
```bash
# Load synthetic economic data (for demo)
curl -X POST http://localhost:8000/macro/collect

# Check status
curl http://localhost:8000/macro/status
```

### Correlation Analysis
```bash
# Get influence factors for imports
curl "http://localhost:8000/macro/influence-factors?target=import_value&top_n=10"

# Get country-specific analysis
curl http://localhost:8000/macro/analysis/country/US

# Get product-specific analysis  
curl http://localhost:8000/macro/analysis/product/6104
```

### Trade Predictions
```bash
# Scenario prediction
curl -X POST http://localhost:8000/macro/predict/scenario \
  -H "Content-Type: application/json" \
  -d '{
    "gdp": 1500,
    "inflation": 3.0,
    "consumer_confidence": 95,
    "female_population": 55
  }'

# Multi-year forecast
curl -X POST http://localhost:8000/macro/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "years_ahead": 3,
    "gdp_growth_assumption": 2.5,
    "inflation_assumption": 2.0
  }'
```

### AI Insights
```bash
# Get LLM-generated insights
curl "http://localhost:8000/macro/llm/insights?analysis_type=executive"
```

## 📊 Macroeconomic Indicators

### General Economic
| Indicator | Impact on Trade | Description |
|-----------|-----------------|-------------|
| GDP | Positive | Higher GDP → more imports |
| GDP Growth | Positive | Growing economies import more |
| Inflation | Negative | Higher prices reduce demand |
| Unemployment | Negative | Less employment → less spending |
| Interest Rate | Negative | Higher rates reduce consumption |

### Demographics
| Indicator | Impact on Trade | Description |
|-----------|-----------------|-------------|
| Female Population | Positive | Key target demographic |
| Working Age Female | Positive | Higher spending power |
| Urbanization Rate | Positive | Urban consumers buy more fashion |
| Female Labor Participation | Positive | Working women spend on apparel |

### Industry Specific
| Indicator | Impact on Trade | Description |
|-----------|-----------------|-------------|
| Clothing CPI | Negative | Higher prices reduce volume |
| Cotton Price Index | Negative | Raw material costs |
| Labor Cost Index | Negative | Manufacturing costs |
| E-commerce Penetration | Positive | Online fashion sales growth |

## 📝 License

MIT License
