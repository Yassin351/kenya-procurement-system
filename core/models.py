from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class ProductCategory(str, Enum):
    ELECTRONICS = 'electronics'
    FASHION = 'fashion'
    HOME = 'home'
    BEAUTY = 'beauty'
    GROCERIES = 'groceries'
    SEEDS = 'seeds'
    GENERAL = 'general'

class RiskLevel(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

class PricePoint(BaseModel):
    platform: str = 'Unknown'
    seller: str = 'Unknown'
    price_kes: float = 0.0
    price_usd: Optional[float] = None
    original_price: Optional[float] = None
    discount_percentage: Optional[float] = None
    availability: str = 'unknown'
    delivery_days: Optional[int] = None
    shipping_cost: float = 0.0
    url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    rating: Optional[float] = None

class SellerInfo(BaseModel):
    name: str = 'Unknown'
    platform: str = 'Unknown'
    registration_number: Optional[str] = None
    is_verified: bool = False
    rating: Optional[float] = None
    review_count: int = 0
    location: Optional[str] = None
    years_active: Optional[int] = None
    risk_flags: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW

class ComplianceReport(BaseModel):
    seller: SellerInfo = Field(default_factory=SellerInfo)
    is_registered: bool = False
    has_fake_reviews: bool = False
    counterfeit_risk: RiskLevel = RiskLevel.LOW
    return_policy_score: int = 0
    warranty_valid: bool = False
    recommended: bool = True
    warnings: List[str] = Field(default_factory=list)

class PriceForecast(BaseModel):
    current_price: float = 0.0
    predicted_price_7d: float = 0.0
    predicted_price_30d: float = 0.0
    confidence_interval: tuple = (0.0, 0.0)
    trend: str = 'stable'
    recommendation: str = 'Buy now'
    best_buy_date: Optional[datetime] = None
    savings_potential: Optional[float] = None

class TaxCalculation(BaseModel):
    cif_value: float = 0.0
    import_duty: float = 0.0
    excise_duty: float = 0.0
    vat: float = 0.0
    total_tax: float = 0.0
    total_landed_cost: float = 0.0
    breakdown: Dict[str, float] = Field(default_factory=dict)

class ProcurementRecommendation(BaseModel):
    product_name: str = 'Unknown'
    category: ProductCategory = ProductCategory.GENERAL
    best_option: PricePoint = Field(default_factory=PricePoint)
    alternatives: List[PricePoint] = Field(default_factory=list)
    price_forecast: PriceForecast = Field(default_factory=PriceForecast)
    compliance_summary: Dict[str, ComplianceReport] = Field(default_factory=dict)
    tax_implications: Optional[TaxCalculation] = None
    final_recommendation: str = 'No recommendation'
    confidence_score: float = 0.0
    generated_at: datetime = Field(default_factory=datetime.now)
    human_approval_required: bool = False
    approval_reason: Optional[str] = None

class SystemState(BaseModel):
    query: str = ''
    product_category: Optional[ProductCategory] = ProductCategory.GENERAL
    collected_data: Dict[str, Any] = Field(default_factory=dict)
    market_data: List[PricePoint] = Field(default_factory=list)
    price_analysis: PriceForecast = Field(default_factory=PriceForecast)
    compliance_checks: Dict[str, ComplianceReport] = Field(default_factory=dict)
    final_recommendation: ProcurementRecommendation = Field(default_factory=ProcurementRecommendation)
    errors: List[str] = Field(default_factory=list)
    retry_count: int = 0
    step: str = 'initialized'

class OCRResult(BaseModel):
    raw_text: str = ''
    extracted_products: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 0.0
    source_file: str = ''
    processed_at: datetime = Field(default_factory=datetime.now)
