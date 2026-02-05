import os
import re
import time
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import httpx
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)
import structlog
from functools import lru_cache

# Project-specific imports (adjust paths as needed)
from core.config import Settings
from core.exceptions import ExternalServiceError, ConfigurationError
from core.cache import CacheManager
from core.monitoring import MetricsCollector

logger = structlog.get_logger("google_shopping")


class PriceCurrency(Enum):
    KES = "KSh"
    USD = "$"
    EUR = "€"


@dataclass
class ProductResult:
    """Structured product data model"""
    platform: str = "Google"
    seller: str = "Unknown"
    product_name: str = "Unknown"
    price: float = 0.0
    currency: str = "KES"
    url: str = ""
    image_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'platform': self.platform,
            'seller': self.seller,
            'product_name': self.product_name,
            'price': self.price,
            'currency': self.currency,
            'url': self.url,
            'image_url': self.image_url,
            'rating': self.rating,
            'review_count': self.review_count,
            'timestamp': self.timestamp,
            'scraped_at': datetime.fromtimestamp(self.timestamp).isoformat()
        }


class GoogleShoppingClient:
    """
    Production-ready Google Custom Search client optimized for 
    Kenyan e-commerce product discovery.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cse_id: Optional[str] = None,
        cache_manager: Optional[CacheManager] = None,
        metrics: Optional[MetricsCollector] = None
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY_ALT")
        self.cse_id = cse_id or os.getenv("GOOGLE_CSE_ID")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.settings = Settings()
        
        # Project integrations
        self.cache = cache_manager or CacheManager()
        self.metrics = metrics or MetricsCollector()
        
        # Rate limiting
        self._last_request_time: Optional[float] = None
        self._min_request_interval = 0.1  # 100ms between requests
        
        # Validation
        if not self.api_key or not self.cse_id:
            raise ConfigurationError(
                "Google API credentials not configured. "
                "Set GOOGLE_API_KEY_ALT and GOOGLE_CSE_ID environment variables."
            )
        
        # Compile regex patterns for performance
        self._price_patterns = {
            'KES': re.compile(r'KSh[\s]*([0-9,]+(?:\.[0-9]{2})?)', re.IGNORECASE),
            'USD': re.compile(r'\$[\s]*([0-9,]+(?:\.[0-9]{2})?)'),
            'EUR': re.compile(r'€[\s]*([0-9,]+(?:\.[0-9]{2})?)'),
        }
        
        logger.info("google_shopping_client_initialized", cse_id=self.cse_id[:8] + "...")

    def _rate_limit(self):
        """Simple rate limiting to avoid API quota exhaustion"""
        if self._last_request_time:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_request_interval:
                time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, "warning"),
        reraise=True
    )
    async def search_products_async(
        self, 
        query: str, 
        max_results: int = 10,
        location: str = "ke",
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        use_cache: bool = True
    ) -> List[ProductResult]:
        """
        Async product search with caching and filtering.
        
        Args:
            query: Product search term
            max_results: Maximum results to return (1-10)
            location: Country code for localization
            price_min: Filter results above this price
            price_max: Filter results below this price
            use_cache: Whether to use cached results
        """
        cache_key = f"google_shopping:{query}:{location}:{max_results}"
        
        # Check cache
        if use_cache:
            cached = await self.cache.get(cache_key)
            if cached:
                self.metrics.increment("google_shopping.cache_hit")
                logger.debug("cache_hit", query=query)
                return [ProductResult(**item) for item in cached]
        
        self._rate_limit()
        
        params = {
            'key': self.api_key,
            'cx': self.cse_id,
            'q': self._build_query(query),
            'num': min(max(max_results, 1), 10),
            'gl': location,
            'hl': 'en',
            'safe': 'active',
            'sort': 'date'  # Prioritize recent listings
        }
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Metrics
                latency = time.time() - start_time
                self.metrics.histogram("google_shopping.latency", latency)
                self.metrics.increment("google_shopping.requests_success")
                
        except httpx.HTTPStatusError as e:
            self.metrics.increment("google_shopping.requests_failed")
            if e.response.status_code == 429:
                logger.error("rate_limit_exceeded", query=query)
                raise ExternalServiceError("Google API rate limit exceeded")
            elif e.response.status_code == 403:
                logger.error("invalid_credentials")
                raise ConfigurationError("Invalid Google API credentials")
            raise
        
        products = self._parse_results(data)
        
        # Apply price filters
        if price_min is not None:
            products = [p for p in products if p.price >= price_min]
        if price_max is not None:
            products = [p for p in products if p.price <= price_max]
        
        # Cache results
        if use_cache:
            await self.cache.set(
                cache_key, 
                [p.to_dict() for p in products], 
                ttl=3600  # 1 hour cache
            )
        
        logger.info(
            "search_completed", 
            query=query, 
            results_found=len(products),
            latency=latency
        )
        
        return products

    def search_products(
        self, 
        query: str, 
        **kwargs
    ) -> List[ProductResult]:
        """Synchronous wrapper for async search"""
        return asyncio.run(self.search_products_async(query, **kwargs))

    def _build_query(self, query: str) -> str:
        """Enhance query for better product discovery in Kenya"""
        # Remove existing price terms to avoid duplication
        clean_query = re.sub(r'price|buy|Kenya', '', query, flags=re.IGNORECASE).strip()
        return f"{clean_query} price buy Kenya site:.co.ke OR site:.com"

    def _parse_results(self, data: Dict) -> List[ProductResult]:
        """Enhanced parsing with rich metadata extraction"""
        products = []
        items = data.get('items', [])
        
        for item in items:
            try:
                product = self._parse_single_item(item)
                if product.price > 0:  # Only include items with valid prices
                    products.append(product)
            except Exception as e:
                logger.warning("parse_item_failed", error=str(e), item_title=item.get('title'))
                continue
        
        return products

    def _parse_single_item(self, item: Dict) -> ProductResult:
        """Parse individual search result into ProductResult"""
        snippet = item.get('snippet', '')
        title = item.get('title', 'Unknown')
        
        # Extract price and currency
        price, currency = self._extract_price(snippet) or self._extract_price(title) or (0.0, "KES")
        
        # Extract rating if available
        rating = self._extract_rating(snippet)
        
        # Parse structured data if available
        pagemap = item.get('pagemap', {})
        offer = pagemap.get('offer', [{}])[0]
        product_data = pagemap.get('product', [{}])[0]
        
        return ProductResult(
            platform='Google',
            seller=item.get('displayLink', 'Unknown').replace('www.', ''),
            product_name=title.replace(' - ', ' | ').split(' | ')[0][:200],  # Clean title
            price=price,
            currency=currency,
            url=item.get('link', ''),
            image_url=self._extract_image(pagemap),
            rating=rating or product_data.get('rating'),
            review_count=self._extract_review_count(snippet),
            raw_data=item
        )

    def _extract_price(self, text: str) -> Optional[tuple[float, str]]:
        """Extract price and currency from text"""
        if not text:
            return None
            
        for currency_code, pattern in self._price_patterns.items():
            match = pattern.search(text)
            if match:
                try:
                    price_str = match.group(1).replace(',', '')
                    return (float(price_str), currency_code)
                except ValueError:
                    continue
        return None

    def _extract_rating(self, text: str) -> Optional[float]:
        """Extract product rating from text"""
        patterns = [
            r'(\d+\.?\d*)\s*out of\s*5',
            r'(\d+\.?\d*)\s*stars?',
            r'Rating:\s*(\d+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None

    def _extract_review_count(self, text: str) -> Optional[int]:
        """Extract number of reviews"""
        match = re.search(r'(\d+)\s+reviews?', text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except ValueError:
                pass
        return None

    def _extract_image(self, pagemap: Dict) -> Optional[str]:
        """Extract image URL from structured data"""
        cse_image = pagemap.get('cse_image', [{}])[0]
        if cse_image:
            return cse_image.get('src')
        
        # Fallback to other image sources
        for key in ['image', 'thumbnail']:
            if key in pagemap:
                img_data = pagemap[key]
                if isinstance(img_data, list) and img_data:
                    return img_data[0].get('src') or img_data[0].get('url')
                elif isinstance(img_data, dict):
                    return img_data.get('src') or img_data.get('url')
        return None

    def get_quota_status(self) -> Dict[str, Any]:
        """Check remaining API quota (approximate)"""
        # Note: Google doesn't provide real-time quota in responses
        # This is a placeholder for your own quota tracking implementation
        return {
            'daily_limit': 100,  # Free tier
            'used_today': self.metrics.get_counter("google_shopping.requests_success"),
            'reset_time': "00:00 UTC"
        }


# Convenience function with project-specific defaults
@lru_cache(maxsize=1)
def get_shopping_client() -> GoogleShoppingClient:
    """Singleton client instance for the project"""
    return GoogleShoppingClient()


async def fetch_google_products(
    query: str,
    max_results: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    Project-standard interface for Google Shopping searches.
    
    Returns list of product dictionaries matching project schema.
    """
    client = get_shopping_client()
    
    try:
        results = await client.search_products_async(
            query=query,
            max_results=max_results,
            price_min=min_price,
            price_max=max_price,
            use_cache=not force_refresh
        )
        return [r.to_dict() for r in results]
    except ExternalServiceError:
        # Return empty list on service failure to maintain API contract
        logger.error("fetch_failed_returning_empty", query=query)
        return []
    except Exception as e:
        logger.exception("unexpected_error", query=query, error=str(e))
        return []


# Backwards compatibility
def fetch_google_products_sync(*args, **kwargs) -> List[Dict[str, Any]]:
    """Synchronous version for legacy code"""
    return asyncio.run(fetch_google_products(*args, **kwargs))