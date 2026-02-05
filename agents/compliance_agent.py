from typing import Dict, List
from core.models import SystemState, ComplianceReport, SellerInfo, RiskLevel
from tools.sentiment_tool import analyze_reviews
from tools.verification_tool import verify_seller

class ComplianceAuditorAgent:
    def run(self, state: SystemState) -> SystemState:
        if not state.market_data:
            state.errors.append("No market data")
            return state
        
        results = {}
        sellers = {}
        
        for item in state.market_data:
            key = f"{item.platform}:{item.seller}"
            sellers[key] = item
        
        for key, item in sellers.items():
            verification = verify_seller(item.seller, item.platform)
            
            seller_info = SellerInfo(
                name=item.seller,
                platform=item.platform,
                is_verified=verification['is_verified'],
                risk_level=RiskLevel.LOW if verification['is_safe'] else RiskLevel.HIGH
            )
            
            results[key] = ComplianceReport(
                seller=seller_info,
                recommended=verification['is_safe'],
                warnings=[] if verification['is_safe'] else ["Failed verification"]
            )
        
        state.compliance_checks = results
        state.step = "compliance_check_complete"
        return state

def compliance_agent(state: dict) -> dict:
    from core.models import SystemState
    agent = ComplianceAuditorAgent()
    result = agent.run(SystemState(**state))
    return result.dict()
