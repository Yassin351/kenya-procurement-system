param([switch]$Unit, [switch]$Integration, [switch]$E2E, [switch]$All, [switch]$Coverage, [switch]$HTML)

$testPaths = @()
if ($Unit) { $testPaths += "tests/unit" }
if ($Integration) { $testPaths += "tests/integration" }
if ($E2E) { $testPaths += "tests/e2e" }
if ($All -or $testPaths.Count -eq 0) { $testPaths += "tests" }

$pytestArgs = @($testPaths) + @("-v")

if ($Coverage -or $HTML) {
    $pytestArgs += "--cov=core"
    $pytestArgs += "--cov-report=term-missing"
    if ($HTML) { $pytestArgs += "--cov-report=html" }
    $pytestArgs += "--cov-fail-under=70"
}

Write-Host "Running tests: $($testPaths -join ', ')" -ForegroundColor Green

# Use python -m pytest instead of pytest directly
python -m pytest @pytestArgs

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "`n✅ All tests passed!" -ForegroundColor Green
    if ($HTML) { Write-Host "📊 Coverage report: htmlcov/index.html" -ForegroundColor Cyan }
} else {
    Write-Host "`n❌ Tests failed with exit code $exitCode!" -ForegroundColor Red
    exit $exitCode
}
