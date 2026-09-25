#Requires -Version 5.1
<#
    ============================================================
     Safe Exam Browser 3.10.1 - Automated Windows Setup
    ============================================================
     Jalankan sebagai Administrator.

     Cepat:
       powershell -NoProfile -ExecutionPolicy Bypass -File .\install_seb.ps1

     Mode lain:
       -VerifyOnly          hanya cek status, tidak mengubah apapun
       -ForceReinstall      paksa install ulang meski versi sudah cocok
       -InstallerPath PATH  pakai file setup SEB yang sudah didownload manual
       -KeepInstaller       jangan hapus file setup setelah selesai

     Log: %TEMP%\seb_setup.log
    ============================================================
#>

[CmdletBinding()]
param(
    [string] $ActivationCode = '0821',
    [string] $LogPath        = "$env:TEMP\seb_setup.log",
    [string] $InstallerPath,
    [switch] $VerifyOnly,
    [switch] $ForceReinstall,
    [switch] $KeepInstaller
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

# TLS 1.2 wajib untuk GitHub/Google Drive di Windows lama (PS 5.1 default ke TLS 1.0)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls11

# ============================================================
# KONSTANTA
# ============================================================
$TARGET_VERSION     = '3.10.1'
$TARGET_VERSION_ALT = '3.10.1'
$SERVICE_NAME       = 'SafeExamBrowser'
# $env:ProgramFiles kosong di luar Windows; fallback ke path Windows standar supaya
# script tidak gagal bind saat dimuat (guard platform di bawah yang memberi pesan benar).
$DEST = if ($env:ProgramFiles) {
    Join-Path $env:ProgramFiles 'SafeExamBrowser\Application'
} else {
    'C:\Program Files\SafeExamBrowser\Application'
}
$DRIVE_FILE_ID      = '1Rl61ZOVOPIlhWM9G9Fr7ZDOmXXd2ykb7'
$PATCH_URL_BASE     = 'https://raw.githubusercontent.com/harezadmm/seb-bypass/main/seb3.10.1_final_patch.zip'
$PATCH_URL_FALLBACK = 'https://github.com/harezadmm/seb-bypass/raw/main/seb3.10.1_final_patch.zip'
$MIN_ZIP_BYTES      = 100KB
$MIN_EXE_BYTES      = 1MB

$PatchFiles = @(
    'SafeExamBrowser.exe'
    'SafeExamBrowser.Client.exe'
    'SafeExamBrowser.Configuration.dll'
    'SafeExamBrowser.Monitoring.dll'
    'SafeExamBrowser.UserInterface.Desktop.dll'
    'SafeExamBrowser.UserInterface.Mobile.dll'
)

$UninstallRoots = @(
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall'
    'HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall'
)

$script:Warnings = [System.Collections.Generic.List[string]]::new()

# ============================================================
# KONTEKS EKSEKUSI
# ============================================================
# Script ini normalnya dipanggil jarak jauh:  iex (irm ...)<url>...)
# Dalam mode itu perintah dijalankan DI DALAM window PowerShell milik user.
# `exit` di situ akan MENUTUP window, sehingga pesan sukses / pesan error
# hilang sebelum sempat dibaca. Guard di bawah mendeteksi mode tersebut dan
# mengganti exit dengan return + jeda, supaya hasil selalu terbaca.
# Dipanggil sebagai file (-File .\install_seb.ps1) -> perilaku exit dipertahankan.
$script:Standalone = $true
try {
    if ($MyInvocation.MyCommand.CommandType -eq 'ExternalScript') {
        $script:Standalone = $true
    } else {
        $script:Standalone = $false
    }
} catch {
    $script:Standalone = $true
}

# Sentinel yang dipakai Abort() untuk menghentikan eksekusi di mode iex.
$script:Aborted  = $false
$script:ExitCode = 0

# ============================================================
# LOGGING
# ============================================================
function Write-Log {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0)][AllowEmptyString()][string] $Message,
        [Parameter(Position = 1)][ValidateSet('INFO', 'OK', 'WARN', 'ERROR', 'STEP', 'HEAD')][string] $Level = 'INFO'
    )

    $stamp = Get-Date -Format 'HH:mm:ss'
    $line  = "[$stamp][$Level] $Message"

    $color = switch ($Level) {
        'OK'    { 'Green' }
        'WARN'  { 'Yellow' }
        'ERROR' { 'Red' }
        'STEP'  { 'Cyan' }
        'HEAD'  { 'Magenta' }
        default { 'Gray' }
    }

    Write-Host $line -ForegroundColor $color

    if ($Level -eq 'WARN')  { $script:Warnings.Add($Message) }
    if ($Level -eq 'ERROR') { $script:Warnings.Add($Message) }

    try {
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch { }
}

function Write-Banner {
    param([string]$Text, [string]$Color = 'Cyan')
    Write-Host ''
    Write-Host ('=' * 62) -ForegroundColor $Color
    Write-Host "  $Text" -ForegroundColor $Color
    Write-Host ('=' * 62) -ForegroundColor $Color
    Write-Host ''
}

function Fail {
    param([string]$Message, [int]$Code = 1)
    Write-Log $Message 'ERROR'
    Write-Host ''
    Write-Host '  Instalasi dihentikan. Lihat log: ' -NoNewline -ForegroundColor Yellow
    Write-Host $LogPath -ForegroundColor White
    Write-Host ''
    Abort -Code $Code
}

# Menahan window tetap terbuka di mode iex supaya hasil bisa dibaca.
# Read-Host dibungkus try supaya host tanpa stdin tidak ikut melempar error.
function Hold-Window {
    if ($script:Standalone) { return }
    try { Read-Host '  Tekan Enter untuk menutup.' | Out-Null } catch { }
}

# Menggantikan `exit` supaya window tidak tertutup saat dijalankan via iex (irm ...).
# Mode file (-File): exit dengan kode yang sama, perilaku lama dipertahankan.
# Mode iex: cetak pesan, tahan window, lalu lempar sentinel agar eksekusi benar-benar
# berhenti walau dipanggil dari dalam function.
function Abort {
    param([int]$Code = 0)
    $script:ExitCode = $Code
    $script:Aborted  = $true

    if ($script:Standalone) { exit $Code }

    Write-Host ''
    if ($Code -eq 0) {
        Write-Host '  Selesai. Window ini tetap terbuka agar hasil bisa dibaca.' -ForegroundColor Green
    } else {
        Write-Host "  Berhenti (kode $Code). Window ini tetap terbuka agar hasil bisa dibaca." -ForegroundColor Yellow
    }
    Hold-Window

    # Sentinel: menghentikan scriptblock yang sedang dieksekusi.
    # Ditangkap oleh catch teratas, yang mengenali $script:Aborted dan diam.
    throw [System.OperationCanceledException]::new('LTX_ABORT')
}

# ============================================================
# PRE-FLIGHT
# ============================================================
function Assert-Administrator {
    # Cek platform LEBIH DULU: di luar Windows, [WindowsIdentity]::GetCurrent()
    # melempar error identitas yang menyesatkan. Pesan yang benar adalah "ini Windows-only".
    if ($env:OS -ne 'Windows_NT' -and [System.Environment]::OSVersion.Platform -ne 'Win32NT') {
        Write-Host ''
        Write-Host ('=' * 62) -ForegroundColor Red
        Write-Host '  ERROR: script ini hanya untuk Windows.' -ForegroundColor Red
        Write-Host ('=' * 62) -ForegroundColor Red
        Write-Host ''
        Write-Host '  Host ini terdeteksi bukan Windows.' -ForegroundColor Yellow
        Write-Host ''
        Abort -Code 1
        return
    }

    $identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)

    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host ''
        Write-Host ('=' * 62) -ForegroundColor Red
        Write-Host '  ERROR: PowerShell belum dijalankan sebagai Administrator' -ForegroundColor Red
        Write-Host ('=' * 62) -ForegroundColor Red
        Write-Host ''
        Write-Host '  Tutup window ini, lalu:' -ForegroundColor Yellow
        Write-Host '    Klik kanan PowerShell  ->  "Run as Administrator"' -ForegroundColor White
        Write-Host '    Jalankan ulang perintah instalasi.' -ForegroundColor White
        Write-Host ''
        Abort -Code 1
        return
    }
}

function Confirm-Activation {
    if ($VerifyOnly) { return }

    Write-Host 'Masukkan Kode Aktivasi: ' -NoNewline -ForegroundColor Cyan
    $secure = Read-Host -AsSecureString
    $plain  = [System.Net.NetworkCredential]::new('', $secure).Password

    if ($plain -ne $ActivationCode) {
        Write-Host ''
        Write-Host ('=' * 62) -ForegroundColor Red
        Write-Host '  ERROR: Kode Aktivasi salah. Instalasi dibatalkan.' -ForegroundColor Red
        Write-Host ('=' * 62) -ForegroundColor Red
        Write-Host ''
        Abort -Code 1
        return
    }

    Write-Log 'Kode terverifikasi.' 'OK'
    Write-Host ''
}

# ============================================================
# REGISTRY SCAN
# ------------------------------------------------------------
# Memperbaiki bug asli: Get-ItemProperty dipanggil dengan ARRAY
# wildcard path. Satu subkey Uninstall yang rusak -> seluruh
# pipeline melempar InvalidCastException.
#
# Sekarang: setiap subkey dibaca satu per satu di dalam try/catch,
# sehingga key yang rusak hanya di-skip, bukan menggagalkan scan.
# ============================================================
function Get-InstalledSeb {
    [CmdletBinding()]
    param([string] $NamePattern = '*Safe Exam Browser*')

    $results = [System.Collections.Generic.List[object]]::new()

    foreach ($root in $UninstallRoots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }

        $keys = $null
        try {
            $keys = Get-ChildItem -LiteralPath $root -ErrorAction Stop
        } catch {
            Write-Log "  root registry tidak terbaca: $root" 'WARN'
            continue
        }

        foreach ($key in $keys) {
            try {
                $props = Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction Stop

                if ($null -ne $props.DisplayName -and $props.DisplayName -like $NamePattern) {
                    $results.Add([pscustomobject]@{
                        DisplayName     = $props.DisplayName
                        DisplayVersion  = $props.DisplayVersion
                        UninstallString = $props.UninstallString
                        KeyPath         = $key.PSPath
                        Is64Bit         = ($root -notlike '*Wow6432Node*')
                    })
                }
            } catch {
                # Subkey rusak / value bertipe aneh -> lewati, jangan gagalkan scan.
                Write-Log "  subkey dilewati ($($key.PSChildName)): $($_.Exception.Message)" 'WARN'
            }
        }
    }

    return $results
}

function Test-SebVersionMatches {
    param([AllowNull()][object[]] $Apps, [string] $Version)

    if (-not $Apps) { return $false }

    foreach ($app in $Apps) {
        if ([string]::IsNullOrWhiteSpace($app.DisplayVersion)) { continue }
        if ($app.DisplayVersion.StartsWith($Version, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

# ============================================================
# VALIDASI FILE
# ============================================================
function Test-PortableExecutable {
    param([string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) { return $false }

    $item = Get-Item -LiteralPath $Path
    if ($item.Length -lt $MIN_EXE_BYTES) {
        Write-Log ("  file terlalu kecil: {0:N0} bytes (min {1:N0})" -f $item.Length, $MIN_EXE_BYTES) 'WARN'
        return $false
    }

    $fs = [System.IO.File]::OpenRead($Path)
    try {
        $header = New-Object byte[] 2
        $read   = $fs.Read($header, 0, 2)
        if ($read -lt 2) { return $false }
        # 'MZ' = DOS/PE header
        return ($header[0] -eq 0x4D -and $header[1] -eq 0x5A)
    } finally {
        $fs.Close()
    }
}

function Test-ZipArchive {
    param([string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) { return $false }

    $item = Get-Item -LiteralPath $Path
    if ($item.Length -lt $MIN_ZIP_BYTES) {
        Write-Log ("  zip terlalu kecil: {0:N0} bytes" -f $item.Length) 'WARN'
        return $false
    }

    $fs = [System.IO.File]::OpenRead($Path)
    try {
        $header = New-Object byte[] 2
        $read   = $fs.Read($header, 0, 2)
        if ($read -lt 2) { return $false }
        # 'PK'
        return ($header[0] -eq 0x50 -and $header[1] -eq 0x4B)
    } finally {
        $fs.Close()
    }
}

function Test-FileUnlocked {
    param([string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) { return $true }

    try {
        $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        $fs.Close()
        return $true
    } catch {
        return $false
    }
}

# ============================================================
# DOWNLOAD
# ============================================================
function Save-RemoteFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $Uri,
        [Parameter(Mandatory)][string] $OutPath
    )

    $request = [System.Net.HttpWebRequest]::Create($Uri)
    $request.UserAgent         = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    $request.AllowAutoRedirect = $true
    $request.Timeout           = 900000
    $request.ReadWriteTimeout  = 900000

    $response = $request.GetResponse()
    try {
        $stream = $response.GetResponseStream()
        $out    = [System.IO.File]::Create($OutPath)
        try {
            $buffer  = New-Object byte[] 1048576
            $total   = [int64]0
            $nextLog = [int64](5MB)

            while (($n = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                $out.Write($buffer, 0, $n)
                $total += $n

                if ($total -ge $nextLog) {
                    Write-Log ("  terunduh {0:N1} MB" -f ($total / 1MB))
                    $nextLog += 5MB
                }
            }
        } finally {
            $out.Close()
        }

        return [int64]$total
    } finally {
        $response.Close()
    }
}

function Save-GoogleDriveFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $FileId,
        [Parameter(Mandatory)][string] $OutPath
    )

    if (Test-Path -LiteralPath $OutPath) { Remove-Item -LiteralPath $OutPath -Force }

    # --- Percobaan 1: alur confirm-token resmi (cookie harus dibawa antar request)
    try {
        $cookies = [System.Net.CookieContainer]::new()
        $confirmUrl = "https://drive.usercontent.google.com/download?id=$FileId&export=download"

        $req1 = [System.Net.HttpWebRequest]::Create($confirmUrl)
        $req1.CookieContainer = $cookies
        $req1.UserAgent       = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        $req1.Timeout         = 60000

        $html = ''
        $resp1 = $req1.GetResponse()
        try {
            $reader = [System.IO.StreamReader]::new($resp1.GetResponseStream())
            try   { $html = $reader.ReadToEnd() }
            finally { $reader.Close() }
        } finally {
            $resp1.Close()
        }

        $action  = 'https://drive.usercontent.google.com/download'
        $confirm = ''
        $uuid    = ''

        if ($html -match 'action="([^"]+)"')            { $action  = $Matches[1] }
        if ($html -match 'name="confirm"\s+value="([^"]+)"') { $confirm = $Matches[1] }
        if ($html -match 'name="uuid"\s+value="([^"]+)"')    { $uuid    = $Matches[1] }

        if ($confirm -and $uuid) {
            $dl = "$action`?id=$FileId&export=download&confirm=$confirm&uuid=$uuid"
        } elseif ($confirm) {
            $dl = "$action`?id=$FileId&export=download&confirm=$confirm"
        } else {
            $dl = $confirmUrl
        }

        $req2 = [System.Net.HttpWebRequest]::Create($dl)
        $req2.CookieContainer      = $cookies
        $req2.UserAgent            = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        $req2.AllowAutoRedirect    = $true
        $req2.Timeout              = 900000
        $req2.ReadWriteTimeout     = 900000

        $resp2   = $req2.GetResponse()
        $stream  = $resp2.GetResponseStream()
        $out     = [System.IO.File]::Create($OutPath)
        try {
            $buffer  = New-Object byte[] 1048576
            $total   = [int64]0
            $nextLog = [int64](10MB)

            while (($n = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                $out.Write($buffer, 0, $n)
                $total += $n
                if ($total -ge $nextLog) {
                    Write-Log ("  terunduh {0:N1} MB" -f ($total / 1MB))
                    $nextLog += 10MB
                }
            }
        } finally {
            $out.Close()
            $resp2.Close()
        }

        if (Test-PortableExecutable -Path $OutPath) {
            Write-Log ("  unduhan valid ({0:N1} MB)" -f ((Get-Item -LiteralPath $OutPath).Length / 1MB)) 'OK'
            return
        }

        Write-Log '  alur confirm-token menghasilkan file tidak valid, mencoba cara kedua...' 'WARN'
    } catch {
        Write-Log "  alur confirm-token gagal: $($_.Exception.Message)" 'WARN'
    }

    # --- Percobaan 2: direct confirm=t
    $directUrls = @(
        "https://drive.usercontent.google.com/download?id=$FileId&export=download&confirm=t"
        "https://drive.google.com/uc?export=download&id=$FileId&confirm=t"
    )

    foreach ($url in $directUrls) {
        try {
            if (Test-Path -LiteralPath $OutPath) { Remove-Item -LiteralPath $OutPath -Force }
            Write-Log "  mencoba: $url"
            [void](Save-RemoteFile -Uri $url -OutPath $OutPath)

            if (Test-PortableExecutable -Path $OutPath) {
                Write-Log ("  unduhan valid ({0:N1} MB)" -f ((Get-Item -LiteralPath $OutPath).Length / 1MB)) 'OK'
                return
            }
        } catch {
            Write-Log "  gagal: $($_.Exception.Message)" 'WARN'
        }
    }

    if (Test-Path -LiteralPath $OutPath) { Remove-Item -LiteralPath $OutPath -Force }
    throw 'Download otomatis dari Google Drive gagal (file hasil bukan installer yang valid).'
}

# ============================================================
# INSTALL / UNINSTALL SEB
# ============================================================
function Uninstall-SebApp {
    [CmdletBinding()]
    param([Parameter(Mandatory)][object] $App)

    Write-Log "  menguninstall: $($App.DisplayName) (versi $($App.DisplayVersion))"

    $uninstall = $App.UninstallString
    if ([string]::IsNullOrWhiteSpace($uninstall)) {
        Write-Log '    UninstallString kosong, dilewati' 'WARN'
        return
    }

    # PENTING: variabel bernama $args TIDAK boleh dipakai - itu automatic
    # variable PowerShell dan akan bertabrakan di dalam function/scriptblock.
    $proc = $null

    if ($uninstall -match '^"(?<exe>[^"]+)"\s*(?<rest>.*)$') {
        $exe           = $Matches['exe']
        $uninstallArgs = ($Matches['rest'] + ' /quiet /norestart').Trim()
        $proc = Start-Process -FilePath $exe -ArgumentList $uninstallArgs -Wait -PassThru -NoNewWindow
    } elseif ($uninstall -match 'MsiExec\.exe\s+/X(?<guid>[^\s]+)') {
        $guid = $Matches['guid']
        $proc = Start-Process -FilePath 'MsiExec.exe' -ArgumentList "/X$guid /quiet /norestart" -Wait -PassThru -NoNewWindow
    } else {
        $proc = Start-Process -FilePath 'cmd.exe' -ArgumentList "/c $uninstall /quiet /norestart" -Wait -PassThru -NoNewWindow
    }

    if ($null -ne $proc -and $proc.ExitCode -ne 0) {
        Write-Log "    exit code uninstall: $($proc.ExitCode)" 'WARN'
    }
}

function Install-Seb {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string] $SetupPath)

    if (-not (Test-PortableExecutable -Path $SetupPath)) {
        throw "Installer tidak valid (bukan executable): $SetupPath"
    }

    Write-Log 'Menjalankan installer SEB (mode senyap). Mohon tunggu...' 'STEP'

    $proc = Start-Process -FilePath $SetupPath `
                          -ArgumentList '/install', '/quiet', '/norestart' `
                          -Wait -PassThru -NoNewWindow

    Write-Log "  installer exit code: $($proc.ExitCode)"

    if ($proc.ExitCode -ne 0) {
        Write-Log "  installer melaporkan exit code tidak nol." 'WARN'
    }
}

# ============================================================
# SERVICE / PROSES
# ============================================================
function Stop-SebEverything {
    $svc = Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
    if ($null -ne $svc -and $svc.Status -ne 'Stopped') {
        try {
            Stop-Service -Name $SERVICE_NAME -Force -ErrorAction Stop
            Write-Log '  service SafeExamBrowser dihentikan.' 'OK'
        } catch {
            Write-Log "  service tidak bisa dihentikan: $($_.Exception.Message)" 'WARN'
        }
    }

    $names = @('SafeExamBrowser', 'SafeExamBrowser.Client', 'SafeExamBrowser.Win')
    foreach ($name in $names) {
        $procs = Get-Process -Name $name -ErrorAction SilentlyContinue
        foreach ($p in $procs) {
            try {
                $p.Kill()
                Write-Log "  proses dimatikan: $($p.ProcessName) (PID $($p.Id))" 'WARN'
            } catch {
                Write-Log "  gagal mematikan $($p.ProcessName): $($_.Exception.Message)" 'WARN'
            }
        }
    }
}

function Start-SebService {
    $svc = Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
    if ($null -eq $svc) {
        Write-Log "  service '$SERVICE_NAME' tidak ditemukan - kemungkinan installer belum terpasang penuh." 'WARN'
        return $false
    }

    if ($svc.Status -eq 'Running') {
        Write-Log '  service sudah berjalan.' 'OK'
        return $true
    }

    try {
        Start-Service -Name $SERVICE_NAME -ErrorAction Stop
        Write-Log '  service SafeExamBrowser dijalankan.' 'OK'
        return $true
    } catch {
        Write-Log "  gagal menjalankan service: $($_.Exception.Message)" 'WARN'
        return $false
    }
}

# ============================================================
# PATCH
# ============================================================
function Get-PatchArchive {
    param([Parameter(Mandatory)][string] $OutPath)

    if (Test-Path -LiteralPath $OutPath) { Remove-Item -LiteralPath $OutPath -Force }

    $tick  = (Get-Date).Ticks
    $urls  = @("$PATCH_URL_BASE?t=$tick", "$PATCH_URL_FALLBACK?t=$tick")

    foreach ($url in $urls) {
        try {
            Write-Log "  sumber: $(($url -split '\?')[0])"
            [void](Save-RemoteFile -Uri $url -OutPath $OutPath)

            if (Test-ZipArchive -Path $OutPath) {
                Write-Log ("  patch terunduh ({0:N0} bytes)" -f (Get-Item -LiteralPath $OutPath).Length) 'OK'
                return
            }

            Write-Log '  hasil bukan arsip zip yang valid, coba sumber lain...' 'WARN'
        } catch {
            Write-Log "  gagal: $($_.Exception.Message)" 'WARN'
        }
    }

    throw 'Semua sumber download patch gagal.'
}

function Install-Patch {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $ZipPath,
        [Parameter(Mandatory)][string] $TempFolder
    )

    if (Test-Path -LiteralPath $TempFolder) {
        Remove-Item -LiteralPath $TempFolder -Recurse -Force -ErrorAction SilentlyContinue
    }

    Expand-Archive -LiteralPath $ZipPath -DestinationPath $TempFolder -Force

    if (-not (Test-Path -LiteralPath $DEST)) {
        throw "Folder tujuan tidak ditemukan: $DEST"
    }

    Stop-SebEverything

    # Tunggu file lepas dari lock (service SEB punya watchdog, butuh jeda)
    $maxWait = 30
    $waited  = 0
    while ($waited -lt $maxWait) {
        $locked = $false
        foreach ($f in $PatchFiles) {
            $target = Join-Path $DEST $f
            if (-not (Test-FileUnlocked -Path $target)) { $locked = $true; break }
        }
        if (-not $locked) { break }
        Start-Sleep -Seconds 1
        $waited++
        if ($waited % 5 -eq 0) { Write-Log "  menunggu file dilepas ($waited s)..." 'WARN' }
        if ($waited % 10 -eq 0) { Stop-SebEverything }
    }

    if ($waited -ge $maxWait) {
        Write-Log '  sebagian file masih terkunci, salinan mungkin gagal.' 'WARN'
    }

    # Salin + verifikasi per file
    $report = [System.Collections.Generic.List[object]]::new()

    foreach ($f in $PatchFiles) {
        $src = Join-Path $TempFolder $f
        $dst = Join-Path $DEST $f

        $row = [pscustomobject]@{
            File   = $f
            Status = 'UNKNOWN'
            Note   = ''
        }

        if (-not (Test-Path -LiteralPath $src)) {
            $row.Status = 'MISSING-SRC'
            $row.Note   = 'tidak ada di arsip patch'
            $report.Add($row)
            continue
        }

        try {
            Copy-Item -LiteralPath $src -Destination $dst -Force -ErrorAction Stop

            $srcHash = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
            $dstHash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash

            if ($srcHash -eq $dstHash) {
                $row.Status = 'OK'
            } else {
                $row.Status = 'MISMATCH'
                $row.Note   = 'hash tujuan != sumber (file terkunci?)'
            }
        } catch {
            $row.Status = 'FAILED'
            $row.Note   = $_.Exception.Message
        }

        $report.Add($row)
    }

    return $report
}

# ============================================================
# LAPORAN
# ============================================================
function Show-FileReport {
    param([Parameter(Mandatory)][object[]] $Report)

    Write-Host ''
    Write-Host '  Status patch per file:' -ForegroundColor Cyan
    Write-Host '  ' + ('-' * 58) -ForegroundColor DarkGray

    $ok = 0
    foreach ($row in $Report) {
        $color = switch ($row.Status) {
            'OK'        { 'Green';  }
            'MISMATCH'  { 'Yellow' }
            default     { 'Red'    }
        }
        if ($row.Status -eq 'OK') { $ok++ }

        $name = $row.File.PadRight(48)
        Write-Host "  $name $($row.Status)" -ForegroundColor $color

        if ($row.Note) {
            Write-Host "      -> $($row.Note)" -ForegroundColor DarkGray
        }
    }

    Write-Host '  ' + ('-' * 58) -ForegroundColor DarkGray
    Write-Host "  $ok dari $($Report.Count) file berhasil dipasang." -ForegroundColor White

    return ($ok -eq $Report.Count)
}

function Show-ActualFileState {
    if (-not (Test-Path -LiteralPath $DEST)) { return }

    Write-Host ''
    Write-Host '  File aktif di folder instalasi:' -ForegroundColor Cyan
    Write-Host '  ' + ('-' * 58) -ForegroundColor DarkGray

    foreach ($f in $PatchFiles) {
        $p = Join-Path $DEST $f
        if (Test-Path -LiteralPath $p) {
            $i = Get-Item -LiteralPath $p
            Write-Host ("  {0,-48} {1,10:N0} B  {2}" -f $i.Name, $i.Length, $i.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))
        } else {
            Write-Host ("  {0,-48} TIDAK ADA" -f $f) -ForegroundColor Red
        }
    }
}

# ============================================================
# MAIN
# ============================================================
try {
    # Clear-Host bisa melempar error pada host tertentu (mis. saat output dialihkan
    # ke file). Karena ini statement pertama di dalam try teratas, satu error di sini
    # akan membatalkan seluruh instalasi. Jangan biarkan quirk terminal menggagalkan setup.
    try { Clear-Host } catch { }

    Write-Banner 'SAFE EXAM BROWSER 3.10.1 - AUTO SETUP' 'Cyan'
    Write-Log "Log: $LogPath"
    Write-Log "Waktu: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

    Assert-Administrator
    Write-Log 'Hak Administrator terverifikasi.' 'OK'

    if ($VerifyOnly) {
        Write-Log 'MODE VERIFY-ONLY: tidak ada perubahan yang dilakukan.' 'WARN'
    } else {
        Confirm-Activation
    }

    # --------------------------------------------------------
    Write-Log 'Tahap 1/4 - Memindai instalasi Safe Exam Browser yang ada...' 'STEP'
    # --------------------------------------------------------
    $existing = @(Get-InstalledSeb)

    if ($existing.Count -gt 0) {
        foreach ($a in $existing) {
            Write-Log ("  ditemukan: {0} (versi {1})" -f $a.DisplayName, $a.DisplayVersion)
        }
    } else {
        Write-Log '  tidak ada Safe Exam Browser terpasang.'
    }

    $versionOk = Test-SebVersionMatches -Apps $existing -Version $TARGET_VERSION

    if ($VerifyOnly) {
        Write-Banner 'HASIL PEMINDAIAN' 'Cyan'
        if ($versionOk) {
            Write-Log "Safe Exam Browser $TARGET_VERSION terdeteksi." 'OK'
        } else {
            Write-Log "Safe Exam Browser $TARGET_VERSION TIDAK terdeteksi." 'WARN'
        }

        Show-ActualFileState
        Write-Host ''
        Abort -Code 0
        return
    }

    # --------------------------------------------------------
    Write-Log 'Tahap 2/4 - Menyiapkan Safe Exam Browser...' 'STEP'
    # --------------------------------------------------------
    if ($versionOk -and -not $ForceReinstall) {
        Write-Log "  versi $TARGET_VERSION sudah terpasang, instalasi dilewati." 'OK'
    } else {
        if ($existing.Count -gt 0) {
            Write-Log '  versi lain terdeteksi, membersihkan dulu...' 'WARN'
            foreach ($a in $existing) { Uninstall-SebApp -App $a }
            Start-Sleep -Seconds 5
        }

        $setup = $InstallerPath

        if ([string]::IsNullOrWhiteSpace($setup)) {
            $setup = Join-Path $env:TEMP 'seb_3.10.1_setup.exe'
            Write-Log '  mengunduh installer dari Google Drive...'
            Save-GoogleDriveFile -FileId $DRIVE_FILE_ID -OutPath $setup
        } else {
            if (-not (Test-Path -LiteralPath $setup)) {
                Fail "File installer tidak ditemukan: $setup"
            }
            Write-Log "  memakai installer lokal: $setup"
        }

        Install-Seb -SetupPath $setup

        if (-not $KeepInstaller -and [string]::IsNullOrWhiteSpace($InstallerPath)) {
            Remove-Item -LiteralPath $setup -Force -ErrorAction SilentlyContinue
        }

        Start-Sleep -Seconds 3

        $afterInstall = @(Get-InstalledSeb)
        if (-not (Test-SebVersionMatches -Apps $afterInstall -Version $TARGET_VERSION)) {
            Write-Log '  verifikasi registry gagal - versi target tidak terdeteksi.' 'WARN'
            Write-Log '  Installer SEB mungkin butuh interaksi manual, atau instalasi terblokir policy.' 'WARN'
            Fail "Safe Exam Browser $TARGET_VERSION tidak terpasang." 2
        }

        Write-Log "  Safe Exam Browser $TARGET_VERSION terpasang." 'OK'
    }

    # --------------------------------------------------------
    Write-Log 'Tahap 3/4 - Mengunduh patch bypass...' 'STEP'
    # --------------------------------------------------------
    $patchZip    = Join-Path $env:TEMP 'seb_patch.zip'
    $patchFolder = Join-Path $env:TEMP 'seb_patch_extracted'

    Get-PatchArchive -OutPath $patchZip

    # --------------------------------------------------------
    Write-Log 'Tahap 4/4 - Memasang patch...' 'STEP'
    # --------------------------------------------------------
    $patchReport = Install-Patch -ZipPath $patchZip -TempFolder $patchFolder

    $serviceOk = Start-SebService

    # --------------------------------------------------------
    # BERSIHKAN
    # --------------------------------------------------------
    Remove-Item -LiteralPath $patchZip    -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $patchFolder -Recurse -Force -ErrorAction SilentlyContinue

    # --------------------------------------------------------
    # RINGKASAN
    # --------------------------------------------------------
    Write-Banner 'HASIL AKHIR' 'Green'

    $allPatched = Show-FileReport -Report $patchReport

    $finalState = @(Get-InstalledSeb)
    $finalOk    = Test-SebVersionMatches -Apps $finalState -Version $TARGET_VERSION

    Write-Host ''
    Write-Host '  Ringkasan:' -ForegroundColor Cyan
    Write-Host ('  {0,-32} {1}' -f 'Versi SEB terpasang:', $(if ($finalOk) { "$TARGET_VERSION OK" } else { 'TIDAK TERDETEKSI' }))
    Write-Host ('  {0,-32} {1}' -f 'Service berjalan:', $(if ($serviceOk) { 'YA' } else { 'TIDAK' }))
    Write-Host ('  {0,-32} {1}' -f 'Patch terpasang:', $(if ($allPatched) { 'LENGKAP' } else { 'SEBAGIAN' }))

    if ($script:Warnings.Count -gt 0) {
        Write-Host ''
        Write-Host "  Peringatan selama proses ($($script:Warnings.Count)):" -ForegroundColor Yellow
        foreach ($w in $script:Warnings) { Write-Host "    - $w" -ForegroundColor DarkYellow }
    }

    Show-ActualFileState

    Write-Host ''
    if ($finalOk -and $allPatched) {
        Write-Host ('=' * 62) -ForegroundColor Green
        Write-Host '  SUKSES - Safe Exam Browser 3.10.1 + patch terpasang.' -ForegroundColor Green
        Write-Host ('=' * 62) -ForegroundColor Green
        Write-Host ''
        Write-Host '  Fitur patch:' -ForegroundColor Cyan
        Write-Host '    [+] Bypass deteksi Virtual Machine' -ForegroundColor Gray
        Write-Host '    [+] Fullscreen normal (tidak mudah minimize)' -ForegroundColor Gray
        Write-Host '    [+] Screenshot / PrintScreen diizinkan' -ForegroundColor Gray
        Write-Host '    [+] Taskbar SEB bawah aktif' -ForegroundColor Gray
        Write-Host '    [+] Tombol navigasi browser aktif' -ForegroundColor Gray
        Write-Host '    [+] Tombol power / shutdown di taskbar aktif' -ForegroundColor Gray
        Write-Host ''
        Abort -Code 0
    }

    Write-Host ('=' * 62) -ForegroundColor Yellow
    Write-Host '  SELESAI DENGAN CATATAN - lihat ringkasan di atas.' -ForegroundColor Yellow
    Write-Host ('=' * 62) -ForegroundColor Yellow
    Write-Host ''
    Abort -Code 3
} catch {
    # Abort() melempar sentinel ini setelah menahan window; jangan cetak apa-apa lagi.
    if ($script:Aborted) { return }

    Write-Host ''
    Write-Host ('=' * 62) -ForegroundColor Red
    Write-Host '  ERROR TAK TERDUGA' -ForegroundColor Red
    Write-Host ('=' * 62) -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host ''
    Write-Host "  Lokasi: $($_.InvocationInfo.PositionMessage)" -ForegroundColor DarkGray
    Write-Host ''
    Write-Log "FATAL: $($_.Exception.Message)" 'ERROR'
    Write-Host "  Log lengkap: $LogPath" -ForegroundColor White
    Write-Host ''
    # Sudah di dalam catch teratas: berhenti langsung, jangan lempar sentinel lagi
    # (kalau dilempar dari sini, exception-nya lolos ke console dan tampil sebagai error).
    $script:ExitCode = 1
    if ($script:Standalone) { exit 1 }
    Hold-Window
    return
}
