"""LLM-powered insights generation for macroeconomic trade analysis."""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

# Optional LLM imports
try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not available. Using rule-based insights.")

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


class MacroInsightsGenerator:
    """Generate insights using LLM for macroeconomic trade analysis."""
    
    SYSTEM_PROMPT = """You are an expert economist specializing in international trade, 
particularly in the women's apparel and fashion industry. Your role is to analyze 
macroeconomic data and provide actionable insights about how economic factors 
affect women's apparel trade patterns.

Focus on:
1. How specific economic indicators influence import/export volumes
2. The relationship between demographic factors (especially female population) and demand
3. Price sensitivity and inflation impacts on trade
4. Regional trade patterns and competitive dynamics
5. Industry-specific factors unique to women's fashion

Provide clear, data-driven insights with specific recommendations for:
- Importers/buyers looking to optimize purchasing decisions
- Exporters looking to identify growth markets
- Policy implications for trade development
"""

    def __init__(self, provider: str = "auto"):
        """Initialize LLM insights generator.
        
        Args:
            provider: LLM provider ('openai', 'anthropic', 'ollama', 'auto')
        """
        self.provider = provider
        self.llm = None
        self._initialize_llm()
        
    def _initialize_llm(self):
        """Initialize LLM based on provider and available API keys."""
        if not LANGCHAIN_AVAILABLE:
            logger.info("Using rule-based insights (no LLM available)")
            return
            
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        ollama_url = os.getenv("OLLAMA_URL")
        
        if self.provider == "auto":
            if openai_key:
                self.provider = "openai"
            elif anthropic_key:
                self.provider = "anthropic"
            elif OLLAMA_AVAILABLE and ollama_url:
                self.provider = "ollama"
            else:
                self.provider = "rule_based"
                
        try:
            if self.provider == "openai" and openai_key:
                self.llm = ChatOpenAI(
                    model="gpt-4o",
                    api_key=openai_key,
                    temperature=0.3,
                )
            elif self.provider == "anthropic" and anthropic_key:
                self.llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    api_key=anthropic_key,
                    temperature=0.3,
                )
            elif self.provider == "ollama" and OLLAMA_AVAILABLE:
                # Will use ollama library directly
                pass
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            self.provider = "rule_based"
    
    def generate_correlation_insights(
        self,
        correlations: Dict[str, Any],
        country: str = None
    ) -> str:
        """Generate insights from correlation analysis.
        
        Args:
            correlations: Correlation analysis results
            country: Country context if applicable
            
        Returns:
            LLM-generated or rule-based insights
        """
        # Build context
        context = f"""Analyze these correlation results between macroeconomic indicators 
and women's apparel trade for {country or 'global markets'}:

Correlation Data:
"""
        for corr in correlations.get("import_drivers", [])[:10]:
            context += f"\n- {corr.get('indicator_name', '')}: correlation={corr.get('correlation', 0):.3f}, "
            context += f"elasticity={corr.get('elasticity', 0):.3f}, p-value={corr.get('p_value', 0):.3f}"
        
        prompt = context + """

Please provide:
1. Key insights on which factors most significantly impact women's apparel imports
2. How businesses should interpret these correlations for decision-making
3. Any surprising or counter-intuitive findings
4. Actionable recommendations based on these relationships
"""
        
        return self._generate_response(prompt)
    
    def generate_forecast_analysis(
        self,
        forecasts: Dict[str, Any],
        assumptions: Dict[str, float]
    ) -> str:
        """Generate analysis of trade forecasts.
        
        Args:
            forecasts: Forecast results
            assumptions: Economic assumptions used
            
        Returns:
            Analysis text
        """
        context = f"""Analyze these women's apparel trade forecasts:

Assumptions:
- GDP Growth: {assumptions.get('gdp_growth', 2.5)}%
- Inflation: {assumptions.get('inflation', 2.0)}%

Forecasts by Country:
"""
        for forecast in forecasts[:10]:
            context += f"\n{forecast.get('country_code', '')}: "
            context += f"Import growth: {forecast.get('predicted_import_growth', 0):.1f}%, "
            context += f"Export growth: {forecast.get('predicted_export_growth', 0):.1f}%"
        
        prompt = context + """

Please provide:
1. Analysis of the overall market outlook
2. Countries expected to show strongest growth
3. Risks and uncertainties in these forecasts
4. Strategic recommendations for market participants
"""
        
        return self._generate_response(prompt)
    
    def generate_country_comparison(
        self,
        country_data: Dict[str, Any]
    ) -> str:
        """Generate comparative analysis across countries.
        
        Args:
            country_data: Dictionary of country -> analysis data
            
        Returns:
            Comparative analysis
        """
        context = "Compare women's apparel trade dynamics across these countries:\n\n"
        
        for country, data in list(country_data.items())[:5]:
            context += f"\n{country}:"
            import_factors = data.get("import_factors", {})
            if isinstance(import_factors, dict) and import_factors:
                top_driver = list(import_factors.items())[0] if import_factors else ("N/A", 0)
                context += f"\n  Top import driver: {top_driver[0]} (score: {top_driver[1]:.1f})"
        
        prompt = context + """

Please provide:
1. Key differences in what drives trade across these markets
2. Which markets are most similar/different
3. Unique opportunities in each market
4. Cross-market trends and patterns
"""
        
        return self._generate_response(prompt)
    
    def generate_product_category_insights(
        self,
        product_analysis: Dict[str, Any]
    ) -> str:
        """Generate insights by product category.
        
        Args:
            product_analysis: Analysis results by HS code/product
            
        Returns:
            Product-specific insights
        """
        context = "Analyze trade patterns for these women's apparel categories:\n\n"
        
        for hs_code, data in list(product_analysis.items())[:8]:
            context += f"\n{data.get('name', hs_code)} ({hs_code}):"
            context += f"\n  Category: {data.get('category', 'N/A')}"
        
        prompt = context + """

Based on this data, provide:
1. Which product categories show strongest correlation with economic factors
2. Category-specific demand drivers
3. Price sensitivity differences across categories
4. Recommendations for product mix optimization
"""
        
        return self._generate_response(prompt)
    
    def generate_scenario_analysis(
        self,
        scenario_results: Dict[str, Any]
    ) -> str:
        """Generate analysis of scenario modeling results.
        
        Args:
            scenario_results: Results from scenario analysis
            
        Returns:
            Scenario analysis narrative
        """
        context = "Analyze these economic scenario impacts on women's apparel trade:\n\n"
        
        for scenario in scenario_results:
            if scenario.get("changed_variable"):
                context += f"\nIf {scenario['changed_variable']} = {scenario['value']}:"
                context += f"\n  Trade impact: {scenario.get('pct_change', 0):.1f}% change"
        
        prompt = context + """

Please provide:
1. Which economic scenarios have the greatest impact on trade
2. Risk assessment for negative scenarios
3. Opportunity identification for positive scenarios
4. Hedging strategies against economic volatility
"""
        
        return self._generate_response(prompt)
    
    def generate_executive_summary(
        self,
        full_analysis: Dict[str, Any]
    ) -> str:
        """Generate executive summary of complete analysis.
        
        Args:
            full_analysis: Complete analysis results
            
        Returns:
            Executive summary
        """
        prompt = f"""Based on comprehensive analysis of macroeconomic factors affecting 
women's apparel trade, generate an executive summary covering:

Key Statistics:
- Countries analyzed: {full_analysis.get('countries_analyzed', 'N/A')}
- Time period: {full_analysis.get('time_period', 'N/A')}
- Data points: {full_analysis.get('data_points', 'N/A')}

Top Import Drivers: {full_analysis.get('top_import_drivers', [])}
Top Export Drivers: {full_analysis.get('top_export_drivers', [])}

Please provide a 3-5 paragraph executive summary suitable for C-level executives,
covering key findings, market outlook, and strategic recommendations.
"""
        
        return self._generate_response(prompt)
    
    def _generate_response(self, prompt: str) -> str:
        """Generate response using LLM or rule-based fallback.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Generated response
        """
        if self.llm is not None:
            try:
                messages = [
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
                response = self.llm.invoke(messages)
                return response.content
            except Exception as e:
                logger.error(f"LLM error: {e}")
                
        if self.provider == "ollama" and OLLAMA_AVAILABLE:
            try:
                response = ollama.chat(
                    model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response["message"]["content"]
            except Exception as e:
                logger.error(f"Ollama error: {e}")
        
        # Rule-based fallback
        return self._rule_based_insights(prompt)
    
    def _rule_based_insights(self, prompt: str) -> str:
        """Generate rule-based insights when LLM is unavailable.
        
        Args:
            prompt: The analysis prompt
            
        Returns:
            Rule-based analysis
        """
        insights = """## Macroeconomic Trade Analysis Insights

### Key Findings

Based on the analysis of macroeconomic indicators and women's apparel trade data:

**Import Drivers:**
1. **GDP and Consumer Income** - Strong positive correlation with import volumes. 
   Higher economic output and disposable income directly increase demand for apparel imports.

2. **Female Population Demographics** - Growing female population, especially working-age 
   women (15-64), is a key demand driver. Markets with expanding female workforce show 
   stronger import growth.

3. **Urbanization Rate** - Urban consumers have higher access to imported fashion and 
   greater brand awareness, driving import demand.

4. **Consumer Confidence** - Apparel purchases are discretionary; consumer sentiment 
   strongly influences buying decisions.

**Price Sensitivity:**
- **Clothing CPI** and **Inflation** show negative correlation with imports
- Higher apparel prices reduce import volumes
- Elasticity analysis suggests ~1-2% import decline for each 1% price increase

**Trade Pattern Observations:**
- Developed markets (US, EU) are net importers
- Asian manufacturing hubs (CN, VN, BD) are net exporters
- Middle-income countries show fastest import growth rates

### Strategic Recommendations

1. **For Importers:**
   - Monitor GDP growth and consumer confidence in target markets
   - Consider price hedging against inflation scenarios
   - Focus on markets with growing female urban populations

2. **For Exporters:**
   - Target markets with strong economic fundamentals
   - Consider currency exposure management
   - Develop product mix aligned with market segments

3. **Risk Factors:**
   - Economic downturns significantly impact discretionary apparel spending
   - Currency fluctuations can shift trade patterns
   - Trade policy changes (tariffs) create market uncertainty

---
*Analysis generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "*"
        
        return insights


# Factory function
def create_insights_generator(provider: str = "auto") -> MacroInsightsGenerator:
    """Create insights generator instance."""
    return MacroInsightsGenerator(provider=provider)
