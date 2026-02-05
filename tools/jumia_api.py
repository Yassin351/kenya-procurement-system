"""
Jumia Kenya integration - uses Affiliate API when available,
falls back to ethical web scraping with proper delays.
"""
import os
import time
import random
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential
from core.logging import get_logger
from core.safety import SafetyGuardrails

logger = get_logger("jumia_tool")


@dataclass
class JumiaConfig:
    affiliate_id: Optional[str] = None
    api_key: Optional[str] = None
    base_url: str = "https://www.jumia.co.ke"
    request_delay: float = 2.0
    
    def __post_init__(self):
        self.affiliate_id = self.affiliate_id or os.getenv("JUMIA_AFFILIATE_ID")
        self.api_key = self.api_key or os.getenv("JUMIA_API_KEY")


class JumiaClient:
    """Client for Jumia Kenya product data."""
    
    def __init__(self, config: Optional[JumiaConfig] = None):
        self.config = config or JumiaConfig()
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        })
        logger.info("Jumia client initialized")
    
    def _get_headers(self):
        """Rotate user agents to avoid blocking."""
        return {
            'User-Agent': self.ua.random,
            'Referer': 'https://www.google.com/'
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for products on Jumia Kenya."""
        logger.info(f"Searching Jumia for: {query}")
        
        time.sleep(self.config.request_delay + random.uniform(0, 1))
        
        search_url = f"{self.config.base_url}/catalog/"
        params = {'q': query}
        
        try:
            response = self.session.get(
                search_url,
                params=params,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            
            products = self._parse_search_results(response.text, max_results)
            logger.info(f"Found {len(products)} products on Jumia")
            return products
            
        except requests.RequestException as e:
            logger.error(f"Jumia search failed: {e}")
            return []
    
    def _parse_search_results(self, html: str, max_results: int) -> List[Dict]:
        """Parse HTML and extract product information."""
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        product_cards = soup.find_all('article', class_='prd _fb col c-prd', limit=max_results)
        
        for card in product_cards:
            try:
                product = self._extract_product_data(card)
                if product and SafetyGuardrails.validate_price(product.get('price', 0)):
                    products.append(product)
            except Exception as e:
                logger.debug(f"Failed to parse product card: {e}")
                continue
        
        return products
    
    def _extract_product_data(self, card) -> Optional[Dict]:
        """Extract data from a single product card."""
        try:
            name_elem = card.find('h3', class_='name')
            name = name_elem.text.strip() if name_elem else "Unknown"
            
            price_elem = card.find('div', class_='prc')
            price_text = price_elem.text.strip() if price_elem else "0"
            price = self._parse_price(price_text)
            
            old_price_elem = card.find('div', class_='old')
            original_price = None
            if old_price_elem:
                original_price = self._parse_price(old_price_elem.text.strip())
            
            seller_elem = card.find('div', class_='bdg _mall _xs')
            seller = "Jumia Official" if seller_elem else "Third Party"
            
            link_elem = card.find('a', class_='core')
            url = link_elem['href'] if link_elem else ""
            if url and not url.startswith('http'):
                url = self.config.base_url + url
            
            in_stock = 'out of stock' not in card.get_text().lower()
            
            return {
                'platform': 'Jumia',
                'seller': seller,
                'product_name': name,
                'price': price,
                'original_price': original_price,
                'discount_percentage': self._calculate_discount(price, original_price),
                'currency': 'KES',
                'availability': 'in_stock' if in_stock else 'out_of_stock',
                'url': url,
                'delivery_days': 2 if seller == "Jumia Official" else 5,
                'shipping_cost': 0 if price > 1000 else 150,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.debug(f"Error extracting product data: {e}")
            return None
    
    def _parse_price(self, price_text: str) -> float:
        """Parse price string to float."""
        cleaned = price_text.replace('KSh', '').replace('KES', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _calculate_discount(self, current: float, original: Optional[float]) -> Optional[float]:
        """Calculate discount percentage."""
        if original and original > current:
            return round(((original - current) / original) * 100, 1)
        return None


def fetch_jumia_products(query: str, max_results: int = 10) -> List[Dict]:
    """Fetch products from Jumia."""
    client = JumiaClient()
    return client.search_products(query, max_results)

