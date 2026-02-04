"""LLM-powered analysis for trade news summaries."""

import os
from typing import Optional, Dict, Any
from datetime import datetime

from loguru import logger

from .models import NewsArticle, NewsAnalysis
from ..models import SessionLocal


# System prompt for trade analysis
TRADE_ANALYSIS_PROMPT = """You are a trade analyst expert specializing in apparel and fashion industry. 
Analyze news articles and provide concise trade impact summaries.

Focus on:
1. How this news affects global apparel/fashion trade
2. Impact on import/export of clothing, textiles, and accessories
3. Which regions (Asia, US, EU) are most affected
4. Potential price changes for consumers
5. Supply chain implications

Keep summaries brief (2-3 sentences), clear, and actionable for fashion business decisions."""


class LLMAnalyzer:
    """LLM-powered trade news analyzer."""

    def __init__(self):
        """Initialize the LLM analyzer."""
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        
        self._client = None
        self._provider = None
        self._init_client()

    def _init_client(self):
        """Initialize the LLM client based on available API keys."""
        # Try OpenAI first
        if self.openai_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.openai_key)
                self._provider = "openai"
                logger.info("Using OpenAI for LLM analysis")
                return
            except ImportError:
                logger.warning("OpenAI package not installed")

        # Try Anthropic
        if self.anthropic_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.anthropic_key)
                self._provider = "anthropic"
                logger.info("Using Anthropic for LLM analysis")
                return
            except ImportError:
                logger.warning("Anthropic package not installed")

        # Try Ollama (local, free)
        try:
            import httpx
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                self._provider = "ollama"
                logger.info("Using Ollama for LLM analysis (local)")
                return
        except Exception:
            pass

        logger.warning("No LLM provider available. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or run Ollama locally.")

    def _generate_openai(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Generate response using OpenAI."""
        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None

    def _generate_anthropic(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Generate response using Anthropic."""
        try:
            response = self._client.messages.create(
                model="claude-3-haiku-20240307",  # Cost-effective model
                max_tokens=200,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return None

    def _generate_ollama(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Generate response using Ollama (local)."""
        try:
            import httpx
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.2",  # or "mistral", "gemma2"
                    "prompt": f"{system_prompt}\n\n{prompt}",
                    "stream": False,
                    "options": {
                        "num_predict": 200,
                        "temperature": 0.3,
                    }
                },
                timeout=60,
            )
            if response.status_code == 200:
                return response.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
        return None

    def generate_summary(self, title: str, description: str, content: str = None) -> Optional[str]:
        """
        Generate a trade impact summary for a news article.

        Args:
            title: Article title
            description: Article description
            content: Full article content (optional)

        Returns:
            Trade impact summary or None
        """
        if not self._provider:
            return self._generate_fallback_summary(title, description)

        # Build the prompt
        article_text = f"Title: {title}\n"
        if description:
            article_text += f"Description: {description}\n"
        if content:
            article_text += f"Content: {content[:500]}"  # Limit content length

        prompt = f"""Analyze this trade/tariff news and explain its potential impact on apparel and fashion trade in 2-3 sentences:

{article_text}

Focus on: How will this affect clothing imports/exports, supply chains, prices, or specific regions (Asia, US, EU)?"""

        # Generate based on provider
        result = None
        if self._provider == "openai":
            result = self._generate_openai(prompt, TRADE_ANALYSIS_PROMPT)
        elif self._provider == "anthropic":
            result = self._generate_anthropic(prompt, TRADE_ANALYSIS_PROMPT)
        elif self._provider == "ollama":
            result = self._generate_ollama(prompt, TRADE_ANALYSIS_PROMPT)

        # Fallback to rule-based if LLM failed
        if not result:
            result = self._generate_fallback_summary(title, description)
        
        return result

    def _generate_fallback_summary(self, title: str, description: str) -> str:
        """Generate a simple rule-based summary when no LLM is available."""
        summary_parts = []
        
        title_lower = title.lower()
        desc_lower = (description or "").lower()
        combined = f"{title_lower} {desc_lower}"

        # Detect key themes
        if any(word in combined for word in ["tariff", "tax", "duty", "duties"]):
            if any(word in combined for word in ["increase", "raise", "higher", "hike"]):
                summary_parts.append("Tariff increases may raise apparel import costs")
            elif any(word in combined for word in ["cut", "reduce", "lower", "remove"]):
                summary_parts.append("Tariff reductions could lower clothing prices")
            else:
                summary_parts.append("Tariff changes may impact apparel trade costs")

        if "china" in combined:
            summary_parts.append("China trade impact affects major textile supply chains")
        
        if any(word in combined for word in ["vietnam", "bangladesh", "india", "asia"]):
            summary_parts.append("Asian manufacturing and exports may be affected")

        if any(word in combined for word in ["supply chain", "shipping", "logistics"]):
            summary_parts.append("Supply chain disruptions may delay fashion deliveries")

        if any(word in combined for word in ["cotton", "textile", "fabric", "clothing", "apparel", "fashion"]):
            summary_parts.append("Direct impact on fashion/apparel industry expected")

        if not summary_parts:
            summary_parts.append("Trade policy changes may indirectly affect apparel markets")

        return ". ".join(summary_parts[:2]) + "."

    def analyze_article(self, article_id: int) -> Optional[str]:
        """
        Analyze a specific article and save the summary.

        Args:
            article_id: Database ID of the article

        Returns:
            Generated summary or None
        """
        db = SessionLocal()
        try:
            article = db.query(NewsArticle).filter(NewsArticle.id == article_id).first()
            if not article:
                logger.warning(f"Article {article_id} not found")
                return None

            # Check if already has summary
            analysis = db.query(NewsAnalysis).filter(NewsAnalysis.article_id == article_id).first()
            if analysis and analysis.summary:
                return analysis.summary

            # Generate summary
            summary = self.generate_summary(
                title=article.title,
                description=article.description,
                content=article.content,
            )

            if summary and analysis:
                analysis.summary = summary
                db.commit()
                logger.info(f"Generated summary for article {article_id}")

            return summary

        except Exception as e:
            logger.error(f"Error analyzing article {article_id}: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def analyze_batch(self, batch_size: int = 50, force: bool = False) -> Dict[str, int]:
        """
        Analyze a batch of articles without summaries.

        Args:
            batch_size: Number of articles to process
            force: Re-generate summaries even if they exist

        Returns:
            Statistics dictionary
        """
        db = SessionLocal()
        stats = {"processed": 0, "skipped": 0, "failed": 0}

        try:
            # Get articles needing summaries
            if force:
                query = db.query(NewsAnalysis).limit(batch_size)
            else:
                query = db.query(NewsAnalysis).filter(
                    NewsAnalysis.summary.is_(None)
                ).limit(batch_size)

            analyses = query.all()
            logger.info(f"Processing {len(analyses)} articles for LLM summary")

            for analysis in analyses:
                article = db.query(NewsArticle).filter(
                    NewsArticle.id == analysis.article_id
                ).first()

                if not article:
                    stats["skipped"] += 1
                    continue

                try:
                    summary = self.generate_summary(
                        title=article.title,
                        description=article.description,
                        content=article.content,
                    )

                    if summary:
                        analysis.summary = summary
                        stats["processed"] += 1
                        logger.debug(f"Summary for '{article.title[:50]}': {summary[:100]}...")
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    logger.error(f"Error generating summary: {e}")
                    stats["failed"] += 1

            db.commit()

        except Exception as e:
            logger.error(f"Batch analysis failed: {e}")
            db.rollback()
        finally:
            db.close()

        logger.info(f"LLM analysis complete: {stats}")
        return stats
