$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$pythonCandidates = @(
    (Join-Path $projectRoot ".venv\Scripts\python.exe"),
    (Join-Path $projectRoot "venv\Scripts\python.exe")
)
$pythonPath = $pythonCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1

if (-not $pythonPath) {
    Write-Host "未找到项目虚拟环境。请先在项目目录执行："
    Write-Host "  py -3.10 -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt"
    exit 1
}

Push-Location $projectRoot
$exitCode = 0
try {
    & $pythonPath -X utf8 (Join-Path $projectRoot "main.py") --check
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        & $pythonPath -X utf8 (Join-Path $projectRoot "app.py")
        $exitCode = $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
exit $exitCode
