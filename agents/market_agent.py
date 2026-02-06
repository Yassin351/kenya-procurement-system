from typing import List, Dict, Optional
from datetime import datetime
from core.logging import get_logger
from core.models import PricePoint, SystemState
from core.monitoring import get_system_monitor, CircuitBreaker, RateLimiter, TimeoutError
from tools.universal_scraper import search_products
from tenacity import retry, stop_after_attempt, wait_exponential

logger = get_logger('market_agent')
monitor = get_system_monitor()

# Circuit breaker for market data retrieval
market_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=60,
    expected_exception=Exception
)

# Rate limiter for API calls
market_rate_limiter = RateLimiter(max_calls=5, window_seconds=60)


class MarketIntelligenceAgent:
    """Agent for gathering market data with resilience."""
    
    def __init__(self):
        self.retry_count = 0
        self.max_retries = 3
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _search_with_retry(self, query: str, preference: str, platforms: List[str]) -> Dict:
        """Search for products with retry logic."""
        try:
            # Rate limiting
            if not market_rate_limiter.allow():
                logger.warning("Rate limit exceeded, waiting...")
                market_rate_limiter.wait_if_needed()
            
            logger.info(f"Searching markets: {query} on {platforms}")
            results = search_products(query, preference, platforms)
            return results
        except Exception as e:
            self.retry_count += 1
            monitor.record_retry(f"market_search_{query}", self.retry_count)
            logger.error(f"Market search failed (attempt {self.retry_count}): {str(e)}")
            raise
    
    def run(self, state: SystemState) -> SystemState:
        """Execute market intelligence gathering with error handling."""
        query = state.query
        preference = state.collected_data.get('preference', 'cheapest')
        platforms = state.collected_data.get('platforms', ['jumia'])
        start_time = datetime.now()
        
        try:
            # Try through circuit breaker
            results = market_circuit_breaker.call(
                self._search_with_retry,
                query,
                preference,
                platforms
            )
            
            price_points = []
            for item in results.get('all_results', []):
                try:
                    price_points.append(PricePoint(
                        platform=item.get('platform', 'Unknown'),
                        seller=item.get('seller', 'Unknown'),
                        price_kes=item.get('price', 0),
                        url=item.get('url'),
                        availability=item.get('availability', 'in_stock')
                    ))
                except Exception as item_error:
                    logger.warning(f"Failed to parse item: {item_error}")
                    state.errors.append(f"Parse error: {str(item_error)}")
                    continue
            
            state.market_data = price_points
            state.step = 'market_data_collected'
            
            # Record metrics
            response_time = (datetime.now() - start_time).total_seconds()
            monitor.record_request('market_search', response_time)
            logger.info(f"Market search completed: {len(price_points)} items in {response_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Market agent failure: {str(e)}")
            state.errors.append(f"Market search failed: {str(e)}")
            monitor.record_error('market_agent_failure', str(e))
            
            # Graceful fallback: return empty market data
            state.market_data = []
            state.step = 'market_data_collection_failed'
        
        return state


def market_agent(state: dict) -> dict:
    """LangGraph compatible market agent function."""
    from core.models import SystemState
    try:
        agent = MarketIntelligenceAgent()
        result = agent.run(SystemState(**state))
        return result.dict()
    except Exception as e:
        logger.critical(f"Market agent crashed: {e}")
        state['errors'] = state.get('errors', []) + [str(e)]
        state['market_data'] = []
        return state
