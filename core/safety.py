"""
Safety and security guardrails for the procurement system.
Includes input validation, output filtering, and content safety.
"""
import re
from typing import Any, Dict, List, Optional
from core.logging import get_logger

logger = get_logger("safety")


class SafetyGuardrails:
    """Comprehensive safety checks for the system."""
    
    # Patterns that might indicate injection attacks
    DANGEROUS_PATTERNS = [
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'eval\s*\(',
        r'document\.cookie',
        r'window\.location',
        r'select\s+.*\s+from',
        r'drop\s+table',
        r'insert\s+into',
        r'delete\s+from',
    ]
    
    # Sensitive data patterns to redact
    SENSITIVE_PATTERNS = {
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'phone_number': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    }
    
    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """Remove potentially dangerous content from input."""
        if not isinstance(text, str):
            return text
            
        sanitized = text
        for pattern in cls.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, sanitized, re.IGNORECASE)
            if matches:
                logger.log_safety_trigger("injection_attempt", f"Pattern: {pattern}")
                sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        # Limit length
        if len(sanitized) > 10000:
            logger.log_safety_trigger("input_too_long", f"Length: {len(sanitized)}")
            sanitized = sanitized[:10000]
        
        return sanitized.strip()
    
    @classmethod
    def redact_sensitive_data(cls, text: str) -> str:
        """Redact sensitive information from logs/outputs."""
        if not isinstance(text, str):
            return text
            
        redacted = text
        for data_type, pattern in cls.SENSITIVE_PATTERNS.items():
            redacted = re.sub(pattern, f'[{data_type.upper()}_REDACTED]', redacted)
        return redacted
    
    @classmethod
    def validate_price(cls, price: float, max_price: float = 10000000) -> bool:
        """Validate price is within reasonable bounds."""
        if not isinstance(price, (int, float)):
            return False
        if price <= 0 or price > max_price:
            logger.log_safety_trigger("invalid_price", f"Price: {price}")
            return False
        return True


class OutputFilter:
    """Filter and validate agent outputs."""
    
    @staticmethod
    def filter_recommendation(recommendation: Dict) -> Dict:
        """Ensure recommendation meets safety standards."""
        safe_fields = {
            'product_name', 'best_option', 'alternatives', 
            'price_forecast', 'compliance_summary', 'final_recommendation',
            'confidence_score', 'human_approval_required'
        }
        
        filtered = {k: v for k, v in recommendation.items() if k in safe_fields}
        
        if 'confidence_score' not in filtered:
            filtered['confidence_score'] = 0.5
        
        if filtered.get('confidence_score', 1.0) < 0.6:
            filtered['human_approval_required'] = True
            filtered['approval_reason'] = "Low confidence score"
        
        return filtered
