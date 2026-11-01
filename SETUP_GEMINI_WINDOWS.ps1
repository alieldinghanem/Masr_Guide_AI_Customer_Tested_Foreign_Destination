# Masr Guide AI - local Gemini setup. Never sends the API key to anyone other than Google.
# Run with SETUP_GEMINI_WINDOWS.bat. Requires Windows PowerShell 5.1+.
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$envPath = Join-Path $projectRoot 'backend\.env'
$examplePath = Join-Path $projectRoot 'backend\.env.example'

if (-not (Test-Path -LiteralPath $examplePath)) {
    Write-Host '[ERROR] backend/.env.example is missing.' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $examplePath -Destination $envPath
}

Write-Host ''
Write-Host 'MASR GUIDE AI - GEMINI SETUP' -ForegroundColor Cyan
Write-Host '1. Open https://aistudio.google.com/apikey'
Write-Host '2. Sign in to Google and create a free-tier API key if available.'
Write-Host '3. Paste the key at the hidden prompt below.'
Write-Host 'The key will be stored ONLY in backend/.env on this computer.'
Write-Host 'Do not share the key in chat, email or on GitHub.'
Write-Host ''

$secureKey = Read-Host -Prompt 'Gemini API key (hidden input)' -AsSecureString
$bstr = [IntPtr]::Zero
$key = $null
try {
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    $key = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    if ($bstr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

# Google AI Studio issues AIza... and AQ.... keys. This is only a format check.
$key = if ($null -ne $key) { $key.Trim() } else { $null }
if ([string]::IsNullOrWhiteSpace($key) -or $key -notmatch '^(?:AIza[A-Za-z0-9_-]{20,256}|AQ\.[A-Za-z0-9_-]{20,256})$') {
    Write-Host '[ERROR] The key is missing or has an unexpected format. No changes made.' -ForegroundColor Red
    exit 1
}

$lines = [System.IO.File]::ReadAllLines($envPath)
$out = New-Object System.Collections.Generic.List[string]
$foundKey = $false
$foundModel = $false
$foundSearch = $false
$foundProvider = $false
foreach ($line in $lines) {
    if ($line -match '^\s*GEMINI_API_KEY\s*=') {
        if (-not $foundKey) { $out.Add('GEMINI_API_KEY=' + $key); $foundKey = $true }
    } elseif ($line -match '^\s*GEMINI_MODEL\s*=') {
        if (-not $foundModel) { $out.Add('GEMINI_MODEL=gemini-2.5-flash'); $foundModel = $true }
    } elseif ($line -match '^\s*AI_PROVIDER\s*=') {
        if (-not $foundProvider) { $out.Add('AI_PROVIDER=gemini'); $foundProvider = $true }
    } elseif ($line -match '^\s*GEMINI_SEARCH_GROUNDING\s*=') {
        if (-not $foundSearch) { $out.Add('GEMINI_SEARCH_GROUNDING=true'); $foundSearch = $true }
    } else {
        $out.Add($line)
    }
}
if (-not $foundKey) { $out.Add('GEMINI_API_KEY=' + $key) }
if (-not $foundModel) { $out.Add('GEMINI_MODEL=gemini-2.5-flash') }
if (-not $foundSearch) { $out.Add('GEMINI_SEARCH_GROUNDING=true') }
if (-not $foundProvider) { $out.Add('AI_PROVIDER=gemini') }

# Write UTF-8 without BOM (works with python-dotenv).
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($envPath, ($out -join "`r`n") + "`r`n", $utf8NoBom)
Write-Host '[OK] Gemini key configured locally in backend/.env.' -ForegroundColor Green
Write-Host '[INFO] Checking real Gemini API connection...' -ForegroundColor Cyan

# Minimal, harmless live request; do not echo the key or the raw provider error.
$endpoint = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent'
$body = @{
    contents = @(@{ role = 'user'; parts = @(@{ text = 'Respond with the word OK only.' }) })
    generationConfig = @{ maxOutputTokens = 64 }
} | ConvertTo-Json -Depth 12 -Compress
$headers = @{ 'x-goog-api-key' = $key }
try {
    $response = Invoke-RestMethod -Uri $endpoint -Method Post -Headers $headers -ContentType 'application/json' -Body $body -TimeoutSec 35
    if ($null -eq $response.candidates -or $response.candidates.Count -lt 1) {
        Write-Host '[WARNING] Google responded, but no candidate was returned.' -ForegroundColor Yellow
        exit 2
    }
    Write-Host '[PASS] Gemini responded to a live API request.' -ForegroundColor Green
    Write-Host '[NEXT] Run TEST_GEMINI_SEARCH_GROUNDING_WINDOWS.bat to verify live Search citations.'
    Write-Host '[NEXT] Run RUN_STARTUP_WINDOWS.bat and visit http://localhost:5173'
    exit 0
} catch {
    Write-Host '[BLOCKED] Could not verify the live Gemini response.' -ForegroundColor Yellow
    Write-Host 'Check that the key has Gemini API access, free-tier quota, and network connectivity.'
    Write-Host 'The local trip planner still works without Gemini.'
    exit 2
} finally {
    Remove-Variable -Name key,headers -ErrorAction SilentlyContinue
}
