import os
from typing import Dict, Optional
from datetime import datetime, timedelta
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

class CBKExchangeRateClient:
    FALLBACK_RATES = {'USD': 130.50, 'EUR': 142.00, 'GBP': 165.00}
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(hours=1)
        self.last_fetch = None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_rate(self, from_currency: str = "USD", to_currency: str = "KES") -> float:
        from_c = from_currency.upper()
        to_c = to_currency.upper()
        
        if self._is_cache_valid(from_c, to_c):
            return self.cache[f"{from_c}_{to_c}"]
        
        if to_c == "KES":
            rate = self._fetch_rate(from_c)
            if rate:
                self._update_cache(from_c, to_c, rate)
                return rate
        
        return self.FALLBACK_RATES.get(from_c, 130.50)
    
    def _fetch_rate(self, currency: str) -> Optional[float]:
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{currency}"
            response = requests.get(url, timeout=10)
            return response.json()['rates'].get('KES')
        except:
            return None
    
    def _is_cache_valid(self, from_c: str, to_c: str) -> bool:
        key = f"{from_c}_{to_c}"
        if key not in self.cache or not self.last_fetch:
            return False
        return datetime.now() - self.last_fetch < self.cache_duration
    
    def _update_cache(self, from_c: str, to_c: str, rate: float):
        self.cache[f"{from_c}_{to_c}"] = rate
        self.last_fetch = datetime.now()
    
    def convert(self, amount: float, from_c: str = "USD", to_c: str = "KES") -> Dict:
        rate = self.get_rate(from_c, to_c)
        return {
            'original_amount': amount,
            'converted_amount': round(amount * rate, 2),
            'exchange_rate': rate
        }

def usd_to_kes(amount: float) -> float:
    return CBKExchangeRateClient().convert(amount)['converted_amount']
