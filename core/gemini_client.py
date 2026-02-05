"""
Google Gemini integration for the procurement system.
Handles all LLM interactions with retry logic and safety.
"""
import os
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
from core.logging import get_logger
from core.safety import SafetyGuardrails

logger = get_logger("gemini")


class GeminiClient:
    """Wrapper for Google Gemini API with resilience features."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        logger.info("Gemini client initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def generate(self, prompt: str, temperature: float = 0.3) -> str:
        """Generate text with retry logic."""
        try:
            safe_prompt = SafetyGuardrails.sanitize_input(prompt)
            
            response = self.model.generate_content(
                safe_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=2048,
                )
            )
            
            if response.text:
                logger.debug("Gemini generation successful")
                return response.text
            else:
                raise ValueError("Empty response from Gemini")
                
        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            raise
    
    def analyze_price_trend(self, price_history: List[Dict]) -> Dict[str, Any]:
        """Use Gemini to analyze price trends and provide insights."""
        prompt = f\"\"\"
        Analyze the following price history and provide insights:
        {price_history}
        
        Provide:
        1. Trend direction (up/down/stable)
        2. Confidence level (0-1)
        3. Recommendation (buy/wait/avoid)
        4. Expected price change in 7 days
        
        Return as JSON.
        \"\"\"
        
        try:
            response = self.generate(prompt, temperature=0.2)
            import json
            if "`json" in response:
                response = response.split("`json")[1].split("`")[0]
            return json.loads(response)
        except Exception as e:
            logger.error(f"Failed to parse price analysis: {e}")
            return {
                "trend": "stable",
                "confidence": 0.5,
                "recommendation": "wait",
                "expected_change": 0
            }
