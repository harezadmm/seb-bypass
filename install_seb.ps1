# Pastikan dijalankan sebagai Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host " ERROR: PowerShell harus dijalankan sebagai Administrator! " -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host "Silakan klik kanan PowerShell -> 'Run as Administrator', lalu jalankan kembali." -ForegroundColor Yellow
    Write-Host ""
    return
}

$url = 'https://github.com/harezadmm/seb-bypass/raw/main/seb3.10.1_final_patch.zip?t=' + (Get-Date).Ticks
$zip = "$env:TEMP\seb_patch.zip"
$tempFolder = "$env:TEMP\seb_patch_extracted"
$dest = "C:\Program Files\SafeExamBrowser\Application"

Write-Host "[1/3] Downloading patch from GitHub..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $url -OutFile $zip

Write-Host "[2/3] Extracting files..." -ForegroundColor Cyan
if (Test-Path $tempFolder) { Remove-Item $tempFolder -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $tempFolder -Force

Write-Host "[3/3] Installing files directly to SafeExamBrowser..." -ForegroundColor Green
Write-Host "Stopping Safe Exam Browser Service..." -ForegroundColor Yellow
Stop-Service -Name "SafeExamBrowser" -Force -ErrorAction SilentlyContinue
Write-Host "Terminating any running Safe Exam Browser processes to unlock files..." -ForegroundColor Yellow
Stop-Process -Name "SafeExamBrowser" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "SafeExamBrowser.Client" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Copy-Item "$tempFolder\SafeExamBrowser.exe"                       "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.Client.exe"                "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.Configuration.dll"         "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.Monitoring.dll"            "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.UserInterface.Desktop.dll" "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.UserInterface.Mobile.dll"  "$dest\" -Force

Write-Host "Starting Safe Exam Browser Service..." -ForegroundColor Yellow
Start-Service -Name "SafeExamBrowser" -ErrorAction SilentlyContinue

# Clean up
Remove-Item $zip -Force
Remove-Item $tempFolder -Recurse -Force

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host " SUKSES! Patch SEB 3.10.1 berhasil terpasang!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

