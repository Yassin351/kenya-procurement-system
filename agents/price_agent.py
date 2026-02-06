import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List
from core.logging import get_logger
from core.models import PricePoint, PriceForecast, SystemState
from core.monitoring import get_system_monitor, CircuitBreaker
from tenacity import retry, stop_after_attempt, wait_exponential

logger = get_logger('price_agent')
monitor = get_system_monitor()

# Circuit breaker for forecasting
forecast_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=60,
    expected_exception=Exception
)


class PriceStrategistAgent:
    """Agent for price analysis and forecasting with resilience."""
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        reraise=True
    )
    def _generate_forecast(self, prices: List[float]) -> PriceForecast:
        """Generate price forecast with retry logic."""
        try:
            current = np.mean(prices)
            std_dev = np.std(prices) if len(prices) > 1 else 0
            
            # Calculate trend
            if len(prices) > 1:
                trend_direction = "down" if prices[-1] < np.mean(prices) else "up"
            else:
                trend_direction = "stable"
            
            # Calculate confidence
            confidence = max(0.5, 1.0 - (std_dev / current)) if current > 0 else 0.5
            
            forecast = PriceForecast(
                current_price=round(current, 2),
                predicted_price_7d=round(current * (0.95 if trend_direction == "down" else 1.05), 2),
                predicted_price_30d=round(current * (0.90 if trend_direction == "down" else 1.10), 2),
                confidence_interval=(current * 0.9, current * 1.1),
                trend=trend_direction,
                recommendation="Buy now" if trend_direction == "up" else "Wait for better deals",
                best_buy_date=datetime.now() + timedelta(days=3),
                savings_potential=round(max(prices) - min(prices), 2),
                confidence=round(confidence, 2)
            )
            
            logger.info(f"Forecast generated: {trend_direction} trend, {confidence:.0%} confidence")
            return forecast
        except Exception as e:
            logger.error(f"Forecast generation failed: {str(e)}")
            raise
    
    def run(self, state: SystemState) -> SystemState:
        """Execute price analysis with error handling."""
        start_time = datetime.now()
        
        try:
            if not state.market_data:
                logger.warning("No market data available for price analysis")
                state.errors.append("No market data for price analysis")
                monitor.record_error('price_analysis_no_data', "Empty market data")
                return state
            
            prices = [p.price_kes for p in state.market_data if p.price_kes > 0]
            
            if not prices:
                logger.error("No valid prices found")
                state.errors.append("No valid prices in market data")
                monitor.record_error('price_analysis_invalid_prices', "All prices are 0")
                
                # Graceful fallback: create minimal forecast
                state.price_analysis = PriceForecast(
                    current_price=0,
                    trend="unknown",
                    recommendation="Unable to analyze"
                )
                return state
            
            # Generate forecast with circuit breaker
            forecast = forecast_circuit_breaker.call(self._generate_forecast, prices)
            
            state.price_analysis = forecast
            state.step = "price_analysis_complete"
            
            # Record metrics
            response_time = (datetime.now() - start_time).total_seconds()
            monitor.record_request('price_analysis', response_time)
            logger.info(f"Price analysis completed in {response_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Price agent failure: {str(e)}")
            state.errors.append(f"Price analysis failed: {str(e)}")
            monitor.record_error('price_agent_failure', str(e))
            
            # Graceful fallback
            state.price_analysis = PriceForecast(
                current_price=0,
                trend="unknown",
                recommendation="Analysis unavailable"
            )
        
        return state


def price_agent(state: dict) -> dict:
    """LangGraph compatible price agent function."""
    from core.models import SystemState
    try:
        agent = PriceStrategistAgent()
        result = agent.run(SystemState(**state))
        return result.dict()
    except Exception as e:
        logger.critical(f"Price agent crashed: {e}")
        state['errors'] = state.get('errors', []) + [str(e)]
        state['price_analysis'] = {}
        return state
