def test_safety():
    from core.safety import SafetyGuardrails
    assert SafetyGuardrails.validate_price(1000) == True
    assert SafetyGuardrails.validate_price(-100) == False

def test_tax():
    from tools.tax_tool import calculate_tax
    result = calculate_tax(100000, 'electronics')
    assert result['total_tax'] > 0
