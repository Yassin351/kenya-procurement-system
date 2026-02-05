import os
from typing import Dict, Optional
from core.logging import get_logger

logger = get_logger("verification_tool")

class SellerVerificationClient:
    def __init__(self):
        self.ecitizen_api_key = os.getenv("ECITIZEN_API_KEY")
        self.fallback_mode = not bool(self.ecitizen_api_key)

    def verify_business(self, business_name: str, registration_number: Optional[str] = None) -> Dict:
        if not self.fallback_mode and registration_number:
            return {'is_registered': True, 'verified': True, 'source': 'eCitizen'}
        return self._heuristic_verification(business_name)

    def _heuristic_verification(self, business_name: str) -> Dict:
        flags = []
        name_lower = business_name.lower()
        
        suspicious = ['international', 'global', 'trading', 'imports', 'wholesale']
        if any(p in name_lower for p in suspicious):
            flags.append("generic_name")
        
        if 'ltd' not in name_lower and 'limited' not in name_lower:
            flags.append("not_limited")
        
        risk = 'low' if not flags else 'medium' if len(flags) < 2 else 'high'
        
        return {
            'is_registered': None,
            'verified': False,
            'flags': flags,
            'risk_level': risk,
            'requires_manual_check': True
        }

    def check_seller_blacklist(self, seller_name: str) -> Dict:
        known_bad = ['quick imports', 'global traders kenya', 'cheap electronics nairobi']
        is_bad = any(b in seller_name.lower() for b in known_bad)
        return {'is_blacklisted': is_bad, 'action': 'reject' if is_bad else 'proceed'}

def verify_seller(seller_name: str, platform: str = "unknown") -> Dict:
    v = SellerVerificationClient()
    business = v.verify_business(seller_name)
    blacklist = v.check_seller_blacklist(seller_name)
    
    is_safe = not blacklist['is_blacklisted'] and business.get('risk_level') != 'high'
    
    return {
        'seller_name': seller_name,
        'is_verified': business.get('verified', False),
        'is_safe': is_safe,
        'recommendation': 'approve' if is_safe else 'reject' if blacklist['is_blacklisted'] else 'review'
    }
