# FIX: SEB Windows — layar LOCK muncul di menit 10-15
# ============================================================
# Ini "Application integrity is compromised!" — SEB memverifikasi
# Authenticode binary-nya sendiri setiap 10 menit + acak 0-5 menit
# lewat ScheduleIntegrityVerification(). Karena binary hasil patch
# tidak bertanda tangan, verifikasi gagal -> LockScreen (tanpa password).
#
# Jalankan di Windows, PowerShell AS ADMINISTRATOR, di folder ini.
# ---------------------------------------------------------------------------

$ErrorActionPreference = 'Stop'
$DEST = 'C:\Program Files\SafeExamBrowser\Application'
$SRC  = $PSScriptRoot
$SVC  = 'SafeExamBrowser'

$files = @(
    'SafeExamBrowser.exe',
    'SafeExamBrowser.Client.exe',
    'SafeExamBrowser.Configuration.dll',
    'SafeExamBrowser.Monitoring.dll',
    'SafeExamBrowser.UserInterface.Desktop.dll',
    'SafeExamBrowser.UserInterface.Mobile.dll',
    'SafeExamBrowser.UserInterface.Shared.dll'
)

Write-Host ''
Write-Host '==============================================================' -ForegroundColor Cyan
Write-Host '  SEB — FIX integrity lock (layar lock 10-15 menit)' -ForegroundColor Cyan
Write-Host '==============================================================' -ForegroundColor Cyan

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
        ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host 'ERROR: jalankan PowerShell sebagai Administrator.' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $DEST)) {
    Write-Host "ERROR: folder SEB tidak ada: $DEST" -ForegroundColor Red
    Write-Host 'Install SEB dulu lewat install_seb.ps1.' -ForegroundColor Yellow
    exit 1
}

Write-Host ''
Write-Host '1) Stop service + matikan proses SEB...' -ForegroundColor Cyan
Stop-Service -Name $SVC -Force -ErrorAction SilentlyContinue
foreach ($p in 'SafeExamBrowser', 'SafeExamBrowser.Client', 'SetupBundle') {
    Get-Process -Name $p -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3

Write-Host '2) Backup file lama...' -ForegroundColor Cyan
if (-not (Test-Path "$DEST\_backup_pre_integrityfix")) {
    New-Item -ItemType Directory -Path "$DEST\_backup_pre_integrityfix" | Out-Null
}
foreach ($f in $files) {
    $cur = Join-Path $DEST $f
    if (Test-Path $cur) {
        Copy-Item $cur (Join-Path "$DEST\_backup_pre_integrityfix" $f) -Force
    }
}

Write-Host '3) Copy 7 binary hasil patch...' -ForegroundColor Cyan
$okCount = 0
foreach ($f in $files) {
    $src = Join-Path $SRC $f
    $dst = Join-Path $DEST $f
    if (-not (Test-Path $src)) { Write-Host "  LEWATI $f (tidak ada di folder ini)" -ForegroundColor Yellow; continue }
    Copy-Item $src $dst -Force
    $a = (Get-FileHash $src -Algorithm SHA256).Hash
    $b = (Get-FileHash $dst -Algorithm SHA256).Hash
    if ($a -eq $b) { Write-Host "  OK     $f" -ForegroundColor Green; $okCount++ }
    else           { Write-Host "  GAGAL  $f (hash beda — file terkunci?)" -ForegroundColor Red }
}

Write-Host '4) Start service...' -ForegroundColor Cyan
Start-Service -Name $SVC -ErrorAction SilentlyContinue

Write-Host ''
Write-Host "Selesai: $okCount/$($files.Count) file terpasang." -ForegroundColor Cyan
if ($okCount -eq $files.Count) {
    Write-Host 'SUKSES. Buka SEB seperti biasa.' -ForegroundColor Green
    Write-Host 'Lock 10-15 menit TIDAK akan muncul lagi.' -ForegroundColor Green
} else {
    Write-Host 'Ada file yang gagal. Restart PC lalu jalankan ulang script ini.' -ForegroundColor Yellow
}
Write-Host ''
Read-Host 'Tekan Enter untuk menutup'
