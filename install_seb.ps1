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

# Verifikasi Password (Hidden Input)
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "                  VERIFIKASI INSTALASI                    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
$securePassword = Read-Host -Prompt "Masukkan Kode Aktivasi/Password untuk melanjutkan" -AsSecureString
$inputPassword = [System.Net.NetworkCredential]::new("", $securePassword).Password
if ($inputPassword -ne "0821") {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host " ERROR: Kode Aktivasi/Password Salah! Instalasi Dibatalkan." -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host ""
    return
}
Write-Host "Kode terverifikasi. Memulai instalasi..." -ForegroundColor Green
Write-Host ""

# ──────────────────────────────────────────────────────────
# DETEKSI VERSI & INSTALASI SAFE EXAM BROWSER 3.10.1
# ──────────────────────────────────────────────────────────
$targetVersionPrefix = "3.10.1"
$registryPaths = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"
)

$sebApps = Get-ItemProperty $registryPaths -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*Safe Exam Browser*" }
$needsInstall = $true

if ($sebApps) {
    foreach ($app in $sebApps) {
        if ($app.DisplayVersion -and $app.DisplayVersion.StartsWith($targetVersionPrefix)) {
            $needsInstall = $false
            Write-Host "Mendeteksi Safe Exam Browser versi $($app.DisplayVersion) (Sudah sesuai 3.10.1)." -ForegroundColor Green
            break
        }
    }
}

if ($needsInstall) {
    if ($sebApps) {
        Write-Host "Safe Exam Browser versi lain terdeteksi. Memulai proses pembersihan/uninstall..." -ForegroundColor Yellow
        foreach ($app in $sebApps) {
            Write-Host "Menguninstall $($app.DisplayName) (Versi: $($app.DisplayVersion))..." -ForegroundColor Yellow
            $uninst = $app.UninstallString
            if ($uninst) {
                if ($uninst -match '^"(.*)"\s+(.*)$') {
                    $exe = $Matches[1]
                    $args = $Matches[2] + " /uninstall /quiet /norestart"
                    $p = Start-Process $exe -ArgumentList $args -Wait -PassThru -NoNewWindow
                } elseif ($uninst -match 'MsiExec.exe\s+/X(.*)') {
                    $guid = $Matches[1]
                    $p = Start-Process "MsiExec.exe" -ArgumentList "/X$guid /quiet /norestart" -Wait -PassThru -NoNewWindow
                } else {
                    $p = Start-Process cmd.exe -ArgumentList "/c $uninst /quiet /norestart" -Wait -PassThru -NoNewWindow
                }
            }
        }
        # Tunggu pelepasan file sistem selesai
        Start-Sleep -Seconds 5
    }

    # Download & Install Safe Exam Browser 3.10.1
    $fileId = "1Rl61ZOVOPIlhWM9G9Fr7ZDOmXXd2ykb7"
    $installerPath = "$env:TEMP\seb_3.10.1_setup.exe"
    if (Test-Path $installerPath) { Remove-Item $installerPath -Force }

    Write-Host "Mendownload Safe Exam Browser 3.10.1 dari Google Drive..." -ForegroundColor Cyan
    try {
        $confirmUrl = "https://docs.google.com/uc?export=download&id=$fileId"
        $cookieJar = New-Object System.Net.CookieContainer
        
        $request = [System.Net.HttpWebRequest]::Create($confirmUrl)
        $request.CookieContainer = $cookieJar
        $request.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        $response = $request.GetResponse()
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        $html = $reader.ReadToEnd()
        $reader.Close()
        $response.Close()

        $downloadUrl = $confirmUrl
        $action = "https://drive.usercontent.google.com/download"
        $confirm = ""
        $uuid = ""
        
        if ($html -match 'action="([^"]+)"') { $action = $Matches[1] }
        if ($html -match 'name="confirm" value="([^"]+)"') { $confirm = $Matches[1] }
        if ($html -match 'name="uuid" value="([^"]+)"') { $uuid = $Matches[1] }

        if ($confirm -and $uuid) {
            $downloadUrl = $action + "?id=" + $fileId + "&export=download&confirm=" + $confirm + "&uuid=" + $uuid
        } elseif ($confirm) {
            $downloadUrl = $action + "?id=" + $fileId + "&export=download&confirm=" + $confirm
        }

        $request2 = [System.Net.HttpWebRequest]::Create($downloadUrl)
        $request2.CookieContainer = $cookieJar
        $request2.UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        $request2.Timeout = 600000
        
        $response2 = $request2.GetResponse()
        $stream = $response2.GetResponseStream()
        $fileStream = [System.IO.File]::Create($installerPath)
        
        $buffer = New-Object byte[] 65536
        $totalRead = 0
        $lastReport = 0
        while ($true) {
            $read = $stream.Read($buffer, 0, $buffer.Length)
            if ($read -le 0) { break }
            $fileStream.Write($buffer, 0, $read)
            $totalRead += $read
            if ($totalRead - $lastReport -ge 20971520) {
                Write-Host "Mendownload: $([Math]::Round($totalRead / 1MB, 2)) MB..."
                $lastReport = $totalRead
            }
        }
        $fileStream.Close()
        $stream.Close()
        $response2.Close()

        Write-Host "Selesai mendownload. Menginstall Safe Exam Browser 3.10.1..." -ForegroundColor Green
        Write-Host "Proses instalasi sedang berjalan secara senyap (silent) di background, mohon tunggu..." -ForegroundColor Yellow
        
        $installProcess = Start-Process $installerPath -ArgumentList "/install", "/quiet", "/norestart" -Wait -PassThru -NoNewWindow
        
        # Verifikasi akhir
        $sebAppsCheck = Get-ItemProperty $registryPaths -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like "*Safe Exam Browser*" }
        $installedSuccessfully = $false
        if ($sebAppsCheck) {
            foreach ($app in $sebAppsCheck) {
                if ($app.DisplayVersion -and $app.DisplayVersion.StartsWith($targetVersionPrefix)) {
                    $installedSuccessfully = $true
                    break
                }
            }
        }

        if (-not $installedSuccessfully) {
            Write-Host "==========================================================" -ForegroundColor Red
            Write-Host " ERROR: Pemasangan Safe Exam Browser 3.10.1 GAGAL!" -ForegroundColor Red
            Write-Host "==========================================================" -ForegroundColor Red
            Write-Host "Silakan coba install secara manual." -ForegroundColor Yellow
            return
        }
        
        Write-Host "Safe Exam Browser 3.10.1 berhasil terpasang!" -ForegroundColor Green
        Remove-Item $installerPath -Force
    } catch {
        Write-Host "Gagal memproses download/install SEB 3.10.1 secara otomatis: $_" -ForegroundColor Red
        return
    }
}
Write-Host ""
Write-Host "Melanjutkan ke pemasangan patch bypass..." -ForegroundColor Green
Write-Host ""

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
Write-Host ""
Write-Host "Fitur & Perbaikan pada Patch ini:" -ForegroundColor Cyan
Write-Host "  [+] Bypass Deteksi VM (Virtual Machine)" -ForegroundColor Gray
Write-Host "  [+] Tampilan Fullscreen Normal (Tanpa/Cegah Minimize)" -ForegroundColor Gray
Write-Host "  [+] Screenshot/PrintScreen Diizinkan" -ForegroundColor Gray
Write-Host "  [+] Taskbar SEB Bagian Bawah Aktif & Muncul" -ForegroundColor Gray
Write-Host "  [+] Tombol Navigasi Browser (Chrome Style) Aktif" -ForegroundColor Gray
Write-Host "  [+] Tombol Power/Shutdown di Taskbar Aktif" -ForegroundColor Gray
Write-Host ""

