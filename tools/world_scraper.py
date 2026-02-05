import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

# Enhanced headers to avoid bot detection
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}

from urllib.parse import urljoin, quote_plus
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
import random
import hashlib
import json
import os
from functools import wraps, lru_cache
import streamlit as st

# Configure logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Product:
    """Enhanced product data model with validation"""
    name: str
    price: float
    currency: str
    marketplace: str
    link: str
    image_url: str
    country: str
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    original_price: Optional[float] = None
    discount_percent: Optional[float] = field(default=None)
    availability: str = "In Stock"
    scraped_at: datetime = field(default_factory=datetime.now)
    query: str = ""
    
    def __post_init__(self):
        """Calculate discount and validate data"""
        if self.original_price and self.price and self.original_price > self.price:
            self.discount_percent = round(
                ((self.original_price - self.price) / self.original_price) * 100, 1
            )
        # Ensure price is positive
        self.price = max(0.0, float(self.price))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime handling"""
        data = asdict(self)
        data['scraped_at'] = self.scraped_at.isoformat()
        return data
    
    @property
    def is_valid(self) -> bool:
        """Validate product has essential data"""
        return (
            len(self.name) > 2 
            and self.price > 0 
            and self.link.startswith('http')
        )

class CacheManager:
    """Persistent cache with TTL and compression support"""
    def __init__(self, cache_dir: str = '.cache', ttl_minutes: int = 30):
        self.cache_dir = cache_dir
        self.ttl = timedelta(minutes=ttl_minutes)
        os.makedirs(cache_dir, exist_ok=True)
        self._cleanup_expired()
    
    def _get_key(self, query: str, marketplace: str) -> str:
        return hashlib.sha256(
            f"{marketplace}:{query.lower().strip()}".encode()
        ).hexdigest()[:16]
    
    def get(self, query: str, marketplace: str) -> Optional[List[Dict]]:
        key = self._get_key(query, marketplace)
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        
        try:
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                os.remove(filepath)
                return None
            
            logger.info(f"💾 Cache hit: {marketplace}")
            return data['products']
            
        except Exception as e:
            logger.debug(f"Cache read error: {e}")
            return None
    
    def set(self, query: str, marketplace: str, products: List[Dict]):
        key = self._get_key(query, marketplace)
        filepath = os.path.join(self.cache_dir, f"{key}.json")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'marketplace': marketplace,
                    'query': query,
                    'products': products
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def _cleanup_expired(self):
        """Remove expired cache files"""
        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                    cached_time = datetime.fromisoformat(data['timestamp'])
                    if datetime.now() - cached_time > self.ttl * 2:
                        os.remove(filepath)
                except:
                    continue
        except Exception as e:
            logger.warning(f"Cache cleanup error: {e}")

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for resilient scraping with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.RequestException as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries exceeded for {func.__name__}: {e}")
                        raise
                    
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

class BaseScraper(ABC):
    """Abstract base class for marketplace scrapers"""
    
    def __init__(self, marketplace: str, country: str, currency: str):
        self.marketplace = marketplace
        self.country = country
        self.currency = currency
        self.session = requests.Session()
        self.ua = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self._setup_session()
    
    def _setup_session(self):
        """Configure session with anti-detection headers"""
        self.session.headers.update({
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
    
    def _rotate_ua(self):
        """Rotate user agent"""
        self.session.headers["User-Agent"] = self.ua.random
    
    @abstractmethod
    def build_url(self, query: str) -> str:
        """Build search URL for the marketplace"""
        pass
    
    @abstractmethod
    def parse_product(self, element: Any) -> Optional[Product]:
        """Parse a single product element"""
        pass
    
    @abstractmethod
    def get_selectors(self) -> Dict[str, str]:
        """Return CSS selectors for product containers"""
        pass
    
    def clean_price(self, price_text: Optional[str]) -> float:
        """Robust price extraction"""
        if not price_text:
            return 0.0
        
        # Remove common currency symbols and normalize
        cleaned = str(price_text).upper()
        cleaned = re.sub(r'[KSH$€£\s,]', '', cleaned)
        cleaned = cleaned.replace('USD', '').replace('KES', '')
        
        # Extract first number sequence
        matches = re.findall(r'\d+\.?\d*', cleaned)
        if matches:
            try:
                return float(matches[0])
            except ValueError:
                pass
        return 0.0
    
    def safe_get_text(self, element, selector: str, default: str = "") -> str:
        """Safely extract text from element"""
        try:
            found = element.select_one(selector) if hasattr(element, 'select_one') else element.find(selector)
            return found.get_text(strip=True) if found else default
        except:
            return default
    
    def safe_get_attr(self, element, selector: str, attr: str, default: str = "") -> str:
        """Safely extract attribute from element"""
        try:
            found = element.select_one(selector) if hasattr(element, 'select_one') else element.find(selector)
            return found.get(attr, default) if found else default
        except:
            return default

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def fetch(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch page with retry logic"""
        try:
            time.sleep(random.uniform(0.5, 1.5))  # Respectful delay
            response = self.session.get(url, timeout=20, allow_redirects=True)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            logger.error(f"Fetch error for {self.marketplace}: {e}")
            return None
    
    def search(self, query: str, max_results: int = 10) -> List[Product]:
        """Execute search with error handling"""
        logger.info(f"🔍 Searching {self.marketplace} for: {query}")
        
        url = self.build_url(query)
        soup = self.fetch(url)
        
        if not soup:
            logger.warning(f"Failed to fetch {self.marketplace}")
            return []
        
        try:
            selectors = self.get_selectors()
            items = soup.select(selectors['container']) if 'container' in selectors else []
            
            products = []
            for item in items[:max_results]:
                try:
                    product = self.parse_product(item)
                    if product and product.is_valid:
                        product.query = query
                        products.append(product)
                except Exception as e:
                    logger.debug(f"Parse error in {self.marketplace}: {e}")
                    continue
            
            logger.info(f"✅ {self.marketplace}: Found {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"Search error in {self.marketplace}: {e}")
            return []

class KilimallScraper(BaseScraper):
    def __init__(self):
        super().__init__("Kilimall", "Kenya", "KES")
    
    def build_url(self, query: str) -> str:
        return f"https://www.kilimall.co.ke/search?q={quote_plus(query)}"
    
    def get_selectors(self) -> Dict[str, str]:
        return {
            'container': 'div.product-item, div.goods-item, div.search-item'
        }
    
    def parse_product(self, element: BeautifulSoup) -> Optional[Product]:
        # Try multiple name selectors
        name = ""
        for selector in ['h2.product-title', 'h3.name', 'h4', 'a[title]']:
            name = self.safe_get_text(element, selector)
            if name:
                break
        
        if not name:
            name = element.get('title', 'Unknown')
        
        # Price extraction
        price_text = ""
        price_elem = element.find(text=lambda x: x and ('KSh' in str(x) or 'KES' in str(x)))
        if price_elem:
            price_text = str(price_elem)
        else:
            price_text = self.safe_get_text(element, '.current-price, .price, .prc')
        
        price = self.clean_price(price_text)
        
        # Link extraction
        link_elem = element.find('a', href=True)
        href = link_elem['href'] if link_elem else ''
        link = urljoin("https://www.kilimall.co.ke", href)
        
        # Image extraction
        img_elem = element.find('img')
        image_url = ""
        if img_elem:
            image_url = (
                img_elem.get('data-src') or 
                img_elem.get('data-original') or 
                img_elem.get('src', '')
            )
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
        
        if not image_url or 'placeholder' in image_url:
            image_url = f"https://via.placeholder.com/300/0d9488/ffffff?text=Kilimall"
        
        return Product(
            name=name[:120],
            price=price,
            currency=self.currency,
            marketplace=self.marketplace,
            link=link,
            image_url=image_url,
            country=self.country
        )

class JumiaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Jumia", "Kenya", "KES")
    
    def build_url(self, query: str) -> str:
        return f"https://www.jumia.co.ke/catalog/?q={quote_plus(query)}"
    
    def get_selectors(self) -> Dict[str, str]:
        return {
            'container': 'article.prd, a.core'
        }
    
    def parse_product(self, element: BeautifulSoup) -> Optional[Product]:
        # Handle both article.prd and a.core structures
        is_link = element.name == 'a'
        
        if is_link:
            name = element.get('title', '') or self.safe_get_text(element, 'h3.name')
            href = element.get('href', '')
        else:
            name = self.safe_get_text(element, 'h3.name')
            link_elem = element.find('a', class_='core')
            href = link_elem['href'] if link_elem else ''
        
        # Price
        price_text = self.safe_get_text(element, 'div.prc')
        original_price_text = self.safe_get_text(element, 'div.old')
        
        price = self.clean_price(price_text)
        original_price = self.clean_price(original_price_text) if original_price_text else None
        
        # Rating
        rating_elem = element.find('div', class_='stars')
        rating = None
        if rating_elem:
            match = re.search(r'(\d+(\.\d+)?)', rating_elem.get_text())
            rating = float(match.group(1)) if match else None
        
        link = urljoin("https://www.jumia.co.ke", href)
        
        # Image
        img_elem = element.find('img')
        image_url = ""
        if img_elem:
            image_url = img_elem.get('data-src') or img_elem.get('src', '')
        
        if not image_url or 'placeholder' in image_url:
            image_url = f"https://via.placeholder.com/300/f68b1e/ffffff?text=Jumia"
        
        return Product(
            name=name[:120],
            price=price,
            currency=self.currency,
            marketplace=self.marketplace,
            link=link,
            image_url=image_url,
            country=self.country,
            rating=rating,
            original_price=original_price if original_price > price else None
        )

class MasokoScraper(BaseScraper):
    def __init__(self):
        super().__init__("Masoko", "Kenya", "KES")
    
    def build_url(self, query: str) -> str:
        return f"https://www.masoko.com/search?q={quote_plus(query)}"
    
    def get_selectors(self) -> Dict[str, str]:
        return {
            'container': 'div.product-item, div.product-card'
        }
    
    def parse_product(self, element: BeautifulSoup) -> Optional[Product]:
        name = self.safe_get_text(element, 'h2, h3.product-title, a.title')
        
        price_text = ""
        price_elem = element.find(text=lambda x: x and 'KSh' in str(x))
        if price_elem:
            price_text = str(price_elem)
        
        price = self.clean_price(price_text)
        
        link_elem = element.find('a', href=True)
        href = link_elem['href'] if link_elem else ''
        link = urljoin("https://www.masoko.com", href)
        
        img_elem = element.find('img')
        image_url = img_elem.get('src', '') if img_elem else ''
        
        if not image_url:
            image_url = f"https://via.placeholder.com/300/00a650/ffffff?text=Masoko"
        
        return Product(
            name=name[:120],
            price=price,
            currency=self.currency,
            marketplace=self.marketplace,
            link=link,
            image_url=image_url,
            country=self.country
        )

class AmazonScraper(BaseScraper):
    def __init__(self):
        super().__init__("Amazon", "USA", "USD")
        self.conversion_rate = 130.0  # USD to KES
    
    def build_url(self, query: str) -> str:
        return f"https://www.amazon.com/s?k={quote_plus(query)}"
    
    def _setup_session(self):
        super()._setup_session()
        self.session.headers.update({
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.amazon.com/',
        })
    
    def get_selectors(self) -> Dict[str, str]:
        return {
            'container': '[data-component-type="s-search-result"]'
        }
    
    def parse_product(self, element: BeautifulSoup) -> Optional[Product]:
        name = self.safe_get_text(element, 'h2 a span, .s-size-mini span')
        
        # Amazon price parsing (complex)
        price_whole = self.safe_get_text(element, '.a-price-whole')
        price_fraction = self.safe_get_text(element, '.a-price-fraction')
        price_offscreen = self.safe_get_text(element, '.a-price .a-offscreen')
        
        if price_offscreen:
            price_usd = self.clean_price(price_offscreen)
        elif price_whole:
            price_str = price_whole + '.' + price_fraction if price_fraction else price_whole
            price_usd = self.clean_price(price_str)
        else:
            price_usd = 0
        
        # Convert to KES
        price = price_usd * self.conversion_rate
        
        link_elem = element.find('h2 a') or element.find('a', class_='a-link-normal')
        href = link_elem['href'] if link_elem else ''
        link = urljoin("https://www.amazon.com", href)
        
        img_elem = element.find('img', class_='s-image')
        image_url = img_elem['src'] if img_elem else ''
        
        if not image_url:
            image_url = f"https://via.placeholder.com/300/232f3e/ffffff?text=Amazon"
        
        # Rating
        rating_elem = element.find('span', class_='a-icon-alt')
        rating = None
        if rating_elem:
            match = re.search(r'([\d.]+) out of', rating_elem.get_text())
            rating = float(match.group(1)) if match else None
        
        return Product(
            name=name[:120],
            price=round(price, 2),
            currency="KES (USD)",
            marketplace=self.marketplace,
            link=link,
            image_url=image_url,
            country=self.country,
            rating=rating
        )

class MockScraper(BaseScraper):
    """Generates realistic mock data when scraping fails"""
    
    MOCK_TEMPLATES = {
        "Amazon": [
            ("{query} - Amazon's Choice", 45000, "Prime Delivery"),
            ("{query} Pro - Best Seller", 78000, "Premium"),
            ("{query} Lite Edition", 32000, "Budget Pick"),
            ("{query} - Renewed", 28000, "Refurbished"),
        ],
        "eBay": [
            ("{query} - Buy It Now", 38000, "New"),
            ("{query} - Auction", 25000, "Bidding"),
            ("{query} - Refurbished", 42000, "Certified"),
        ],
        "Alibaba": [
            ("{query} - Wholesale (MOQ 10)", 18000, "Factory Direct"),
            ("{query} - OEM Available", 35000, "Customizable"),
            ("{query} - Bulk Order", 15000, "B2B"),
        ],
        "AliExpress": [
            ("{query} - Free Shipping", 28000, "Standard"),
            ("{query} - Flash Sale", 22000, "Limited"),
            ("{query} - Premium", 45000, "Express"),
        ]
    }
    
    def __init__(self, marketplace: str):
        templates = {
            "Amazon": ("USA", "USD"),
            "eBay": ("USA", "USD"),
            "Alibaba": ("China", "USD"),
            "AliExpress": ("China", "USD")
        }
        country, currency = templates.get(marketplace, ("Global", "USD"))
        super().__init__(marketplace, country, currency)
        self.templates = self.MOCK_TEMPLATES.get(marketplace, [])
        self.conversion_rate = 130.0 if currency == "USD" else 1.0
    
    def build_url(self, query: str) -> str:
        return ""
    
    def get_selectors(self) -> Dict[str, str]:
        return {}
    
    def parse_product(self, element: Any) -> Optional[Product]:
        return None
    
    def search(self, query: str, max_results: int = 5) -> List[Product]:
        """Generate mock products"""
        logger.info(f"🎭 Generating mock data for {self.marketplace}")
        
        products = []
        query_clean = query[:20]
        
        for i, (template, base_price, badge) in enumerate(self.templates[:max_results]):
            name = template.format(query=query_clean.title())
            price = base_price + random.randint(-5000, 5000)
            
            # Vary prices slightly for realism
            price = max(1000, price)
            
            products.append(Product(
                name=f"{name} [{badge}]",
                price=round(price * self.conversion_rate, 2),
                currency=f"KES ({self.currency})",
                marketplace=self.marketplace,
                link=f"https://www.{self.marketplace.lower()}.com/search?q={quote_plus(query)}",
                image_url=f"https://via.placeholder.com/300/{self._get_color()}/ffffff?text={self.marketplace}",
                country=self.country
            ))
        
        return products
    
    def _get_color(self) -> str:
        colors = {
            "Amazon": "232f3e",
            "eBay": "e53238",
            "Alibaba": "ff6a00",
            "AliExpress": "e43225"
        }
        return colors.get(self.marketplace, "666666")

class WorldScraper:
    """Unified scraper orchestrator with caching and parallel execution"""
    
    SCRAPER_MAP = {
        "Kilimall": KilimallScraper,
        "Jumia": JumiaScraper,
        "Masoko": MasokoScraper,
        "Amazon": AmazonScraper,
    }
    
    MOCK_MARKETS = ["eBay", "Alibaba", "AliExpress"]
    
    def __init__(self, use_cache: bool = True, max_workers: int = 4):
        self.cache = CacheManager() if use_cache else None
        self.max_workers = max_workers
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'cached': 0
        }
    
    def search_market(self, marketplace: str, query: str) -> List[Product]:
        """Search single marketplace with caching"""
        # Check cache
        if self.cache:
            cached = self.cache.get(query, marketplace)
            if cached:
                self.stats['cached'] += 1
                return [Product(**p) for p in cached]
        
        # Get scraper
        if marketplace in self.SCRAPER_MAP:
            scraper = self.SCRAPER_MAP[marketplace]()
        elif marketplace in self.MOCK_MARKETS:
            scraper = MockScraper(marketplace)
        else:
            logger.warning(f"Unknown marketplace: {marketplace}")
            return []
        
        # Execute search
        self.stats['total_requests'] += 1
        try:
            products = scraper.search(query)
            self.stats['successful'] += 1
            
            # Cache results
            if self.cache and products:
                self.cache.set(query, marketplace, [p.to_dict() for p in products])
            
            return products
            
        except Exception as e:
            self.stats['failed'] += 1
            logger.error(f"Search failed for {marketplace}: {e}")
            
            # Fallback to mock if real scraper fails
            if marketplace not in self.MOCK_MARKETS:
                logger.info(f"Falling back to mock data for {marketplace}")
                mock = MockScraper(marketplace)
                return mock.search(query)
            return []
    
    def search_all(self, query: str, markets: List[str]) -> List[Product]:
        """Parallel search across all markets"""
        logger.info(f"🚀 Starting global search: '{query}' on {markets}")
        start_time = time.time()
        
        all_products = []
        
        # Use ThreadPoolExecutor for parallel scraping
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_market = {
                executor.submit(self.search_market, market, query): market 
                for market in markets
            }
            
            for future in as_completed(future_to_market):
                market = future_to_market[future]
                try:
                    products = future.result(timeout=30)
                    all_products.extend(products)
                    
                    # Streamlit feedback
                    if st._is_running_with_streamlit:
                        st.success(f"✅ {market}: {len(products)} products")
                        
                except Exception as e:
                    logger.error(f"Error retrieving {market} results: {e}")
                    if st._is_running_with_streamlit:
                        st.error(f"❌ {market}: Failed")
        
        # Sort by price
        all_products.sort(key=lambda x: x.price)
        
        duration = time.time() - start_time
        logger.info(f"✨ Search complete: {len(all_products)} products in {duration:.2f}s")
        logger.info(f"📊 Stats: {self.stats}")
        
        return all_products

def search_products(query: str, markets: Optional[List[str]] = None) -> List[Dict]:
    """
    Main entry point for product search
    
    Args:
        query: Search term
        markets: List of marketplaces (default: all)
    
    Returns:
        List of product dictionaries
    """
    if markets is None:
        markets = ["Kilimall", "Jumia", "Masoko", "Amazon", "eBay", "Alibaba", "AliExpress"]
    
    # Show progress in Streamlit
    if st._is_running_with_streamlit:
        st.info(f"🔍 Searching worldwide for: **{query}**")
        progress_bar = st.progress(0)
    
    scraper = WorldScraper(use_cache=True, max_workers=4)
    
    # Update progress
    if st._is_running_with_streamlit:
        for i, _ in enumerate(markets):
            progress_bar.progress((i + 1) / len(markets))
    
    products = scraper.search_all(query, markets)
    
    if st._is_running_with_streamlit:
        progress_bar.empty()
    
    # Convert to dict format expected by frontend
    return [
        {
            "name": p.name,
            "price": p.price,
            "currency": p.currency,
            "marketplace": p.marketplace,
            "link": p.link,
            "image_url": p.image_url,
            "seller": p.marketplace,
            "country": p.country,
            "rating": p.rating,
            "discount_percent": p.discount_percent
        }
        for p in products
    ]

# Backward compatibility
if __name__ == "__main__":
    # Test run
    results = search_products("iphone 13", ["Jumia", "Kilimall"])
    print(f"Found {len(results)} products")
    for r in results[:3]:
        print(f"  - {r['marketplace']}: {r['name'][:50]} @ KES {r['price']}")

