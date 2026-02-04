"""Text analyzer for NLP processing of news articles."""

import re
from collections import Counter
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from loguru import logger

from .config import (
    news_settings,
    TENSION_KEYWORDS,
    EFFECTIVENESS_KEYWORDS,
    ANALYSIS_REGIONS,
)
from .models import NewsArticle, NewsAnalysis, NewsEntity
from ..models import SessionLocal


class TextAnalyzer:
    """NLP-based text analyzer for tariff news."""

    def __init__(self, use_transformers: bool = False):
        """
        Initialize the text analyzer.

        Args:
            use_transformers: Whether to use transformer models (requires more memory)
        """
        self.use_transformers = use_transformers  # Default to False for faster processing
        self._sentiment_pipeline = None
        self._nlp = None

        # Pre-compile region patterns
        self._region_patterns = {}
        for region in ANALYSIS_REGIONS:
            keywords = region["keywords"]
            pattern = re.compile(
                r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b',
                re.IGNORECASE
            )
            self._region_patterns[region["code"]] = {
                "pattern": pattern,
                "name": region["name"],
            }

        # Pre-compile tension keyword patterns
        self._tension_patterns = {}
        for level, keywords in TENSION_KEYWORDS.items():
            pattern = re.compile(
                r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b',
                re.IGNORECASE
            )
            self._tension_patterns[level] = pattern

        # Pre-compile effectiveness keyword patterns
        self._effectiveness_patterns = {}
        for direction, keywords in EFFECTIVENESS_KEYWORDS.items():
            pattern = re.compile(
                r'\b(' + '|'.join(re.escape(k) for k in keywords) + r')\b',
                re.IGNORECASE
            )
            self._effectiveness_patterns[direction] = pattern

    def _load_sentiment_model(self):
        """Load the sentiment analysis model."""
        if self._sentiment_pipeline is not None:
            return

        if self.use_transformers:
            try:
                from transformers import pipeline
                self._sentiment_pipeline = pipeline(
                    "sentiment-analysis",
                    model=news_settings.sentiment_model,
                    top_k=None,  # Return all scores
                )
                logger.info(f"Loaded sentiment model: {news_settings.sentiment_model}")
            except Exception as e:
                logger.warning(f"Failed to load transformer model: {e}")
                self.use_transformers = False

        if not self.use_transformers:
            # Fallback to TextBlob
            logger.info("Using TextBlob for sentiment analysis")

    def _load_nlp_model(self):
        """Load the spaCy NLP model."""
        if self._nlp is not None:
            return

        try:
            import spacy
            self._nlp = spacy.load(news_settings.ner_model)
            logger.info(f"Loaded spaCy model: {news_settings.ner_model}")
        except OSError:
            logger.warning("spaCy model not found. Downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", news_settings.ner_model])
            import spacy
            self._nlp = spacy.load(news_settings.ner_model)

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text using FinBERT or TextBlob.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment, score, and confidence
        """
        self._load_sentiment_model()

        # Truncate text for transformer models
        max_length = 512
        truncated_text = text[:max_length] if len(text) > max_length else text

        if self.use_transformers and self._sentiment_pipeline:
            try:
                results = self._sentiment_pipeline(truncated_text)

                # FinBERT returns list of dicts with label and score
                if isinstance(results, list) and len(results) > 0:
                    if isinstance(results[0], list):
                        results = results[0]

                    # Find best sentiment
                    best = max(results, key=lambda x: x["score"])
                    label = best["label"].lower()

                    # Map FinBERT labels
                    label_map = {"positive": "positive", "negative": "negative", "neutral": "neutral"}
                    sentiment = label_map.get(label, "neutral")

                    # Calculate score (-1 to 1)
                    score_map = {"positive": 1, "negative": -1, "neutral": 0}
                    base_score = score_map.get(sentiment, 0)
                    score = base_score * best["score"]

                    return {
                        "sentiment": sentiment,
                        "score": score,
                        "confidence": best["score"],
                    }

            except Exception as e:
                logger.error(f"Transformer sentiment analysis failed: {e}")

        # Fallback to TextBlob
        try:
            from textblob import TextBlob
            blob = TextBlob(truncated_text)
            polarity = blob.sentiment.polarity

            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            return {
                "sentiment": sentiment,
                "score": polarity,
                "confidence": abs(polarity),
            }

        except Exception as e:
            logger.error(f"TextBlob sentiment analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "confidence": 0.0,
            }

    def analyze_regions(self, text: str) -> Dict[str, Any]:
        """
        Identify regions mentioned in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with primary region, all regions, and scores
        """
        region_counts = {}

        for code, data in self._region_patterns.items():
            matches = data["pattern"].findall(text)
            if matches:
                region_counts[code] = len(matches)

        if not region_counts:
            return {
                "primary_region": None,
                "regions_mentioned": [],
                "region_scores": {},
            }

        # Calculate scores (normalized by total mentions)
        total = sum(region_counts.values())
        region_scores = {k: v / total for k, v in region_counts.items()}

        # Find primary region
        primary_region = max(region_counts, key=region_counts.get)

        return {
            "primary_region": primary_region,
            "regions_mentioned": list(region_counts.keys()),
            "region_scores": region_scores,
        }

    def analyze_tension(self, text: str) -> Dict[str, Any]:
        """
        Analyze trade tension level in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with tension level, score, and keywords
        """
        tension_scores = {}
        matched_keywords = {}

        for level, pattern in self._tension_patterns.items():
            matches = pattern.findall(text)
            if matches:
                tension_scores[level] = len(matches)
                matched_keywords[level] = list(set(m.lower() for m in matches))

        if not tension_scores:
            return {
                "tension_level": "neutral",
                "tension_score": 0.0,
                "tension_keywords": {},
            }

        # Calculate weighted tension score
        weights = {
            "high_tension": 1.0,
            "moderate_tension": 0.6,
            "low_tension": 0.3,
            "positive": -0.5,  # Positive news reduces tension
        }

        total_score = sum(
            weights.get(level, 0) * count
            for level, count in tension_scores.items()
        )
        max_possible = sum(tension_scores.values())
        normalized_score = total_score / max_possible if max_possible > 0 else 0

        # Determine level
        if normalized_score >= 0.7:
            level = "high"
        elif normalized_score >= 0.4:
            level = "moderate"
        elif normalized_score >= 0:
            level = "low"
        else:
            level = "positive"

        return {
            "tension_level": level,
            "tension_score": min(max(normalized_score, -1), 1),  # Clamp to [-1, 1]
            "tension_keywords": matched_keywords,
        }

    def analyze_effectiveness(self, text: str) -> Dict[str, Any]:
        """
        Analyze trade effectiveness indicators in text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with direction, score, and keywords
        """
        matched_keywords = {}
        scores = {"positive_impact": 0, "negative_impact": 0}

        for direction, pattern in self._effectiveness_patterns.items():
            matches = pattern.findall(text)
            if matches:
                scores[direction] = len(matches)
                matched_keywords[direction] = list(set(m.lower() for m in matches))

        # Calculate effectiveness score
        pos = scores["positive_impact"]
        neg = scores["negative_impact"]
        total = pos + neg

        if total == 0:
            return {
                "effectiveness_direction": "neutral",
                "effectiveness_score": 0.0,
                "effectiveness_keywords": {},
            }

        score = (pos - neg) / total

        if score > 0.2:
            direction = "positive"
        elif score < -0.2:
            direction = "negative"
        else:
            direction = "neutral"

        return {
            "effectiveness_direction": direction,
            "effectiveness_score": score,
            "effectiveness_keywords": matched_keywords,
        }

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text using spaCy.

        Args:
            text: Text to analyze

        Returns:
            List of entity dictionaries
        """
        self._load_nlp_model()

        if not self._nlp:
            return []

        try:
            # Limit text length for processing
            max_length = 10000
            truncated = text[:max_length] if len(text) > max_length else text

            doc = self._nlp(truncated)

            # Count entities
            entity_counter = Counter()
            for ent in doc.ents:
                if ent.label_ in ["ORG", "GPE", "PERSON", "MONEY", "PERCENT", "PRODUCT", "EVENT"]:
                    key = (ent.text, ent.label_)
                    entity_counter[key] += 1

            entities = []
            for (text, label), count in entity_counter.most_common(50):
                # Truncate long entity text
                clean_text = text[:450] if len(text) > 450 else text
                entities.append({
                    "entity_text": clean_text,
                    "entity_type": label,
                    "entity_label": self._normalize_entity(clean_text, label)[:180],
                    "count": count,
                })

            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def _normalize_entity(self, text: str, label: str) -> str:
        """Normalize entity text."""
        # Simple normalization - can be extended
        normalized = text.strip()

        # Handle common variations
        if label == "GPE":
            # Country name normalization
            country_map = {
                "USA": "United States",
                "U.S.": "United States",
                "UK": "United Kingdom",
                "PRC": "China",
            }
            normalized = country_map.get(normalized.upper(), normalized)

        return normalized

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
        Extract key phrases from text.

        Args:
            text: Text to analyze
            top_n: Number of keywords to return

        Returns:
            List of key phrases
        """
        self._load_nlp_model()

        if not self._nlp:
            return []

        try:
            # Clean HTML from text
            import re
            clean_text = re.sub(r'<[^>]+>', '', text)
            clean_text = re.sub(r'&[a-z]+;', ' ', clean_text)
            
            doc = self._nlp(clean_text[:5000])  # Limit text length

            # Extract noun chunks as keywords
            keywords = []
            for chunk in doc.noun_chunks:
                chunk_text = chunk.text.strip()
                # Filter out short, common phrases, or those with special chars
                if (len(chunk_text) > 3 and 
                    chunk.root.pos_ in ["NOUN", "PROPN"] and
                    not chunk_text.startswith('http') and
                    '<' not in chunk_text):
                    keywords.append(chunk_text.lower()[:100])

            # Count and return top keywords
            keyword_counts = Counter(keywords)
            return [kw for kw, _ in keyword_counts.most_common(top_n)]

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []

    def analyze_article(self, article: NewsArticle) -> Optional[NewsAnalysis]:
        """
        Perform full analysis on a news article.

        Args:
            article: NewsArticle to analyze

        Returns:
            NewsAnalysis object or None
        """
        # Combine title, description, and content
        text_parts = [
            article.title or "",
            article.description or "",
            article.content or "",
        ]
        full_text = " ".join(filter(None, text_parts))

        if not full_text.strip():
            logger.warning(f"Article {article.id} has no text content")
            return None

        try:
            # Perform analyses
            sentiment = self.analyze_sentiment(full_text)
            regions = self.analyze_regions(full_text)
            tension = self.analyze_tension(full_text)
            effectiveness = self.analyze_effectiveness(full_text)
            entities = self.extract_entities(full_text)
            keywords = self.extract_keywords(full_text)

            # Create analysis object
            analysis = NewsAnalysis(
                article_id=article.id,
                sentiment=sentiment["sentiment"],
                sentiment_score=sentiment["score"],
                sentiment_confidence=sentiment["confidence"],
                tension_level=tension["tension_level"],
                tension_score=tension["tension_score"],
                tension_keywords=tension["tension_keywords"],
                effectiveness_direction=effectiveness["effectiveness_direction"],
                effectiveness_score=effectiveness["effectiveness_score"],
                effectiveness_keywords=effectiveness["effectiveness_keywords"],
                primary_region=regions["primary_region"],
                regions_mentioned=regions["regions_mentioned"],
                region_scores=regions["region_scores"],
                keywords_extracted=keywords,
                analyzed_at=datetime.utcnow(),
            )

            return analysis, entities

        except Exception as e:
            logger.error(f"Article analysis failed: {e}")
            return None

    def analyze_unprocessed_articles(self, batch_size: int = 50) -> Dict[str, int]:
        """
        Analyze all unprocessed articles in the database.

        Args:
            batch_size: Number of articles to process per batch

        Returns:
            Dictionary with processing statistics
        """
        db = SessionLocal()
        stats = {"processed": 0, "failed": 0, "entities": 0}

        try:
            # Get unprocessed articles
            articles = db.query(NewsArticle).filter(
                NewsArticle.is_analyzed == False
            ).limit(batch_size).all()

            logger.info(f"Processing {len(articles)} unanalyzed articles")

            for article in articles:
                result = self.analyze_article(article)

                if result:
                    analysis, entities = result

                    # Save analysis
                    db.add(analysis)

                    # Save entities
                    for entity_data in entities:
                        entity = NewsEntity(
                            article_id=article.id,
                            **entity_data
                        )
                        db.add(entity)
                        stats["entities"] += 1

                    # Mark article as analyzed
                    article.is_analyzed = True
                    article.analyzed_at = datetime.utcnow()

                    db.commit()
                    stats["processed"] += 1
                    logger.info(f"Analyzed article {article.id}: {article.title[:50]}...")
                else:
                    stats["failed"] += 1

        except Exception as e:
            logger.error(f"Batch analysis failed: {e}")
            db.rollback()

        finally:
            db.close()

        logger.info(f"Analysis complete: {stats}")
        return stats
