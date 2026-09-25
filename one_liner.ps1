# one_liner.ps1 - Universal bootstrap: SEB 3.10.1 + bypass patch, self-elevating.
# Cara pakai (PowerShell mana saja, admin / non-admin):
#   [Net.ServicePointManager]::SecurityProtocol='Tls12'
#   irm https://raw.githubusercontent.com/harezadmm/seb-bypass/main/one_liner.ps1 -OutFile $env:TEMP\seb1.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\seb1.ps1
# Non-admin: muncul UAC -> window baru elevated -> ketik 0821 saat diminta.
# Admin: langsung jalan; kode bisa dipipe (echo 0821 | ssh ...).
# Idempotent: aman dijalankan berulang kali.

$ErrorActionPreference = 'Stop'

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# Inner command. $env:TEMP di-escape (backtick) supaya diekspansi di konteks yang
# mengeksekusi, lalu Set-Location + path relatif = aman untuk username yang mengandung spasi.
$c = "[Net.ServicePointManager]::SecurityProtocol='Tls12'; Set-Location `$env:TEMP; irm https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_seb.ps1 -OutFile seb_setup.ps1; powershell -NoProfile -ExecutionPolicy Bypass -File .\seb_setup.ps1; Read-Host 'Selesai - Enter untuk tutup' | Out-Null"

if ($admin) {
    # Sudah elevated (admin console / sesi SSH admin): jalan inline, stdin tetap tersambung
    # sehingga kode aktivasi yang dipipe via SSH tetap terbaca.
    Invoke-Expression $c
} else {
    # Non-admin: UAC elevation, window baru interaktif (user ketik 0821 manual).
    # ArgumentList array: $c diterima verbatim oleh -Command tanpa masalah nested-quote.
    Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-Command',$c
}
