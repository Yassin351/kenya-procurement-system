from typing import Dict, List, Optional
from datetime import datetime
from core.logging import get_logger
from core.models import SystemState, ComplianceReport, SellerInfo, RiskLevel
from core.monitoring import get_system_monitor, CircuitBreaker, RateLimiter
from tools.verification_tool import verify_seller
from tenacity import retry, stop_after_attempt, wait_exponential

logger = get_logger('compliance_agent')
monitor = get_system_monitor()

# Circuit breaker for verification
verification_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=120,
    expected_exception=Exception
)

# Rate limiter to avoid overwhelming verification service
verification_rate_limiter = RateLimiter(max_calls=3, window_seconds=10)


class ComplianceAuditorAgent:
    """Agent for vendor compliance and verification with resilience."""
    
    def __init__(self):
        self.verification_cache = {}
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        reraise=True
    )
    def _verify_seller_with_retry(self, seller: str, platform: str) -> Dict:
        """Verify seller with retry logic and caching."""
        cache_key = f"{seller}:{platform}"
        
        if cache_key in self.verification_cache:
            logger.debug(f"Using cached verification for {cache_key}")
            return self.verification_cache[cache_key]
        
        # Rate limiting
        if not verification_rate_limiter.allow():
            logger.warning(f"Rate limit for verification, waiting...")
            verification_rate_limiter.wait_if_needed()
        
        try:
            logger.info(f"Verifying seller: {seller} on {platform}")
            verification = verify_seller(seller, platform)
            self.verification_cache[cache_key] = verification
            return verification
        except Exception as e:
            logger.warning(f"Verification failed for {cache_key}: {str(e)}")
            monitor.record_retry(f"verify_seller_{seller}", 1)
            raise
    
    def run(self, state: SystemState) -> SystemState:
        """Execute compliance checks with error handling."""
        start_time = datetime.now()
        
        try:
            if not state.market_data:
                logger.warning("No market data for compliance checks")
                state.errors.append("No market data for compliance checks")
                monitor.record_error('compliance_no_data', "Empty market data")
                return state
            
            results = {}
            sellers = {}
            verification_count = 0
            verification_failures = 0
            
            # De-duplicate sellers
            for item in state.market_data:
                key = f"{item.platform}:{item.seller}"
                if key not in sellers:
                    sellers[key] = item
            
            # Verify each unique seller
            for key, item in sellers.items():
                try:
                    # Try through circuit breaker
                    verification = verification_circuit_breaker.call(
                        self._verify_seller_with_retry,
                        item.seller,
                        item.platform
                    )
                    verification_count += 1
                    
                    seller_info = SellerInfo(
                        name=item.seller,
                        platform=item.platform,
                        is_verified=verification.get('is_verified', False),
                        risk_level=RiskLevel.LOW if verification.get('is_safe', False) else RiskLevel.HIGH
                    )
                    
                    results[key] = ComplianceReport(
                        seller=seller_info,
                        recommended=verification.get('is_safe', False),
                        warnings=verification.get('warnings', []) if not verification.get('is_safe') else []
                    )
                    
                except Exception as e:
                    verification_failures += 1
                    logger.error(f"Failed to verify {key}: {str(e)}")
                    monitor.record_error('seller_verification_failure', str(e))
                    
                    # Graceful fallback: mark as unverified but continue
                    seller_info = SellerInfo(
                        name=item.seller,
                        platform=item.platform,
                        is_verified=False,
                        risk_level=RiskLevel.MEDIUM
                    )
                    
                    results[key] = ComplianceReport(
                        seller=seller_info,
                        recommended=False,
                        warnings=[f"Verification failed: {str(e)[:50]}"]
                    )
            
            state.compliance_checks = results
            state.step = "compliance_check_complete"
            
            # Record metrics
            response_time = (datetime.now() - start_time).total_seconds()
            monitor.record_request('compliance_check', response_time)
            logger.info(
                f"Compliance check completed: {verification_count} verified, "
                f"{verification_failures} failures in {response_time:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"Compliance agent failure: {str(e)}")
            state.errors.append(f"Compliance check failed: {str(e)}")
            monitor.record_error('compliance_agent_failure', str(e))
            
            # Graceful fallback: return empty compliance checks
            state.compliance_checks = {}
        
        return state


def compliance_agent(state: dict) -> dict:
    """LangGraph compatible compliance agent function."""
    from core.models import SystemState
    try:
        agent = ComplianceAuditorAgent()
        result = agent.run(SystemState(**state))
        return result.dict()
    except Exception as e:
        logger.critical(f"Compliance agent crashed: {e}")
        state['errors'] = state.get('errors', []) + [str(e)]
        state['compliance_checks'] = {}
        return state
