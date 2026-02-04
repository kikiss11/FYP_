"""Trade Insights Engine - Consultant-grade analysis of how macroeconomic factors affect women's apparel trade."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger


# Industry-specific knowledge base
INDICATOR_IMPACTS = {
    "gdp": {
        "name": "GDP & Economic Growth",
        "mechanism": """**How it affects trade:**
- Higher GDP boosts consumer spending on non-essentials like clothing
- Women's apparel accounts for ~$655 avg U.S. household spend (vs $406 for men's)
- GDP slowdowns shift demand to value-driven options (fast fashion, resale)
- Recessions reduce both imports and exports as consumers delay purchases

**Trade Impact Pattern:**
- GDP ↑ 1% → Women's apparel imports ↑ 0.8-1.2%
- Recession → Shift from premium to affordable imports (China, Bangladesh)
- Recovery → Premium segment rebounds first in developed markets""",
        "direction": "positive",
        "sensitivity": "high",
        "lag_months": 3,
        "recommendations": [
            "Monitor GDP forecasts to anticipate demand shifts 3-6 months ahead",
            "In slowdowns, pivot sourcing to cost-competitive suppliers",
            "Maintain premium inventory for post-recession recovery"
        ]
    },
    
    "gdp_growth": {
        "name": "GDP Growth Rate",
        "mechanism": """**How it affects trade:**
- Growth rate signals future demand trajectory more than absolute GDP
- Accelerating growth → retailers increase forward orders
- Decelerating growth → inventory reduction, order cancellations
- Negative growth triggers immediate supply chain adjustments

**Trade Impact Pattern:**
- Growth acceleration → Import orders increase 2-3 quarters ahead
- Growth deceleration → Importers reduce commitments, seek discounts
- 2025-2026: Low single-digit global fashion growth due to economic uncertainty""",
        "direction": "positive",
        "sensitivity": "high",
        "lag_months": 6,
        "recommendations": [
            "Track quarterly GDP growth to adjust import forecasts",
            "Build flexible supplier contracts for growth volatility",
            "In slowdowns, focus on core bestsellers vs. trend items"
        ]
    },
    
    "inflation": {
        "name": "Inflation Rate",
        "mechanism": """**How it affects trade:**
- Rising inflation increases production costs (fabrics, labor, shipping)
- Brands like Zara, H&M raised prices 8-15% in 2025-2026
- High inflation squeezes retailer margins, reducing import volumes
- Consumers trade down to affordable imports from low-cost producers

**Trade Impact Pattern:**
- Inflation ↑ → Production costs ↑ → Retail prices ↑ → Volume ↓
- High inflation correlates with shift to China/Bangladesh sourcing
- Inflation >5% typically reduces apparel import growth by 2-4%

**Current Context (2025-2026):**
- Global inflation driving price hikes across fast fashion
- Shift to value-driven purchasing patterns
- Resale market growing 10-12% annually""",
        "direction": "negative",
        "sensitivity": "high",
        "lag_months": 1,
        "recommendations": [
            "Hedge against inflation with forward contracts on key materials",
            "Diversify to low-cost sourcing countries during high inflation",
            "Develop value-tier product lines for price-sensitive consumers"
        ]
    },
    
    "unemployment": {
        "name": "Unemployment Rate",
        "mechanism": """**How it affects trade:**
- Higher unemployment reduces disposable income
- Women's apparel hit harder as it's often seen as discretionary
- Job losses trigger immediate spending cuts on non-essentials
- Economic anxiety affects even employed consumers

**Trade Impact Pattern:**
- Unemployment ↑ 1% → Apparel spending ↓ 1.5-2%
- Resale market grows 10-12% annually in downturns
- Premium segment most affected; basics remain stable

**Consumer Behavior:**
- >60% of global shoppers in 2026 seek to reduce fashion expenses
- Shift from new purchases to secondhand, dupes, repairs""",
        "direction": "negative",
        "sensitivity": "high",
        "lag_months": 0,
        "recommendations": [
            "Develop entry-price points for unemployment-sensitive markets",
            "Partner with resale platforms to capture value-conscious consumers",
            "Focus marketing on value proposition during high unemployment"
        ]
    },
    
    "exchange_rate": {
        "name": "Exchange Rates",
        "mechanism": """**How it affects trade:**
- Currency fluctuations directly affect export competitiveness
- Weaker exporter currency → cheaper exports → volume increase
- Stronger importer currency → cheaper imports → volume increase
- Volatility creates pricing uncertainty for long-term contracts

**Trade Impact Pattern:**
- Yuan depreciation 5% → Chinese apparel exports ↑ 3-4%
- USD strength → U.S. imports cheaper → volume ↑
- Currency wars can reshape global sourcing strategies

**Key Currency Pairs:**
- USD/CNY: Primary for U.S.-China apparel trade
- EUR/USD: Key for EU-U.S. fashion trade
- USD/VND: Growing importance as Vietnam gains share""",
        "direction": "mixed",
        "sensitivity": "high",
        "lag_months": 2,
        "recommendations": [
            "Hedge currency exposure for orders >$1M",
            "Monitor competitor currency advantages for sourcing decisions",
            "Build multi-currency pricing strategies for key markets"
        ]
    },
    
    "interest_rate": {
        "name": "Interest Rates",
        "mechanism": """**How it affects trade:**
- Higher rates increase borrowing costs for manufacturers and retailers
- Working capital becomes more expensive, slowing expansion
- Consumer credit tightens, reducing big-ticket purchases
- Inventory financing costs rise, affecting stock levels

**Trade Impact Pattern:**
- Rate hikes → Retailer expansion slows → Forward orders reduced
- Higher rates → Consumer credit ↓ → Discretionary spending ↓
- Manufacturing investment deferred → Capacity constraints

**Supply Chain Impact:**
- Small/medium suppliers most affected by rate increases
- Factory consolidation during high-rate environments""",
        "direction": "negative",
        "sensitivity": "medium",
        "lag_months": 6,
        "recommendations": [
            "Secure fixed-rate financing before anticipated hikes",
            "Reduce inventory turns to minimize financing needs",
            "Evaluate supplier financial health in high-rate environments"
        ]
    },
    
    "clothing_cpi": {
        "name": "Clothing CPI (Consumer Price Index)",
        "mechanism": """**How it affects trade:**
- Clothing CPI reflects retail price changes passed to consumers
- Rising CPI → Reduced unit sales → Lower import volumes
- CPI outpacing general inflation → Consumer resistance
- Price elasticity of women's apparel: -0.8 to -1.2

**Trade Impact Pattern:**
- Clothing CPI ↑ 5% → Unit sales ↓ 4-6%
- But revenue may remain stable due to higher prices
- Import value vs. volume divergence during price increases

**Current Dynamics:**
- Fast fashion price increases driving CPI higher
- Consumers seeking alternatives (resale, outlet, off-price)
- Premium-to-mass trading down trend""",
        "direction": "negative",
        "sensitivity": "high",
        "lag_months": 0,
        "recommendations": [
            "Track competitor pricing to maintain market position",
            "Develop price architecture with clear value tiers",
            "Invest in off-price/outlet channels during high CPI periods"
        ]
    },
    
    "consumer_confidence": {
        "name": "Consumer Confidence Index (CCI)",
        "mechanism": """**How it affects trade:**
- CCI predicts future spending better than current economic data
- Low confidence → Cautious spending → Secondhand/dupes favored
- CCI drop precedes actual spending decline by 2-3 months
- Fashion is highly sensitive to consumer sentiment

**Trade Impact Pattern:**
- CCI drop 10 points → Apparel spending ↓ 2-3% within 3 months
- Low CCI → Import orders for discretionary items cut first
- High CCI → Forward orders increase, premium segment grows

**2026 Context:**
- >60% of global shoppers seeking to reduce fashion expenses
- Shift to value, resale, and conscious consumption
- Brand loyalty declining as price sensitivity rises""",
        "direction": "positive",
        "sensitivity": "very high",
        "lag_months": 2,
        "recommendations": [
            "Use CCI as leading indicator for demand planning",
            "Develop marketing for value proposition when CCI low",
            "Time new product launches with CCI recovery"
        ]
    },
    
    "female_population": {
        "name": "Female Population & Demographics",
        "mechanism": """**How it affects trade:**
- Direct correlation: More women = Larger addressable market
- Working-age women (15-64) drive majority of purchases
- Female workforce participation increases spending power
- Urbanization concentrates fashion-conscious consumers

**Trade Impact Pattern:**
- Female population ↑ 1% → Women's apparel market ↑ 0.8-1.0%
- Urban female population more valuable per capita
- Emerging markets with young female demographics = high growth

**Key Demographics:**
- Peak spending age: 25-54 years
- Urban females: 2-3x spending vs. rural
- Working women: Higher discretionary income""",
        "direction": "positive",
        "sensitivity": "medium",
        "lag_months": 12,
        "recommendations": [
            "Prioritize markets with growing urban female populations",
            "Develop products for emerging market preferences",
            "Target working women with professional apparel lines"
        ]
    },
    
    "urbanization_rate": {
        "name": "Urbanization Rate",
        "mechanism": """**How it affects trade:**
- Urban consumers have greater access to fashion retail
- Higher brand awareness and fashion consciousness
- Better logistics infrastructure for imports
- Concentration effect enables efficient distribution

**Trade Impact Pattern:**
- Urbanization ↑ → Retail penetration ↑ → Import demand ↑
- Urban markets demand more variety (styles, sizes, trends)
- Rural-to-urban migration creates new consumer segments

**Emerging Market Opportunity:**
- China: 65% urban (still growing)
- India: 35% urban (massive headroom)
- Southeast Asia: Rapid urbanization driving fashion growth""",
        "direction": "positive",
        "sensitivity": "medium",
        "lag_months": 12,
        "recommendations": [
            "Expand distribution in rapidly urbanizing markets",
            "Develop urban-specific product lines (commutewear, athleisure)",
            "Invest in e-commerce for reaching newly urban consumers"
        ]
    },
    
    "tariff_impact": {
        "name": "Tariffs & Trade Policies",
        "mechanism": """**How it affects trade:**
- Direct cost increase on imported goods
- Supply chain restructuring to avoid tariff exposure
- Price increases passed to consumers reduce demand
- Trade diversion to non-tariffed countries

**2025-2026 Context:**
- U.S. tariffs 25-35% hikes on imports from China, Mexico
- Supply chains diversifying to Vietnam, India, Bangladesh
- Low single-digit global fashion growth due to trade uncertainty

**Trade Impact Pattern:**
- Tariff ↑ 10% → Import from that country ↓ 15-25%
- But total imports may remain stable (trade diversion)
- Compliance costs add 2-5% to supply chain costs""",
        "direction": "negative",
        "sensitivity": "very high",
        "lag_months": 3,
        "recommendations": [
            "Diversify sourcing across tariff zones",
            "Build relationships with alternative suppliers proactively",
            "Evaluate nearshoring options to reduce tariff exposure"
        ]
    },
    
    "trade_balance": {
        "name": "Trade Balance & Global Demand",
        "mechanism": """**How it affects trade:**
- Trade deficits indicate import reliance
- Surplus countries have competitive export advantage
- Imbalances can trigger protectionist responses
- Global demand cycles affect all participants

**Trade Impact Pattern:**
- Growing deficit → Political pressure for protection
- Surplus economies export strength may invite retaliation
- Recessions reduce overall global trade volumes

**Key Imbalances:**
- U.S.: Major deficit drives import reliance
- China, Vietnam, Bangladesh: Surplus exporters
- EU: Mixed, varies by country""",
        "direction": "mixed",
        "sensitivity": "medium",
        "lag_months": 6,
        "recommendations": [
            "Monitor trade policy debates in deficit countries",
            "Prepare for potential protectionist measures",
            "Build political risk into sourcing decisions"
        ]
    }
}


class TradeInsightsEngine:
    """Generate consultant-grade trade insights."""
    
    def __init__(self, data: Dict[str, pd.DataFrame] = None):
        self.data = data or {}
        self.indicator_impacts = INDICATOR_IMPACTS
        
    def generate_indicator_insight(
        self,
        indicator: str,
        correlation: float,
        elasticity: float,
        country: str = None,
        current_value: float = None,
        trend: str = None
    ) -> Dict[str, Any]:
        """Generate detailed insight for a specific indicator.
        
        Args:
            indicator: Indicator code
            correlation: Correlation coefficient
            elasticity: Elasticity value
            country: Country context
            current_value: Current value of the indicator
            trend: 'rising', 'falling', or 'stable'
        """
        base_info = self.indicator_impacts.get(indicator, {})
        
        if not base_info:
            return self._generate_generic_insight(indicator, correlation, elasticity)
        
        # Determine impact assessment
        impact_direction = "positive" if correlation > 0 else "negative"
        impact_strength = "strong" if abs(correlation) > 0.5 else ("moderate" if abs(correlation) > 0.3 else "weak")
        
        # Generate contextual recommendation
        current_context = self._get_current_context(indicator, current_value, trend, country)
        
        insight = {
            "indicator": indicator,
            "name": base_info.get("name", indicator),
            "impact_summary": f"{impact_strength.title()} {impact_direction} correlation with trade",
            "correlation": correlation,
            "elasticity": elasticity,
            "mechanism": base_info.get("mechanism", ""),
            "sensitivity": base_info.get("sensitivity", "medium"),
            "lag_months": base_info.get("lag_months", 3),
            "recommendations": base_info.get("recommendations", []),
            "current_context": current_context,
            "action_items": self._generate_action_items(indicator, correlation, trend),
        }
        
        return insight
    
    def _get_current_context(
        self,
        indicator: str,
        value: float,
        trend: str,
        country: str
    ) -> str:
        """Generate current context assessment."""
        if indicator == "gdp_growth":
            if value and value < 0:
                return "⚠️ **Recession Alert**: Negative GDP growth signals demand contraction. Expect import volume reductions and shift to value segments."
            elif value and value < 2:
                return "⚡ **Slow Growth**: Below-trend growth suggests cautious consumer spending. Focus on core products and value positioning."
            elif value and value > 5:
                return "🚀 **Strong Growth**: Robust expansion supports premium positioning and inventory investment."
            
        elif indicator == "inflation":
            if value and value > 5:
                return "🔥 **High Inflation**: Cost pressures intense. Expect margin compression and consumer trading down. Diversify to low-cost suppliers."
            elif value and value > 3:
                return "⚠️ **Elevated Inflation**: Price increases being passed to consumers. Monitor competitive pricing closely."
            elif value and value < 2:
                return "✅ **Stable Prices**: Low inflation environment supports stable margins and consumer confidence."
                
        elif indicator == "unemployment":
            if value and value > 7:
                return "⚠️ **High Unemployment**: Discretionary spending under severe pressure. Shift to value-tier products and resale partnerships."
            elif value and value > 5:
                return "⚡ **Elevated Unemployment**: Consumer caution evident. Emphasize value proposition in marketing."
            elif value and value < 4:
                return "✅ **Full Employment**: Strong labor market supports consumer spending. Opportunity for premium positioning."
                
        elif indicator == "consumer_confidence":
            if value and value < 90:
                return "⚠️ **Low Confidence**: Consumers pessimistic. Expect reduced discretionary spending and shift to essentials."
            elif value and value > 110:
                return "🚀 **High Confidence**: Consumers optimistic. Good environment for new product launches and premium offerings."
        
        if trend == "rising":
            return f"📈 **Trending Up**: {indicator.replace('_', ' ').title()} is increasing, which may {'boost' if self.indicator_impacts.get(indicator, {}).get('direction') == 'positive' else 'pressure'} trade volumes."
        elif trend == "falling":
            return f"📉 **Trending Down**: {indicator.replace('_', ' ').title()} is declining, which may {'reduce' if self.indicator_impacts.get(indicator, {}).get('direction') == 'positive' else 'support'} trade volumes."
        
        return ""
    
    def _generate_action_items(
        self,
        indicator: str,
        correlation: float,
        trend: str
    ) -> List[str]:
        """Generate specific action items based on indicator and trend."""
        actions = []
        
        if indicator in ["gdp", "gdp_growth"] and trend == "falling":
            actions = [
                "Review and reduce forward inventory commitments",
                "Accelerate clearance of non-core SKUs",
                "Negotiate flexible terms with suppliers",
                "Shift marketing budget to value messaging"
            ]
        elif indicator == "inflation" and trend == "rising":
            actions = [
                "Evaluate alternative sourcing from lower-cost countries",
                "Review pricing strategy—pass through costs gradually",
                "Hedge raw material costs where possible",
                "Develop value-tier product options"
            ]
        elif indicator == "unemployment" and trend == "rising":
            actions = [
                "Increase investment in off-price/outlet channels",
                "Partner with resale platforms",
                "Develop entry-price product lines",
                "Reduce marketing spend on premium positioning"
            ]
        elif indicator == "consumer_confidence" and trend == "falling":
            actions = [
                "Delay new product launches until confidence recovers",
                "Increase promotional activity to maintain volume",
                "Focus on essential categories vs. trend items",
                "Monitor competitor pricing weekly"
            ]
        elif indicator == "exchange_rate":
            actions = [
                "Review currency hedging positions",
                "Evaluate supplier cost competitiveness by currency",
                "Consider multi-currency pricing in key markets",
                "Monitor central bank policy announcements"
            ]
        
        return actions or self.indicator_impacts.get(indicator, {}).get("recommendations", [])
    
    def _generate_generic_insight(
        self,
        indicator: str,
        correlation: float,
        elasticity: float
    ) -> Dict[str, Any]:
        """Generate insight for unknown indicators."""
        direction = "positive" if correlation > 0 else "negative"
        strength = "strong" if abs(correlation) > 0.5 else ("moderate" if abs(correlation) > 0.3 else "weak")
        
        return {
            "indicator": indicator,
            "name": indicator.replace("_", " ").title(),
            "impact_summary": f"{strength.title()} {direction} correlation with trade",
            "correlation": correlation,
            "elasticity": elasticity,
            "mechanism": f"A {strength} {direction} relationship exists between {indicator.replace('_', ' ')} and women's apparel trade volumes.",
            "sensitivity": "medium",
            "lag_months": 3,
            "recommendations": [
                f"Monitor {indicator.replace('_', ' ')} trends for trade planning",
                "Include in demand forecasting models",
                "Analyze regional variations in this relationship"
            ],
            "current_context": "",
            "action_items": []
        }
    
    def generate_market_outlook(
        self,
        country: str,
        indicators: Dict[str, float],
        trends: Dict[str, str]
    ) -> Dict[str, Any]:
        """Generate comprehensive market outlook for a country.
        
        Args:
            country: Country code
            indicators: Current indicator values
            trends: Indicator trends ('rising', 'falling', 'stable')
        """
        # Assess overall market health
        positive_factors = []
        negative_factors = []
        watch_items = []
        
        for ind, value in indicators.items():
            impact_info = self.indicator_impacts.get(ind, {})
            direction = impact_info.get("direction", "positive")
            trend = trends.get(ind, "stable")
            
            if direction == "positive":
                if trend == "rising":
                    positive_factors.append(f"{impact_info.get('name', ind)}: Improving ↑")
                elif trend == "falling":
                    negative_factors.append(f"{impact_info.get('name', ind)}: Declining ↓")
            elif direction == "negative":
                if trend == "rising":
                    negative_factors.append(f"{impact_info.get('name', ind)}: Rising ↑ (headwind)")
                elif trend == "falling":
                    positive_factors.append(f"{impact_info.get('name', ind)}: Declining ↓ (tailwind)")
            
            # Flag high-sensitivity indicators changing
            if impact_info.get("sensitivity") in ["high", "very high"] and trend != "stable":
                watch_items.append(f"{impact_info.get('name', ind)}: {trend.title()} - High sensitivity")
        
        # Generate outlook rating
        outlook_score = len(positive_factors) - len(negative_factors)
        if outlook_score >= 3:
            outlook = "Positive"
            outlook_color = "🟢"
        elif outlook_score <= -3:
            outlook = "Negative"
            outlook_color = "🔴"
        elif outlook_score > 0:
            outlook = "Cautiously Positive"
            outlook_color = "🟡"
        elif outlook_score < 0:
            outlook = "Cautiously Negative"
            outlook_color = "🟠"
        else:
            outlook = "Neutral"
            outlook_color = "⚪"
        
        return {
            "country": country,
            "outlook": outlook,
            "outlook_indicator": outlook_color,
            "positive_factors": positive_factors,
            "negative_factors": negative_factors,
            "watch_items": watch_items,
            "outlook_score": outlook_score,
            "summary": self._generate_outlook_summary(country, outlook, positive_factors, negative_factors),
            "strategic_recommendations": self._generate_strategic_recommendations(outlook, negative_factors)
        }
    
    def _generate_outlook_summary(
        self,
        country: str,
        outlook: str,
        positive: List[str],
        negative: List[str]
    ) -> str:
        """Generate narrative outlook summary."""
        summary = f"**{country} Women's Apparel Trade Outlook: {outlook}**\n\n"
        
        if positive:
            summary += "**Tailwinds:**\n"
            for factor in positive[:3]:
                summary += f"- {factor}\n"
        
        if negative:
            summary += "\n**Headwinds:**\n"
            for factor in negative[:3]:
                summary += f"- {factor}\n"
        
        if outlook in ["Positive", "Cautiously Positive"]:
            summary += "\n*Favorable conditions for import growth and premium positioning.*"
        elif outlook in ["Negative", "Cautiously Negative"]:
            summary += "\n*Challenging environment; focus on value positioning and cost management.*"
        else:
            summary += "\n*Mixed signals; maintain flexibility and monitor closely.*"
        
        return summary
    
    def _generate_strategic_recommendations(
        self,
        outlook: str,
        negative_factors: List[str]
    ) -> List[str]:
        """Generate strategic recommendations based on outlook."""
        if outlook in ["Positive", "Cautiously Positive"]:
            return [
                "Consider increasing forward inventory commitments",
                "Opportunity to launch new premium products",
                "Invest in brand building and market share growth",
                "Evaluate capacity expansion with suppliers"
            ]
        elif outlook in ["Negative", "Cautiously Negative"]:
            return [
                "Reduce inventory exposure and maintain liquidity",
                "Focus on core bestsellers; delay trend experiments",
                "Negotiate flexible terms with suppliers",
                "Shift marketing to value messaging",
                "Explore cost reduction through sourcing diversification"
            ]
        else:
            return [
                "Maintain balanced inventory position",
                "Monitor leading indicators closely",
                "Prepare contingency plans for both scenarios",
                "Focus on quick-response supply chain capability"
            ]
    
    def generate_full_analysis_report(
        self,
        correlations: List[Dict],
        country: str = None
    ) -> str:
        """Generate comprehensive analysis report in markdown format."""
        report = f"""# Women's Apparel Trade Analysis Report
## {country or 'Global'} Market Assessment

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*

---

## Executive Summary

This analysis examines how macroeconomic factors influence women's apparel trade volumes, 
providing actionable insights for sourcing, pricing, and market strategy decisions.

### Key Findings

"""
        # Add top correlations with explanations
        for i, corr in enumerate(correlations[:5], 1):
            indicator = corr.get('indicator', '')
            insight = self.generate_indicator_insight(
                indicator,
                corr.get('correlation', 0),
                corr.get('elasticity', 0)
            )
            
            report += f"""
#### {i}. {insight['name']}

**Impact**: {insight['impact_summary']}  
**Correlation**: {corr.get('correlation', 0):.3f} | **Elasticity**: {corr.get('elasticity', 0):.2f}%

{insight['mechanism'][:500]}...

**Recommended Actions:**
"""
            for rec in insight['recommendations'][:3]:
                report += f"- {rec}\n"
        
        report += """

---

## Market Context: 2025-2026

### Macro Environment
- Global fashion growth in low single digits due to economic uncertainty
- Inflation driving price increases across fast fashion (8-15%)
- >60% of global shoppers seeking to reduce fashion expenses
- Resale market growing 10-12% annually

### Trade Policy Impact
- U.S. tariffs 25-35% on imports from China, Mexico
- Supply chain diversification to Vietnam, India, Bangladesh
- Compliance costs adding 2-5% to supply chain costs

### Consumer Behavior Shifts
- Trading down from premium to value segments
- Growth in secondhand, dupes, and off-price channels
- Reduced brand loyalty as price sensitivity increases

---

## Strategic Recommendations

1. **Sourcing Strategy**: Diversify across tariff zones; build alternative supplier relationships
2. **Inventory Management**: Reduce commitments; focus on quick-response capabilities
3. **Pricing Strategy**: Develop clear value tiers; prepare for margin compression
4. **Channel Mix**: Invest in off-price and resale partnerships
5. **Market Focus**: Prioritize markets with stable/growing consumer confidence

---

*This analysis is based on World Bank macroeconomic data and industry research.*
"""
        return report


def get_insights_engine(data: Dict[str, pd.DataFrame] = None) -> TradeInsightsEngine:
    """Factory function to create insights engine."""
    return TradeInsightsEngine(data)
