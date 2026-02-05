import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time
import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Callable
from functools import wraps
import random
import asyncio
from core.logging import get_logger

logger = get_logger('universal_scraper')

@dataclass
class Product:
    """Standardized product data structure"""
    platform: str
    name: str
    price: float
    currency: str
    url: str
    seller: str
    image_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None
    availability: str = "In Stock"
    scraped_at: datetime = None
    
    def __post_init__(self):
        if self.scraped_at is None:
            self.scraped_at = datetime.now()
        if self.discount_percent is None and self.original_price and self.price:
            self.discount_percent = round(((self.original_price - self.price) / self.original_price) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class RateLimiter:
    """Token bucket rate limiter for respectful scraping"""
    def __init__(self, max_requests: int = 10, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests = []
        self._lock = False
    
    def acquire(self):
        now = time.time()
        self.requests = [req for req in self.requests if now - req < self.window]
        
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window - (now - self.requests[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit hit, sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.requests.append(now)
    
    def __enter__(self):
        self.acquire()
        return self
    
    def __exit__(self, *args):
        pass

class CacheManager:
    """Enhanced cache manager with compression and TTL"""
    def __init__(self, cache_dir: str = 'cache', default_ttl: int = 10):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        self._ensure_dir()
        self._cleanup_expired()
    
    def _ensure_dir(self):
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_key(self, query: str, platform: str) -> str:
        return hashlib.sha256(f'{platform}:{query.lower().strip()}'.encode()).hexdigest()[:16]
    
    def _get_filepath(self, key: str) -> str:
        return os.path.join(self.cache_dir, f'{key}.json')
    
    def get(self, query: str, platform: str, max_age_minutes: Optional[int] = None) -> Optional[List[Dict]]:
        if max_age_minutes is None:
            max_age_minutes = self.default_ttl
            
        key = self._get_cache_key(query, platform)
        filepath = self._get_filepath(key)
        
        try:
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cached_time = datetime.fromisoformat(data['timestamp'])
            age = datetime.now() - cached_time
            
            if age > timedelta(minutes=max_age_minutes):
                logger.debug(f'Cache expired for {platform}:{query}')
                return None
            
            logger.info(f'✅ Cache hit for {platform}:{query} (age: {age.seconds//60}m)')
            return data['results']
            
        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.warning(f'Cache read error: {e}')
            return None
    
    def set(self, query: str, platform: str, results: List[Dict]):
        key = self._get_cache_key(query, platform)
        filepath = self._get_filepath(key)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'results': results,
                    'platform': platform,
                    'query': query
                }, f, indent=2, default=str)
            logger.debug(f'Cache saved: {platform}:{query}')
        except IOError as e:
            logger.error(f'Cache write error: {e}')
    
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
                    if datetime.now() - cached_time > timedelta(hours=24):
                        os.remove(filepath)
                        logger.debug(f'Cleaned expired cache: {filename}')
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f'Cache cleanup error: {e}')
    
    def clear(self):
        """Clear all cache"""
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, filename))
        logger.info('Cache cleared')

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, TimeoutError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f'Max retries ({max_retries}) exceeded for {func.__name__}: {e}')
                        raise
                    
                    logger.warning(f'Attempt {retries} failed for {func.__name__}, retrying in {current_delay}s...')
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return None
        return wrapper
    return decorator

class UniversalEcommerceScraper:
    """Enterprise-grade multi-platform e-commerce scraper"""
    
    PLATFORM_CONFIG = {
        'jumia': {
            'base_url': 'https://www.jumia.co.ke',
            'search_path': '/catalog/',
            'currency': 'KES',
            'selectors': {
                'container': 'article.prd',
                'name': 'h3.name',
                'price': 'div.prc',
                'link': 'a.core',
                'image': 'img.img',
                'rating': 'div.stars',
                'original_price': 'div.old'
            }
        },
        'kilimall': {
            'base_url': 'https://www.kilimall.co.ke',
            'search_path': '/search',
            'currency': 'KES',
            'selectors': {
                'container': 'div.product-item',
                'name': 'h2.product-title',
                'price': 'span.current-price',
                'link': 'a.product-link',
                'image': 'img.product-img',
                'original_price': 'span.original-price'
            }
        },
        'amazon': {
            'base_url': 'https://www.amazon.com',
            'search_path': '/s',
            'currency': 'USD',
            'headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br'
            }
        }
    }
    
    def __init__(self, respect_robots: bool = True, delay_range: tuple = (1, 3)):
        self.ua = UserAgent(fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.session = requests.Session()
        self.cache = CacheManager()
        self.rate_limiter = RateLimiter(max_requests=20, window=60)
        self.respect_robots = respect_robots
        self.delay_range = delay_range
        self._setup_session()
        
    def _setup_session(self):
        """Configure session with rotating headers"""
        self.session.headers.update({
            'User-Agent': self.ua.random,
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
        })
    
    def _rotate_user_agent(self):
        """Rotate User-Agent to avoid detection"""
        self.session.headers['User-Agent'] = self.ua.random
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Robust price parsing with multiple formats"""
        if not price_text:
            return None
        
        # Remove common currency symbols and whitespace
        cleaned = re.sub(r'[KSh$€£\s,]', '', price_text.strip())
        
        # Extract numeric value
        match = re.search(r'[\d,]+\.?\d*', cleaned)
        if match:
            try:
                return float(match.group().replace(',', ''))
            except ValueError:
                pass
        return None
    
    def _extract_rating(self, rating_text: str) -> Optional[float]:
        """Extract numeric rating from text"""
        if not rating_text:
            return None
        match = re.search(r'(\d+(\.\d+)?)', rating_text)
        return float(match.group(1)) if match else None
    
    @retry_on_failure(max_retries=3, delay=1.0)
    def _fetch_page(self, url: str, platform: str) -> Optional[BeautifulSoup]:
        """Fetch and parse page with error handling"""
        with self.rate_limiter:
            try:
                config = self.PLATFORM_CONFIG.get(platform, {})
                headers = {**self.session.headers, **config.get('headers', {})}
                
                response = self.session.get(
                    url, 
                    headers=headers, 
                    timeout=15,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Random delay between requests
                time.sleep(random.uniform(*self.delay_range))
                
                return BeautifulSoup(response.content, 'lxml')
                
            except requests.RequestException as e:
                logger.error(f'Fetch error for {platform}: {e}')
                return None
    
    def search_jumia(self, query: str, max_results: int = 10) -> List[Product]:
        """Enhanced Jumia scraper with more data points"""
        cached = self.cache.get(query, 'jumia')
        if cached:
            return [Product(**p) for p in cached]
        
        logger.info(f'🔍 Searching Jumia for: {query}')
        products = []
        
        try:
            url = f"{self.PLATFORM_CONFIG['jumia']['base_url']}/catalog/?q={quote_plus(query)}"
            soup = self._fetch_page(url, 'jumia')
            
            if not soup:
                return products
            
            selectors = self.PLATFORM_CONFIG['jumia']['selectors']
            items = soup.find_all('article', class_='prd', limit=max_results)
            
            for item in items:
                try:
                    # Name
                    name_elem = item.find('h3', class_='name')
                    name = name_elem.text.strip() if name_elem else 'N/A'
                    
                    # Current price
                    price_elem = item.find('div', class_='prc')
                    price = self._parse_price(price_elem.text) if price_elem else 0.0
                    
                    # Original price (for discount calculation)
                    old_price_elem = item.find('div', class_='old')
                    original_price = self._parse_price(old_price_elem.text) if old_price_elem else None
                    
                    # Link
                    link_elem = item.find('a', class_='core')
                    link = urljoin(self.PLATFORM_CONFIG['jumia']['base_url'], link_elem['href']) if link_elem else ''
                    
                    # Image
                    img_elem = item.find('img', class_='img')
                    image_url = img_elem.get('data-src') or img_elem.get('src', '') if img_elem else None
                    
                    # Rating
                    rating_elem = item.find('div', class_='stars')
                    rating = self._extract_rating(rating_elem.text) if rating_elem else None
                    
                    # Reviews count
                    reviews_elem = item.find('div', class_='rev')
                    reviews_count = None
                    if reviews_elem:
                        match = re.search(r'\((\d+)\)', reviews_elem.text)
                        reviews_count = int(match.group(1)) if match else None
                    
                    if name and price > 0:
                        product = Product(
                            platform='Jumia',
                            name=name,
                            price=price,
                            currency='KES',
                            url=link,
                            seller='Jumia',
                            image_url=image_url,
                            rating=rating,
                            reviews_count=reviews_count,
                            original_price=original_price
                        )
                        products.append(product)
                        
                except Exception as e:
                    logger.debug(f'Parse error for item: {e}')
                    continue
            
            # Cache results
            self.cache.set(query, 'jumia', [p.to_dict() for p in products])
            logger.info(f'✅ Found {len(products)} products on Jumia')
            
        except Exception as e:
            logger.error(f'Jumia search error: {e}')
        
        return products
    
    def search_kilimall(self, query: str, max_results: int = 10) -> List[Product]:
        """Kilimall scraper implementation"""
        cached = self.cache.get(query, 'kilimall')
        if cached:
            return [Product(**p) for p in cached]
        
        logger.info(f'🔍 Searching Kilimall for: {query}')
        products = []
        
        try:
            url = f"{self.PLATFORM_CONFIG['kilimall']['base_url']}/search?q={quote_plus(query)}"
            soup = self._fetch_page(url, 'kilimall')
            
            if not soup:
                return products
            
            items = soup.find_all('div', class_='product-item', limit=max_results)
            
            for item in items:
                try:
                    name_elem = item.find('h2', class_='product-title')
                    name = name_elem.text.strip() if name_elem else 'N/A'
                    
                    price_elem = item.find('span', class_='current-price')
                    price = self._parse_price(price_elem.text) if price_elem else 0.0
                    
                    link_elem = item.find('a', class_='product-link')
                    link = urljoin(self.PLATFORM_CONFIG['kilimall']['base_url'], link_elem['href']) if link_elem else ''
                    
                    img_elem = item.find('img', class_='product-img')
                    image_url = img_elem.get('data-src') or img_elem.get('src', '') if img_elem else None
                    
                    if name and price > 0:
                        products.append(Product(
                            platform='Kilimall',
                            name=name,
                            price=price,
                            currency='KES',
                            url=link,
                            seller='Kilimall',
                            image_url=image_url
                        ))
                        
                except Exception as e:
                    logger.debug(f'Parse error: {e}')
                    continue
            
            self.cache.set(query, 'kilimall', [p.to_dict() for p in products])
            logger.info(f'✅ Found {len(products)} products on Kilimall')
            
        except Exception as e:
            logger.error(f'Kilimall search error: {e}')
        
        return products
    
    def search_amazon(self, query: str, max_results: int = 10) -> List[Product]:
        """Amazon scraper with async support - delegates to amazon_scraper module"""
        cached = self.cache.get(query, 'amazon')
        if cached:
            return [Product(**p) for p in cached]
        
        logger.info(f'🔍 Searching Amazon for: {query}')
        
        try:
            # Import and use the dedicated Amazon scraper
            from tools.amazon_scraper import search_amazon_products
            
            # Run async function in a thread-safe way
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            amazon_results = loop.run_until_complete(
                search_amazon_products(query, region="US", max_results=max_results)
            )
            
            products = []
            for result in amazon_results:
                product = Product(
                    platform="Amazon",
                    name=result.get('product_name', 'Unknown'),
                    price=float(result.get('price', 0)),
                    currency=result.get('currency', 'USD'),
                    url=result.get('url', ''),
                    seller=result.get('seller', 'Amazon'),
                    image_url=result.get('image_url'),
                    rating=result.get('rating'),
                    reviews_count=result.get('review_count'),
                    availability=result.get('availability', 'In Stock')
                )
                products.append(product)
            
            # Cache results
            if products:
                self.cache.set(query, 'amazon', [p.to_dict() for p in products], ttl=3600)
            
            logger.info(f'✓ Found {len(products)} products on Amazon')
            return products
            
        except ImportError:
            logger.warning('amazon_scraper module not available, falling back to direct scraping')
            return self._search_amazon_fallback(query, max_results)
        except Exception as e:
            logger.error(f'Amazon search failed: {str(e)}')
            return self._search_amazon_fallback(query, max_results)
    
    def _search_amazon_fallback(self, query: str, max_results: int = 10) -> List[Product]:
        """Fallback Amazon scraper using BeautifulSoup"""
        products = []
        
        try:
            # Use different TLD or parameters to avoid blocks
            url = f"https://www.amazon.com/s?k={quote_plus(query)}&ref=nb_sb_noss"
            
            # Additional headers for Amazon
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.amazon.com/'
            }
            
            with self.rate_limiter:
                response = self.session.get(url, headers=headers, timeout=20)
                
                if response.status_code == 503:
                    logger.warning('Amazon blocked request (503), returning empty')
                    return products
                
                soup = BeautifulSoup(response.content, 'lxml')
                
                # Try multiple selectors as Amazon changes frequently
                selectors = [
                    'div[data-component-type="s-search-result"]',
                    '.s-result-item',
                    '[data-component-type="s-search-result"]'
                ]
                
                items = []
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        break
                
                for item in items[:max_results]:
                    try:
                        # Multiple possible selectors for title
                        name_elem = (
                            item.select_one('h2 a span') or 
                            item.select_one('.s-size-mini span') or
                            item.select_one('h2 span')
                        )
                        name = name_elem.text.strip() if name_elem else 'N/A'
                        
                        # Price extraction
                        price_elem = (
                            item.select_one('.a-price-whole') or
                            item.select_one('.a-price .a-offscreen')
                        )
                        price_text = price_elem.text if price_elem else ''
                        price = self._parse_price(price_text)
                        
                        if not price:
                            continue
                        
                        # Link
                        link_elem = item.select_one('h2 a') or item.select_one('a.a-link-normal')
                        link = urljoin('https://amazon.com', link_elem['href']) if link_elem else ''
                        
                        # Image
                        img_elem = item.select_one('img.s-image')
                        image_url = img_elem['src'] if img_elem else None
                        
                        # Rating
                        rating_elem = item.select_one('.a-icon-alt')
                        rating = self._extract_rating(rating_elem.text) if rating_elem else None
                        
                        products.append(Product(
                            platform='Amazon',
                            name=name,
                            price=price,
                            currency='USD',
                            url=link,
                            seller='Amazon',
                            image_url=image_url,
                            rating=rating
                        ))
                        
                    except Exception as e:
                        continue
                
                self.cache.set(query, 'amazon', [p.to_dict() for p in products])
                logger.info(f'✅ Found {len(products)} products on Amazon')
                
        except Exception as e:
            logger.error(f'Amazon search error: {e}')
        
        return products
    
    def search_all(self, query: str, platforms: Optional[List[str]] = None, 
                   preference: str = 'cheapest', max_workers: int = 3) -> Dict[str, Any]:
        """
        Parallel search across multiple platforms with intelligent aggregation
        
        Args:
            query: Search term
            platforms: List of platforms to search (default: all available)
            preference: Sorting preference ('cheapest', 'expensive', 'rating', 'newest')
            max_workers: Max concurrent threads
        """
        if platforms is None:
            platforms = list(self.PLATFORM_CONFIG.keys())
        
        logger.info(f'🚀 Starting multi-platform search: {query} on {platforms}')
        start_time = time.time()
        
        all_products: List[Product] = []
        platform_stats = {}
        
        # Map platform names to methods
        search_methods = {
            'jumia': self.search_jumia,
            'kilimall': self.search_kilimall,
            'amazon': self.search_amazon
        }
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            
            for platform in platforms:
                if platform in search_methods:
                    future = executor.submit(search_methods[platform], query)
                    futures[future] = platform
            
            for future in as_completed(futures):
                platform = futures[future]
                try:
                    results = future.result(timeout=30)
                    all_products.extend(results)
                    platform_stats[platform] = {
                        'count': len(results),
                        'status': 'success'
                    }
                except TimeoutError:
                    logger.error(f'⏱️ Timeout for {platform}')
                    platform_stats[platform] = {'count': 0, 'status': 'timeout'}
                except Exception as e:
                    logger.error(f'❌ Error on {platform}: {e}')
                    platform_stats[platform] = {'count': 0, 'status': 'error', 'message': str(e)}
        
        # Sort based on preference
        sort_key = {
            'cheapest': lambda x: x.price,
            'expensive': lambda x: -x.price,
            'rating': lambda x: -(x.rating or 0),
            'newest': lambda x: x.scraped_at
        }.get(preference, lambda x: x.price)
        
        all_products.sort(key=sort_key)
        
        # Calculate statistics
        if all_products:
            prices = [p.price for p in all_products]
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            
            # Find best deals (significantly below average)
            threshold = avg_price * 0.8
            deals = [p for p in all_products if p.price <= threshold]
        else:
            avg_price = min_price = max_price = 0
            deals = []
        
        execution_time = time.time() - start_time
        
        return {
            'query': query,
            'platforms_searched': platforms,
            'platform_stats': platform_stats,
            'total_results': len(all_products),
            'execution_time': round(execution_time, 2),
            'price_stats': {
                'average': round(avg_price, 2),
                'minimum': round(min_price, 2),
                'maximum': round(max_price, 2)
            },
            'best_option': all_products[0].to_dict() if all_products else None,
            'top_deals': [p.to_dict() for p in deals[:5]],
            'all_results': [p.to_dict() for p in all_products],
            'timestamp': datetime.now().isoformat()
        }

def search_products(query: str, preference: str = 'cheapest', 
                   platforms: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convenience function for searching products
    
    Example:
        results = search_products("iphone 13", preference="cheapest", platforms=["jumia", "kilimall"])
    """
    scraper = UniversalEcommerceScraper()
    return scraper.search_all(query, platforms, preference)

# Advanced usage example
if __name__ == "__main__":
    # Example usage
    results = search_products(
        query="samsung galaxy s23",
        platforms=["jumia", "kilimall"],
        preference="cheapest"
    )
    
    print(f"Found {results['total_results']} products in {results['execution_time']}s")
    print(f"Best price: {results['best_option']['price']} {results['best_option']['currency']}")
    print(f"Platform breakdown: {results['platform_stats']}")
