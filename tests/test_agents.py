def test_import():
    from agents.market_agent import MarketIntelligenceAgent
    assert MarketIntelligenceAgent is not None

def test_price_agent():
    from agents.price_agent import PriceStrategistAgent
    agent = PriceStrategistAgent()
    assert agent is not None
