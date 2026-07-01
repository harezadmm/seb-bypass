$url = 'https://github.com/harezadmm/seb-bypass/raw/main/seb3.10.1_final_patch.zip'
$zip = "$env:TEMP\seb_patch.zip"
$tempFolder = "$env:TEMP\seb_patch_extracted"
$dest = "C:\Program Files\SafeExamBrowser\Application"

Write-Host "[1/3] Downloading patch from GitHub..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $url -OutFile $zip

Write-Host "[2/3] Extracting files..." -ForegroundColor Cyan
if (Test-Path $tempFolder) { Remove-Item $tempFolder -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $tempFolder -Force

Write-Host "[3/3] Installing files directly to SafeExamBrowser..." -ForegroundColor Green
Copy-Item "$tempFolder\SafeExamBrowser.exe"                       "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.Client.exe"                "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.Configuration.dll"         "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.Monitoring.dll"            "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.UserInterface.Desktop.dll" "$dest\" -Force
Copy-Item "$tempFolder\SafeExamBrowser.UserInterface.Mobile.dll"  "$dest\" -Force

# Clean up
Remove-Item $zip -Force
Remove-Item $tempFolder -Recurse -Force

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host " SUKSES! Patch SEB 3.10.1 berhasil terpasang!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " PENGATURAN JADWAL HAPUS CONFIGURATION OTOMATIS" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "Folder target: C:\Program Files\SafeExamBrowser\Configuration\"
Write-Host ""

$confirmSch = Read-Host "Apakah Anda ingin membuat jadwal pembersihan otomatis? (Y/N)"
if ($confirmSch -imatch '^y$') {
    Write-Host ""
    Write-Host "Pilih tipe penjadwalan:"
    Write-Host "[1] Harian (Daily)"
    Write-Host "[2] Mingguan (Weekly)"
    Write-Host "[3] Bulanan (Monthly)"
    Write-Host "[4] Satu Kali Saja (One-time Expiration)"
    Write-Host ""
    $schType = Read-Host "Masukkan pilihan (1-4)"
    
    $action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c rd /s /q "C:\Program Files\SafeExamBrowser\Configuration\"'
    
    if ($schType -eq '1') {
        $daysVal = Read-Host "Dijalankan setiap berapa hari sekali? (contoh: 1 untuk tiap hari)"
        $trigger = New-ScheduledTaskTrigger -Daily -At '12:00PM' -DaysInterval [int]$daysVal
        Register-ScheduledTask -TaskName 'SEB_AutoCleanup_Config' -Action $action -Trigger $trigger -RunLevel Highest -Force
        Write-Host "Penjadwalan harian berhasil dibuat!" -ForegroundColor Green
    }
    elseif ($schType -eq '2') {
        $weeksVal = Read-Host "Dijalankan setiap berapa minggu sekali? (contoh: 1 untuk tiap minggu)"
        $currentDay = (Get-Date).DayOfWeek
        $trigger = New-ScheduledTaskTrigger -Weekly -At '12:00PM' -DaysOfWeek $currentDay -WeeksInterval [int]$weeksVal
        Register-ScheduledTask -TaskName 'SEB_AutoCleanup_Config' -Action $action -Trigger $trigger -RunLevel Highest -Force
        Write-Host "Penjadwalan mingguan berhasil dibuat!" -ForegroundColor Green
    }
    elseif ($schType -eq '3') {
        $monthsVal = Read-Host "Dijalankan setiap berapa bulan sekali? (contoh: 1 untuk tiap bulan)"
        & schtasks.exe /Create /TN "SEB_AutoCleanup_Config" /TR "cmd.exe /c rd /s /q \"C:\Program Files\SafeExamBrowser\Configuration\\\"" /SC MONTHLY /MO $monthsVal /RL HIGHEST /F
        Write-Host "Penjadwalan bulanan berhasil dibuat!" -ForegroundColor Green
    }
    elseif ($schType -eq '4') {
        $expDays = Read-Host "Akan dihapus otomatis setelah berapa hari dari sekarang?"
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddDays([double]$expDays)
        Register-ScheduledTask -TaskName 'SEB_AutoCleanup_Config' -Action $action -Trigger $trigger -RunLevel Highest -Force
        Write-Host "Penjadwalan satu kali saja berhasil dibuat!" -ForegroundColor Green
    }
    else {
        Write-Host "Pilihan tidak valid." -ForegroundColor Yellow
    }
}

