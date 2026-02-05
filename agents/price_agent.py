import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from prophet import Prophet
from core.models import PricePoint, PriceForecast, SystemState

class PriceStrategistAgent:
    def run(self, state: SystemState) -> SystemState:
        if not state.market_data:
            state.errors.append("No market data")
            return state
        
        prices = [p.price_kes for p in state.market_data]
        current = np.mean(prices)
        
        # Simple forecast
        forecast = PriceForecast(
            current_price=round(current, 2),
            predicted_price_7d=round(current * 0.95, 2),
            predicted_price_30d=round(current * 0.90, 2),
            confidence_interval=(current * 0.9, current * 1.1),
            trend="down",
            recommendation="Wait for Friday deals",
            best_buy_date=datetime.now() + timedelta(days=(4 - datetime.now().weekday()) % 7),
            savings_potential=round(current * 0.12, 2)
        )
        
        state.price_analysis = forecast
        state.step = "price_analysis_complete"
        return state

def price_agent(state: dict) -> dict:
    from core.models import SystemState
    agent = PriceStrategistAgent()
    result = agent.run(SystemState(**state))
    return result.dict()
