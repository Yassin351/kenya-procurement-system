import re
import json
import asyncio
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import Counter
import numpy as np
from functools import lru_cache

# ML/NLP imports (install: pip install transformers scikit-learn)
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

import structlog
from core.config import Settings
from core.cache import CacheManager
from core.monitoring import MetricsCollector
from core.exceptions import MLModelError

logger = structlog.get_logger("sentiment_analyzer")


class ReviewAuthenticity(Enum):
    GENUINE = "genuine"
    SUSPICIOUS = "suspicious"
    FAKE = "fake"
    UNCERTAIN = "uncertain"


class SellerRecommendation(Enum):
    HIGHLY_RECOMMENDED = "highly_recommended"
    RECOMMENDED = "recommended"
    CAUTION = "caution"
    AVOID = "avoid"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class ReviewFeatures:
    """Extracted features from a review for ML analysis"""
    text_length: int
    word_count: int
    avg_word_length: float
    punctuation_ratio: float
    caps_ratio: float
    exclamation_count: int
    question_count: int
    duplicate_word_ratio: float
    sentiment_polarity: float
    sentiment_subjectivity: float
    has_price_mention: bool
    has_url: bool
    timestamp: Optional[datetime] = None


@dataclass
class ReviewAnalysis:
    """Complete analysis result for a single review"""
    original_text: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str
    authenticity_score: float  # 0 to 1 (1 = genuine)
    authenticity_label: ReviewAuthenticity
    features: ReviewFeatures
    fake_indicators: List[str] = field(default_factory=list)
    authentic_indicators: List[str] = field(default_factory=list)
    confidence: float = 0.0
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sentiment_score': round(self.sentiment_score, 3),
            'sentiment_label': self.sentiment_label,
            'authenticity_score': round(self.authenticity_score, 3),
            'authenticity_label': self.authenticity_label.value,
            'fake_indicators_found': self.fake_indicators,
            'authentic_indicators_found': self.authentic_indicators,
            'confidence': round(self.confidence, 3),
            'features': {
                'text_length': self.features.text_length,
                'word_count': self.features.word_count,
                'has_price_mention': self.features.has_price_mention,
            }
        }


@dataclass
class SellerTrustReport:
    """Comprehensive seller analysis report"""
    seller_id: Optional[str]
    total_reviews: int
    genuine_percentage: float
    suspicious_percentage: float
    fake_percentage: float
    average_sentiment: float
    sentiment_distribution: Dict[str, int]
    trust_score: float  # 0 to 1
    recommendation: SellerRecommendation
    risk_factors: List[str]
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'seller_id': self.seller_id,
            'total_reviews': self.total_reviews,
            'authenticity_breakdown': {
                'genuine_pct': round(self.genuine_percentage, 1),
                'suspicious_pct': round(self.suspicious_percentage, 1),
                'fake_pct': round(self.fake_percentage, 1)
            },
            'average_sentiment': round(self.average_sentiment, 3),
            'sentiment_distribution': self.sentiment_distribution,
            'trust_score': round(self.trust_score, 3),
            'recommendation': self.recommendation.value,
            'risk_factors': self.risk_factors,
            'analyzed_at': self.analyzed_at.isoformat()
        }


class FakeReviewDetector:
    """
    Advanced fake review detection using linguistic patterns,
    behavioral analysis, and optional ML models.
    """
    
    # Expanded indicator sets with weights
    FAKE_PATTERNS = {
        # Direct fake mentions (weight 3)
        'fake': 3, 'counterfeit': 3, 'not original': 3, 'clone': 3,
        'bandia': 3, 'feki': 3, 'duplicate': 2, 'knockoff': 3,
        'imitation': 2, 'replica': 2, 'scam': 3, 'fraud': 3,
        
        # Quality complaints suggesting fake (weight 2)
        'poor quality': 2, 'cheap material': 2, 'fell apart': 2,
        'stopped working': 2, 'not as described': 1, 'waste of money': 1,
        'defective': 2, 'broken': 1, 'damaged': 1,
        
        # Suspicious patterns (weight 2)
        'too good to be true': 2, 'suspiciously cheap': 2,
        'no serial number': 3, 'missing logo': 2, 'wrong packaging': 2,
        
        # Kenyan market specific
        'mtumba fake': 3, 'second hand disguised': 3, 'refurbished as new': 3,
    }
    
    AUTHENTIC_PATTERNS = {
        # Direct authentic mentions (weight 3)
        'genuine': 3, 'original': 3, 'authentic': 3, 'verified purchase': 3,
        'official': 2, 'licensed': 2, 'warranty valid': 3,
        
        # Quality positives (weight 1)
        'excellent quality': 1, 'high quality': 1, 'premium': 1,
        'durable': 1, 'reliable': 1, 'works perfectly': 1,
        
        # Trust signals (weight 2)
        'fast delivery': 1, 'good packaging': 1, 'responsive seller': 1,
        'as described': 2, 'exactly as pictured': 2,
        
        # Kenyan specific
        'original kenya': 2, 'authorized dealer': 3, 'with receipt': 2,
    }
    
    # Behavioral fake indicators
    SUSPICIOUS_BEHAVIORS = [
        r'\b\d{1,2}\s*stars?\b',  # Rating mentioned in text
        r'(posted|reviewed)\s*(on|at)\s*\d{1,2}[\/\.-]\d{1,2}',  # Date mentions
        r'http[s]?://',  # URLs in reviews
        r'\b[A-Z]{5,}\b',  # Excessive caps
        r'(.)\1{4,}',  # Repeated characters (e.g., "sooooo")
        r'\b\d{3,}\s*(ksh|kes|kshs)\b',  # Specific price mentions
    ]
    
    def __init__(self, use_ml: bool = True):
        self.use_ml = use_ml and TRANSFORMERS_AVAILABLE
        self.ml_pipeline = None
        self.nlp = None
        
        if self.use_ml:
            self._load_ml_model()
        
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spacy_model_not_found")
        
        self.behavioral_patterns = [re.compile(p, re.IGNORECASE) for p in self.SUSPICIOUS_BEHAVIORS]
        logger.info("fake_review_detector_initialized", ml_enabled=self.use_ml)

    def _load_ml_model(self):
        """Load pre-trained fake review detection model"""
        try:
            # Using a sentiment model as proxy; ideally use fine-tuned fake review detector
            model_name = "distilbert-base-uncased-finetuned-sst-2-english"
            self.ml_pipeline = pipeline(
                "sentiment-analysis",
                model=model_name,
                tokenizer=model_name,
                device=-1  # CPU
            )
            logger.info("ml_model_loaded", model=model_name)
        except Exception as e:
            logger.error("ml_model_load_failed", error=str(e))
            self.use_ml = False

    def extract_features(self, text: str) -> ReviewFeatures:
        """Extract linguistic features for analysis"""
        if not text:
            return ReviewFeatures(0, 0, 0.0, 0.0, 0.0, 0, 0, 0.0, 0.0, 0.0, False, False)
        
        # Basic stats
        text_length = len(text)
        words = text.split()
        word_count = len(words)
        avg_word_length = np.mean([len(w) for w in words]) if words else 0
        
        # Punctuation analysis
        punct_count = sum(1 for c in text if c in '.,;:!?')
        punctuation_ratio = punct_count / text_length if text_length > 0 else 0
        
        # Capitalization
        caps_count = sum(1 for c in text if c.isupper())
        caps_ratio = caps_count / text_length if text_length > 0 else 0
        
        # Duplicates
        word_freq = Counter(words)
        duplicates = sum(1 for count in word_freq.values() if count > 1)
        duplicate_ratio = duplicates / word_count if word_count > 0 else 0
        
        # Sentiment (fallback to TextBlob if no ML)
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
        except ImportError:
            polarity, subjectivity = 0.0, 0.0
        
        # Content indicators
        has_price = bool(re.search(r'(ksh|kes|\$|€|£)\s*\d', text, re.IGNORECASE))
        has_url = bool(re.search(r'http[s]?://|www\.', text))
        
        return ReviewFeatures(
            text_length=text_length,
            word_count=word_count,
            avg_word_length=avg_word_length,
            punctuation_ratio=punctuation_ratio,
            caps_ratio=caps_ratio,
            exclamation_count=text.count('!'),
            question_count=text.count('?'),
            duplicate_word_ratio=duplicate_ratio,
            sentiment_polarity=polarity,
            sentiment_subjectivity=subjectivity,
            has_price_mention=has_price,
            has_url=has_url
        )

    def calculate_authenticity_score(
        self, 
        text: str, 
        features: ReviewFeatures
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculate authenticity score (0-1, higher = more genuine)
        Returns: (score, fake_indicators_found, authentic_indicators_found)
        """
        text_lower = text.lower()
        
        # Pattern matching with weights
        fake_score = 0
        fake_indicators = []
        for pattern, weight in self.FAKE_PATTERNS.items():
            if pattern in text_lower:
                fake_score += weight
                fake_indicators.append(pattern)
        
        authentic_score = 0
        authentic_indicators = []
        for pattern, weight in self.AUTHENTIC_PATTERNS.items():
            if pattern in text_lower:
                authentic_score += weight
                authentic_indicators.append(pattern)
        
        # Behavioral analysis
        behavioral_flags = sum(1 for p in self.behavioral_patterns if p.search(text))
        
        # Feature-based heuristics
        feature_risk = 0
        if features.caps_ratio > 0.3:
            feature_risk += 1
        if features.duplicate_word_ratio > 0.5:
            feature_risk += 1
        if features.exclamation_count > 3:
            feature_risk += 0.5
        
        # Calculate final score
        base_score = 0.5  # Neutral starting point
        indicator_impact = (authentic_score - fake_score) * 0.1
        behavioral_penalty = behavioral_flags * 0.05
        feature_penalty = feature_risk * 0.05
        
        authenticity = base_score + indicator_impact - behavioral_penalty - feature_penalty
        authenticity = max(0.0, min(1.0, authenticity))  # Clamp to 0-1
        
        return authenticity, fake_indicators, authentic_indicators

    def ml_predict(self, text: str) -> Optional[float]:
        """Get ML model prediction if available"""
        if not self.use_ml or not self.ml_pipeline:
            return None
        
        try:
            # Truncate if too long for model
            truncated = text[:512]
            result = self.ml_pipeline(truncated)[0]
            # Convert to authenticity score (positive sentiment = more likely genuine)
            score = result['score'] if result['label'] == 'POSITIVE' else 1 - result['score']
            return score
        except Exception as e:
            logger.warning("ml_prediction_failed", error=str(e))
            return None


class ReviewAnalyzer:
    """
    Production-ready review analysis engine with caching,
    metrics, and comprehensive fake detection.
    """
    
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        metrics: Optional[MetricsCollector] = None,
        use_ml: bool = True
    ):
        self.detector = FakeReviewDetector(use_ml=use_ml)
        self.cache = cache_manager or CacheManager()
        self.metrics = metrics or MetricsCollector()
        self.settings = Settings()
        
        # Analysis thresholds
        self.SENTIMENT_THRESHOLDS = {
            'very_positive': 0.6,
            'positive': 0.2,
            'neutral': -0.2,
            'negative': -0.6
        }
        
        self.AUTHENTICITY_THRESHOLDS = {
            'genuine': 0.7,
            'suspicious': 0.4,
            'fake': 0.0
        }

    def _get_sentiment_label(self, score: float) -> str:
        """Convert numeric sentiment to label"""
        if score >= self.SENTIMENT_THRESHOLDS['very_positive']:
            return 'very_positive'
        elif score >= self.SENTIMENT_THRESHOLDS['positive']:
            return 'positive'
        elif score >= self.SENTIMENT_THRESHOLDS['neutral']:
            return 'neutral'
        elif score >= self.SENTIMENT_THRESHOLDS['negative']:
            return 'negative'
        return 'very_negative'

    def _get_authenticity_label(self, score: float) -> ReviewAuthenticity:
        """Classify authenticity score"""
        if score >= self.AUTHENTICITY_THRESHOLDS['genuine']:
            return ReviewAuthenticity.GENUINE
        elif score >= self.AUTHENTICITY_THRESHOLDS['suspicious']:
            return ReviewAuthenticity.SUSPICIOUS
        elif score > self.AUTHENTICITY_THRESHOLDS['fake']:
            return ReviewAuthenticity.FAKE
        return ReviewAuthenticity.UNCERTAIN

    async def analyze_review(self, review_text: str, review_id: Optional[str] = None) -> ReviewAnalysis:
        """
        Comprehensive single review analysis with caching.
        """
        if not review_text or not review_text.strip():
            return self._empty_analysis(review_text or "")
        
        # Check cache
        cache_key = f"review_analysis:{hash(review_text)}"
        cached = await self.cache.get(cache_key)
        if cached:
            self.metrics.increment("review_analysis.cache_hit")
            return ReviewAnalysis(**cached)
        
        start_time = datetime.now()
        
        # Feature extraction
        features = self.detector.extract_features(review_text)
        
        # Authenticity analysis
        auth_score, fake_inds, auth_inds = self.detector.calculate_authenticity_score(
            review_text, features
        )
        
        # ML enhancement
        ml_score = self.detector.ml_predict(review_text)
        if ml_score is not None:
            # Weighted combination: 70% heuristic, 30% ML
            auth_score = (auth_score * 0.7) + (ml_score * 0.3)
        
        # Sentiment
        sentiment = features.sentiment_polarity
        
        # Classification
        auth_label = self._get_authenticity_label(auth_score)
        sentiment_label = self._get_sentiment_label(sentiment)
        
        # Confidence based on text length and indicator strength
        confidence = min(1.0, (len(review_text) / 100) * 0.5 + abs(auth_score - 0.5) * 0.5)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = ReviewAnalysis(
            original_text=review_text[:500],  # Truncate for storage
            sentiment_score=sentiment,
            sentiment_label=sentiment_label,
            authenticity_score=auth_score,
            authenticity_label=auth_label,
            features=features,
            fake_indicators=fake_inds,
            authentic_indicators=auth_inds,
            confidence=confidence,
            processing_time_ms=processing_time
        )
        
        # Cache and metrics
        await self.cache.set(cache_key, result.to_dict(), ttl=86400)  # 24h
        self.metrics.histogram("review_analysis.latency_ms", processing_time)
        self.metrics.increment(f"review_analysis.authenticity.{auth_label.value}")
        
        return result

    def _empty_analysis(self, text: str) -> ReviewAnalysis:
        """Return empty analysis for invalid input"""
        return ReviewAnalysis(
            original_text=text,
            sentiment_score=0.0,
            sentiment_label='neutral',
            authenticity_score=0.5,
            authenticity_label=ReviewAuthenticity.UNCERTAIN,
            features=self.detector.extract_features(""),
            confidence=0.0
        )

    async def analyze_seller_reviews(
        self,
        reviews: List[str],
        seller_id: Optional[str] = None,
        weights: Optional[List[float]] = None
    ) -> SellerTrustReport:
        """
        Comprehensive seller trust analysis with weighted reviews.
        """
        if not reviews:
            return SellerTrustReport(
                seller_id=seller_id,
                total_reviews=0,
                genuine_percentage=0.0,
                suspicious_percentage=0.0,
                fake_percentage=0.0,
                average_sentiment=0.0,
                sentiment_distribution={},
                trust_score=0.5,
                recommendation=SellerRecommendation.INSUFFICIENT_DATA,
                risk_factors=["insufficient_review_data"]
            )
        
        # Analyze all reviews concurrently
        analyses = await asyncio.gather(*[
            self.analyze_review(r) for r in reviews
        ])
        
        # Calculate distributions
        total = len(analyses)
        sentiment_dist = Counter(a.sentiment_label for a in analyses)
        
        authenticity_counts = Counter(a.authenticity_label for a in analyses)
        genuine_pct = (authenticity_counts[ReviewAuthenticity.GENUINE] / total) * 100
        suspicious_pct = (authenticity_counts[ReviewAuthenticity.SUSPICIOUS] / total) * 100
        fake_pct = (authenticity_counts[ReviewAuthenticity.FAKE] / total) * 100
        
        # Weighted average sentiment
        if weights:
            avg_sentiment = np.average([a.sentiment_score for a in analyses], weights=weights)
        else:
            avg_sentiment = np.mean([a.sentiment_score for a in analyses])
        
        # Trust score calculation
        # Factors: authenticity (60%), sentiment (25%), volume (15%)
        volume_factor = min(1.0, total / 50)  # Max bonus at 50+ reviews
        
        trust_score = (
            (genuine_pct / 100) * 0.6 +
            ((avg_sentiment + 1) / 2) * 0.25 +
            volume_factor * 0.15
        ) * (1 - (fake_pct / 100) * 0.5)  # Penalty for fake reviews
        
        # Risk factors
        risk_factors = []
        if fake_pct > 20:
            risk_factors.append("high_fake_review_rate")
        if suspicious_pct > 30:
            risk_factors.append("elevated_suspicious_activity")
        if avg_sentiment < -0.3:
            risk_factors.append("predominantly_negative_sentiment")
        if total < 5:
            risk_factors.append("low_review_volume")
        if any(a.features.has_url for a in analyses):
            risk_factors.append("reviews_contain_urls")
        
        # Recommendation logic
        if total < 3:
            recommendation = SellerRecommendation.INSUFFICIENT_DATA
        elif fake_pct > 30 or trust_score < 0.3:
            recommendation = SellerRecommendation.AVOID
        elif fake_pct > 15 or suspicious_pct > 40 or trust_score < 0.6:
            recommendation = SellerRecommendation.CAUTION
        elif trust_score > 0.85 and genuine_pct > 80:
            recommendation = SellerRecommendation.HIGHLY_RECOMMENDED
        else:
            recommendation = SellerRecommendation.RECOMMENDED
        
        report = SellerTrustReport(
            seller_id=seller_id,
            total_reviews=total,
            genuine_percentage=genuine_pct,
            suspicious_percentage=suspicious_pct,
            fake_percentage=fake_pct,
            average_sentiment=avg_sentiment,
            sentiment_distribution=dict(sentiment_dist),
            trust_score=trust_score,
            recommendation=recommendation,
            risk_factors=risk_factors
        )
        
        self.metrics.gauge("seller_trust.score", trust_score, tags={"seller": seller_id})
        
        return report

    def batch_analyze(self, reviews: List[str]) -> List[Dict]:
        """Synchronous batch analysis for legacy compatibility"""
        return asyncio.run(self._batch_analyze_async(reviews))

    async def _batch_analyze_async(self, reviews: List[str]) -> List[Dict]:
        results = await asyncio.gather(*[self.analyze_review(r) for r in reviews])
        return [r.to_dict() for r in results]


# Project integration functions
_analyzer_instance: Optional[ReviewAnalyzer] = None

def get_analyzer(use_ml: bool = True) -> ReviewAnalyzer:
    """Singleton analyzer instance"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ReviewAnalyzer(use_ml=use_ml)
    return _analyzer_instance


async def analyze_reviews(
    reviews: List[str],
    seller_id: Optional[str] = None,
    detailed: bool = False
) -> Dict[str, Any]:
    """
    Primary project interface for seller review analysis.
    
    Args:
        reviews: List of review texts
        seller_id: Optional seller identifier
        detailed: If True, includes individual review analyses
    
    Returns:
        Seller trust report dictionary
    """
    analyzer = get_analyzer()
    report = await analyzer.analyze_seller_reviews(reviews, seller_id)
    
    result = report.to_dict()
    
    if detailed:
        individual = await asyncio.gather(*[
            analyzer.analyze_review(r) for r in reviews
        ])
        result['individual_reviews'] = [r.to_dict() for r in individual]
    
    return result


def quick_sentiment_check(text: str) -> Dict[str, Any]:
    """
    Fast synchronous sentiment check for single reviews.
    """
    analyzer = get_analyzer(use_ml=False)  # Faster without ML
    # Run async in sync context
    result = asyncio.run(analyzer.analyze_review(text))
    return result.to_dict()


# Backwards compatibility
class LegacyReviewAnalyzer(ReviewAnalyzer):
    """Maintains old interface for existing code"""
    
    FAKE_INDICATORS = list(FakeReviewDetector.FAKE_PATTERNS.keys())
    AUTHENTIC_INDICATORS = list(FakeReviewDetector.AUTHENTIC_PATTERNS.keys())
    
    def analyze_review(self, review_text: str) -> Dict:
        """Legacy single review analysis"""
        result = asyncio.run(super().analyze_review(review_text))
        return {
            'sentiment': result.sentiment_score,
            'is_fake_suspicious': result.authenticity_label in [ReviewAuthenticity.SUSPICIOUS, ReviewAuthenticity.FAKE],
            'fake_indicators_found': len(result.fake_indicators)
        }
    
    def analyze_seller_reviews(self, reviews: List[str]) -> Dict:
        """Legacy seller analysis"""
        report = asyncio.run(super().analyze_seller_reviews(reviews))
        return {
            'trust_score': report.trust_score,
            'fake_review_percentage': report.fake_percentage,
            'recommendation': report.recommendation.value.replace('_', ' ')
        }


def analyze_reviews_legacy(reviews: List[str]) -> Dict:
    """Legacy function signature"""
    return LegacyReviewAnalyzer().analyze_seller_reviews(reviews)