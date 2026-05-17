# COMETH Git Repository Setup
# Run after installing Git for Windows: https://git-scm.com/download/win
# Usage: powershell -ExecutionPolicy Bypass -File setup_git.ps1

$ErrorActionPreference = "Stop"
Write-Host "=== COMETH Git Setup ===" -ForegroundColor Cyan

# --- Config (EDIT THIS) ---
$GITHUB_REMOTE = "https://github.com/chenzhilei-lab/Atlas.git"

# --- 1. Init ---
Write-Host "[1/4] Initializing repository..." -ForegroundColor Yellow
git init
git branch -M main

# --- 2. Stage files ---
Write-Host "[2/4] Staging files..." -ForegroundColor Yellow
git add .

Write-Host "`n=== Files to be committed ===" -ForegroundColor Cyan
git status --short

$confirm = Read-Host "`nProceed with commit? (Y/n)"
if ($confirm -eq 'n' -or $confirm -eq 'N') {
    Write-Host "Aborted." -ForegroundColor Red
    exit
}

# --- 3. Commit ---
Write-Host "[3/4] Creating initial commit..." -ForegroundColor Yellow
git commit -m @'
Initial commit: COMETH paper + supplementary code

- main_methodology_v2.tex: methodology & benchmark paper
- main_application.tex: application to 2I/Borisov & 3I/ATLAS
- Atlas-supplementary/: Python source, notebooks, configs
- Figures, bibliography, AAS style files
'@

# --- 4. Remote ---
Write-Host "[4/4] Adding remote..." -ForegroundColor Yellow
$hasRemote = git remote
if ($hasRemote) {
    Write-Host "Remote already exists: $hasRemote" -ForegroundColor Green
} else {
    git remote add origin $GITHUB_REMOTE
    Write-Host "Remote added: $GITHUB_REMOTE" -ForegroundColor Green
    Write-Host "`nTo push, run: git push -u origin main" -ForegroundColor Cyan
}

Write-Host "`n=== Done! ===" -ForegroundColor Green
git log --oneline -1
