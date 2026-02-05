import os
import re
import time
import asyncio
import json
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
import logging
from functools import lru_cache
from urllib.parse import quote

# Try to import structlog, fallback to logging
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

# Try to use structlog if available, fallback to logging
if HAS_STRUCTLOG:
    logger = structlog.get_logger("amazon_scraper")
else:
    logger = logging.getLogger("amazon_scraper")
    logging.basicConfig(level=logging.INFO)


# Try to import project-specific modules, fallback to stubs if not available
try:
    from core.config import Settings
except:
    class Settings:
        pass

try:
    from core.exceptions import ExternalServiceError, ConfigurationError
except:
    class ExternalServiceError(Exception):
        pass
    class ConfigurationError(Exception):
        pass

try:
    from core.cache import CacheManager
except:
    class CacheManager:
        def get(self, key, namespace=None):
            return None
        def set(self, key, namespace, value, ttl=3600):
            pass

try:
    from core.monitoring import MetricsCollector
except:
    class MetricsCollector:
        def record_metric(self, name, value):
            pass


class AmazonRegion(Enum):
    """Supported Amazon regions"""
    US = "amazon.com"
    UK = "amazon.co.uk"
    DE = "amazon.de"
    FR = "amazon.fr"
    IN = "amazon.in"
    CA = "amazon.ca"


@dataclass
class AmazonProduct:
    """Amazon product data model"""
    platform: str = "Amazon"
    product_name: str = ""
    price: float = 0.0
    currency: str = "USD"
    url: str = ""
    asin: str = ""  # Amazon Standard Identification Number
    seller: str = "Amazon"
    image_url: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    in_stock: bool = True
    availability: str = "In Stock"
    timestamp: float = field(default_factory=time.time)
    raw_data: Dict[str, Any] = field(default_factory=dict, repr=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "platform": self.platform,
            "product_name": self.product_name,
            "price": self.price,
            "currency": self.currency,
            "url": self.url,
            "asin": self.asin,
            "seller": self.seller,
            "image_url": self.image_url,
            "rating": self.rating,
            "review_count": self.review_count,
            "in_stock": self.in_stock,
            "availability": self.availability,
            "timestamp": self.timestamp
        }


class AmazonScraper:
    """Amazon product scraper with API integration support"""
    
    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            },
            timeout=30.0,
            follow_redirects=True
        )
        self.settings = Settings()
        self.cache = CacheManager()
        self.metrics = MetricsCollector()
        self.base_urls = {
            AmazonRegion.US: "https://www.amazon.com",
            AmazonRegion.UK: "https://www.amazon.co.uk",
            AmazonRegion.IN: "https://www.amazon.in",
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARN)
    )
    async def _fetch_page(self, url: str) -> str:
        """Fetch page with retries"""
        try:
            response = await self.session.get(url)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            logger.error("request_error", url=url, error=str(e))
            raise ExternalServiceError(f"Failed to fetch {url}: {e}")
    
    def extract_price(self, price_str: str) -> Optional[float]:
        """Extract price from Amazon price string"""
        if not price_str:
            return None
        
        # Remove common currency symbols and extract number
        price_match = re.search(r'[\$£€₹]?\s?(\d+[.,]\d{2})', price_str)
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', ''))
                return price
            except ValueError:
                return None
        return None
    
    def extract_rating(self, rating_str: str) -> Optional[float]:
        """Extract rating from Amazon rating string"""
        if not rating_str:
            return None
        
        rating_match = re.search(r'(\d+\.?\d*)\s*out of 5', rating_str, re.IGNORECASE)
        if rating_match:
            try:
                return float(rating_match.group(1))
            except ValueError:
                return None
        return None
    
    def extract_review_count(self, review_str: str) -> Optional[int]:
        """Extract review count from string"""
        if not review_str:
            return None
        
        # Remove commas and extract number
        review_match = re.search(r'([\d,]+)', review_str)
        if review_match:
            try:
                return int(review_match.group(1).replace(',', ''))
            except ValueError:
                return None
        return None
    
    async def search_amazon(
        self,
        query: str,
        region: AmazonRegion = AmazonRegion.US,
        max_results: int = 10
    ) -> List[AmazonProduct]:
        """
        Search Amazon products (requires page parsing)
        Note: For production, consider using Amazon PA-API
        """
        try:
            cache_key = f"amazon_search_{query}_{region.value}"
            cached = self.cache.get(cache_key)
            if cached:
                logger.info("cache_hit", query=query)
                return cached
            
            base_url = self.base_urls.get(region, self.base_urls[AmazonRegion.US])
            search_url = f"{base_url}/s?k={quote(query)}"
            
            logger.info("searching_amazon", query=query, region=region.value)
            
            # Note: Direct HTML scraping is rate-limited
            # In production, use Amazon's Product Advertising API
            html = await self._fetch_page(search_url)
            
            products = await self._parse_search_results(html, region)
            
            # Limit results
            products = products[:max_results]
            
            # Cache for 1 hour
            self.cache.set(cache_key, products, ttl=3600)
            
            self.metrics.record_metric("amazon_search", len(products))
            
            return products
            
        except Exception as e:
            logger.error("search_failed", query=query, error=str(e))
            raise
    
    async def _parse_search_results(self, html: str, region: AmazonRegion) -> List[AmazonProduct]:
        """Parse Amazon search results from HTML"""
        products = []
        
        try:
            # Using regex patterns to extract data
            # This is a simplified parser; production code should use proper HTML parsing
            
            # Pattern for product data-component-type="s-search-result"
            product_pattern = r'<div[^>]*data-component-type="s-search-result"[^>]*>(.*?)</div>'
            products_html = re.findall(product_pattern, html, re.DOTALL)
            
            for product_html in products_html[:20]:  # Limit to 20
                try:
                    # Extract ASIN
                    asin_match = re.search(r'data-asin="([A-Z0-9]+)"', product_html)
                    asin = asin_match.group(1) if asin_match else ""
                    
                    # Extract product name
                    name_pattern = r'<h2[^>]*>.*?<a[^>]*>([^<]+)</a>'
                    name_match = re.search(name_pattern, product_html, re.DOTALL)
                    name = name_match.group(1).strip() if name_match else "Unknown"
                    
                    # Extract price
                    price_pattern = r'<span class="a-price-whole">([^<]+)</span>'
                    price_match = re.search(price_pattern, product_html)
                    price = self.extract_price(price_match.group(1)) if price_match else 0.0
                    
                    # Extract rating
                    rating_pattern = r'<span aria-label="([^"]*out of 5[^"]*)"'
                    rating_match = re.search(rating_pattern, product_html)
                    rating = self.extract_rating(rating_match.group(1)) if rating_match else None
                    
                    # Extract URL
                    url_pattern = r'<a[^>]*href="([^"]*)"[^>]*data-asin'
                    url_match = re.search(url_pattern, product_html)
                    url = url_match.group(1) if url_match else ""
                    if url and not url.startswith('http'):
                        base = self.base_urls.get(region, self.base_urls[AmazonRegion.US])
                        url = base + url
                    
                    product = AmazonProduct(
                        product_name=name,
                        price=price,
                        currency="USD" if region == AmazonRegion.US else "GBP" if region == AmazonRegion.UK else "INR",
                        url=url,
                        asin=asin,
                        rating=rating,
                        raw_data={"html_snippet": product_html[:500]}
                    )
                    
                    products.append(product)
                    
                except Exception as e:
                    logger.warning("parse_error", error=str(e))
                    continue
            
            return products
            
        except Exception as e:
            logger.error("parsing_failed", error=str(e))
            return []
    
    async def get_product_details(self, asin: str, region: AmazonRegion = AmazonRegion.US) -> Optional[AmazonProduct]:
        """Get detailed product information"""
        try:
            base_url = self.base_urls.get(region, self.base_urls[AmazonRegion.US])
            product_url = f"{base_url}/dp/{asin}"
            
            logger.info("fetching_details", asin=asin)
            
            html = await self._fetch_page(product_url)
            product = await self._parse_product_page(html, asin, region)
            
            return product
            
        except Exception as e:
            logger.error("details_fetch_failed", asin=asin, error=str(e))
            return None
    
    async def _parse_product_page(self, html: str, asin: str, region: AmazonRegion) -> Optional[AmazonProduct]:
        """Parse individual product page"""
        try:
            # Extract product title
            title_match = re.search(r'<h1[^>]*>.*?<span[^>]*>([^<]+)</span>', html)
            title = title_match.group(1).strip() if title_match else "Unknown"
            
            # Extract price
            price_pattern = r'<span class="a-price-whole">([^<]+)</span>'
            price_match = re.search(price_pattern, html)
            price = self.extract_price(price_match.group(1)) if price_match else 0.0
            
            # Extract rating
            rating_pattern = r'<span id="acrPopup"[^>]*title="([^"]*)"'
            rating_match = re.search(rating_pattern, html)
            rating = self.extract_rating(rating_match.group(1)) if rating_match else None
            
            # Extract review count
            review_pattern = r'<span id="acrCustomerReviewText"[^>]*>([^<]+)</span>'
            review_match = re.search(review_pattern, html)
            review_count = self.extract_review_count(review_match.group(1)) if review_match else None
            
            # Extract availability
            availability_pattern = r'<span[^>]*id="availability"[^>]*>([^<]+)</span>'
            availability_match = re.search(availability_pattern, html)
            availability = availability_match.group(1).strip() if availability_match else "Unknown"
            in_stock = "in stock" in availability.lower()
            
            # Extract image
            image_pattern = r'<img[^>]*id="landingImage"[^>]*src="([^"]+)"'
            image_match = re.search(image_pattern, html)
            image_url = image_match.group(1) if image_match else None
            
            base_url = self.base_urls.get(region, self.base_urls[AmazonRegion.US])
            product_url = f"{base_url}/dp/{asin}"
            
            product = AmazonProduct(
                product_name=title,
                price=price,
                currency="USD" if region == AmazonRegion.US else "GBP" if region == AmazonRegion.UK else "INR",
                url=product_url,
                asin=asin,
                rating=rating,
                review_count=review_count,
                availability=availability,
                in_stock=in_stock,
                image_url=image_url
            )
            
            return product
            
        except Exception as e:
            logger.error("product_parse_error", asin=asin, error=str(e))
            return None
    
    async def close(self):
        """Clean up resources"""
        await self.session.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience functions
async def search_amazon_products(
    query: str,
    region: str = "US",
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """Search Amazon products"""
    try:
        region_enum = AmazonRegion[region.upper()] if region.upper() in AmazonRegion.__members__ else AmazonRegion.US
        
        async with AmazonScraper() as scraper:
            products = await scraper.search_amazon(query, region_enum, max_results)
            return [p.to_dict() for p in products]
    except Exception as e:
        logger.error("search_error", query=query, error=str(e))
        return []


async def get_amazon_product(asin: str, region: str = "US") -> Optional[Dict[str, Any]]:
    """Get Amazon product details"""
    try:
        region_enum = AmazonRegion[region.upper()] if region.upper() in AmazonRegion.__members__ else AmazonRegion.US
        
        async with AmazonScraper() as scraper:
            product = await scraper.get_product_details(asin, region_enum)
            return product.to_dict() if product else None
    except Exception as e:
        logger.error("fetch_error", asin=asin, error=str(e))
        return None
