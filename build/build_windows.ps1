# Build SEB Config Bypass Studio untuk Windows (.exe)
# Hasil: build\dist\SEB Config Bypass Studio.exe  (satu file, tanpa konsol)
#
# Jalankan di Windows:
#   powershell -ExecutionPolicy Bypass -File build_windows.ps1
#
# PENTING: PyInstaller TIDAK bisa cross-compile. .exe WAJIB dibangun
# di Windows (atau lewat GitHub Actions, lihat .github/workflows/build.yml).

$ErrorActionPreference = 'Stop'

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $Here
Set-Location $Here

Write-Host '==> SEB Config Bypass Studio - build Windows' -ForegroundColor Cyan
Write-Host ("    root : {0}" -f $Root)

# 1) cari python
$Py = $null
foreach ($c in 'py', 'python', 'python3') {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { $Py = $cmd.Source; break }
}
if (-not $Py) {
    Write-Host 'ERROR: Python tidak ditemukan. Install dari https://python.org' -ForegroundColor Red
    Write-Host '       (centang "Add python.exe to PATH" saat instalasi)' -ForegroundColor Yellow
    exit 1
}
Write-Host ("==> python: {0}" -f $Py)

# 2) venv + dependensi
$Venv = Join-Path $Here '.venv'
$VenvPy = Join-Path $Venv 'Scripts\python.exe'
if (-not (Test-Path $VenvPy)) {
    Write-Host '==> membuat venv...'
    & $Py -m venv $Venv
}
& $VenvPy -m pip install -q --upgrade pip
Write-Host '==> memasang pyinstaller + pillow...'
& $VenvPy -m pip install -q pyinstaller pillow

# 3) ikon
if (-not (Test-Path (Join-Path $Here 'assets\sebstudio.ico'))) {
    Write-Host '==> membuat ikon...'
    & $VenvPy (Join-Path $Here 'make_icon.py')
}

# 4) build
Write-Host '==> pyinstaller...'
Remove-Item -Recurse -Force (Join-Path $Here 'dist'), (Join-Path $Here 'build') -ErrorAction SilentlyContinue
& $VenvPy -m PyInstaller --clean --noconfirm (Join-Path $Here 'seb_bypass_gui.spec')

$Exe = Join-Path $Here 'dist\SEB Config Bypass Studio.exe'
if (-not (Test-Path $Exe)) {
    Write-Host 'ERROR: .exe tidak terbentuk.' -ForegroundColor Red
    exit 1
}

$mb = [math]::Round((Get-Item $Exe).Length / 1MB, 1)
Write-Host ''
Write-Host '==================================================' -ForegroundColor Green
Write-Host ' SELESAI' -ForegroundColor Green
Write-Host ("   .exe : {0}  ({1} MB)" -f $Exe, $mb) -ForegroundColor Green
Write-Host '==================================================' -ForegroundColor Green
Write-Host ''
Write-Host 'File .exe bisa dipindah ke PC mana pun (tidak butuh Python).'
Write-Host 'Windows SmartScreen mungkin memperingatkan karena belum'
Write-Host 'ditandatangani: More info -> Run anyway.'
