from typing import Dict
from dataclasses import dataclass

@dataclass
class TaxConfig:
    vat_rate: float = 0.16
    import_duty_electronics: float = 0.25
    import_duty_general: float = 0.35
    railway_levy: float = 0.015
    idf_fee: float = 0.035

class KenyaTaxCalculator:
    def __init__(self):
        self.config = TaxConfig()
    
    def calculate_import_taxes(self, cif_value: float, category: str = "general", is_electronic: bool = False) -> Dict:
        duty_rate = self.config.import_duty_electronics if is_electronic else self.config.import_duty_general
        
        import_duty = cif_value * duty_rate
        railway_levy = cif_value * self.config.railway_levy
        idf_fee = cif_value * self.config.idf_fee
        
        vat_base = cif_value + import_duty + railway_levy + idf_fee
        vat = vat_base * self.config.vat_rate
        
        total_tax = import_duty + railway_levy + idf_fee + vat
        
        return {
            'cif_value': round(cif_value, 2),
            'import_duty': round(import_duty, 2),
            'railway_levy': round(railway_levy, 2),
            'idf_fee': round(idf_fee, 2),
            'vat': round(vat, 2),
            'total_tax': round(total_tax, 2),
            'total_landed_cost': round(cif_value + total_tax, 2)
        }

def calculate_tax(cif_value: float, category: str = "general") -> Dict:
    return KenyaTaxCalculator().calculate_import_taxes(cif_value, category)
