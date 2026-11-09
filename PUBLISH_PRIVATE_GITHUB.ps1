# Run in PowerShell from the unzipped Masr_Guide_AI folder.
# Requires gh (GitHub CLI) and a login using: gh auth login
# Creates a PRIVATE repo only after the local validation commands succeed.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required.' }
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) { throw 'GitHub CLI (gh) is required. Install it from https://cli.github.com/.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js is required.' }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python is required.' }
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Please run gh auth login first.' }
if (-not (Test-Path 'backend/.venv/Scripts/python.exe')) {
  & python -m venv backend/.venv
  if ($LASTEXITCODE -ne 0) { throw 'Could not create Python virtual environment.' }
}
$py = Join-Path $PSScriptRoot 'backend/.venv/Scripts/python.exe'
& $py -m pip install -r backend/requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed. Nothing was published.' }
Push-Location backend
try {
  & $py -m pytest -q
  if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed. Nothing was published.' }
} finally { Pop-Location }
& $py scripts/qa_live_http.py
if ($LASTEXITCODE -ne 0) { throw 'HTTP QA failed. Nothing was published.' }
& $py scripts/qa_planner_stress.py
if ($LASTEXITCODE -ne 0) { throw 'Planner QA failed. Nothing was published.' }
Push-Location frontend
try {
  & npm ci --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) { throw 'npm ci failed. Nothing was published.' }
  & npm run lint
  if ($LASTEXITCODE -ne 0) { throw 'Frontend lint failed. Nothing was published.' }
  & npm test
  if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed. Nothing was published.' }
  & npm run build
  if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed. Nothing was published.' }
} finally { Pop-Location }
if (-not (Test-Path '.git')) { & git init -b main; if ($LASTEXITCODE -ne 0) { throw 'Git initialization failed.' } }
& git add .
if ($LASTEXITCODE -ne 0) { throw 'git add failed.' }
# Display the actual staged file list, so the user can inspect it before publishing.
$staged = @(& git diff --cached --name-only)
$secrets = @($staged | Where-Object { $_ -match '(^|/|\\)\.env($|\.)' -or $_ -match '\.(pem|p12|pfx|key)$' })
if ($secrets.Count -gt 0) { throw 'Sensitive credential files are staged. Nothing was published.' }
$staged | ForEach-Object { Write-Host $_ }
Write-Host 'Review the files above. This will create a PRIVATE GitHub repository.'
$confirm = Read-Host 'Enter YES to create and push the repository'
if ($confirm -cne 'YES') { Write-Host 'Canceled; no files uploaded.'; exit 0 }
& git commit -m 'Initial portfolio MVP — verified local checks'
if ($LASTEXITCODE -ne 0) { throw 'Git commit failed. Check git user.name and user.email.' }
& gh repo create masr-guide-ai --private --source . --remote origin --push
if ($LASTEXITCODE -ne 0) { throw 'GitHub repository creation/push failed. The local files are preserved.' }
Write-Host 'Private GitHub repository created. Review the GitHub Actions checks before making it public.'
