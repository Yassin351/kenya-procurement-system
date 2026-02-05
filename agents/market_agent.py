from typing import List, Dict
from core.logging import get_logger
from core.models import PricePoint, SystemState
from tools.universal_scraper import search_products

logger = get_logger('market_agent')

class MarketIntelligenceAgent:
    def run(self, state: SystemState) -> SystemState:
        query = state.query
        preference = state.collected_data.get('preference', 'cheapest')
        platforms = state.collected_data.get('platforms', ['jumia'])
        
        logger.info(f'Searching: {query}')
        results = search_products(query, preference, platforms)
        
        price_points = []
        for item in results.get('all_results', []):
            try:
                price_points.append(PricePoint(
                    platform=item.get('platform', 'Unknown'),
                    seller=item.get('seller', 'Unknown'),
                    price_kes=item.get('price', 0),
                    url=item.get('url'),
                    availability='in_stock'
                ))
            except:
                continue
        
        state.market_data = price_points
        state.step = 'market_data_collected'
        return state

def market_agent(state: dict) -> dict:
    from core.models import SystemState
    agent = MarketIntelligenceAgent()
    result = agent.run(SystemState(**state))
    return result.dict()
