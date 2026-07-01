# SEB 3.10.1 Final Patch
Repository ini berisi file zip patch SafeExamBrowser 3.10.1.

## Cara Install
Buka PowerShell sebagai Administrator di Windows, lalu jalankan:
`powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "IEX (New-Object Net.WebClient).DownloadString('https://github.com/harezadmm/seb-bypass/raw/main/install_seb.ps1')"
`
"@ | Out-File -FilePath "C:\Users\Hariz\Downloads\SEB\github_upload\README.md" -Encoding utf8

# 4. Buat script install_seb.ps1 agar instalasinya super ringkas!
@"
$url = 'https://github.com/harezadmm/seb-bypass/raw/main/seb3.10.1_final_patch.zip'
$zip = "$env:TEMP\seb_patch.zip"
$tempFolder = "$env:TEMP\seb_patch_extracted"

Write-Host "Downloading patch from GitHub..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $url -OutFile $zip

Write-Host "Extracting files..." -ForegroundColor Cyan
if (Test-Path $tempFolder) { Remove-Item $tempFolder -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $tempFolder -Force

Write-Host "Installing to Program Files..." -ForegroundColor Green
Start-Process cmd -ArgumentList '/c', ""$tempFolder\INSTALL.bat"" -Verb RunAs -Wait

# Clean up
Remove-Item $zip -Force
Remove-Item $tempFolder -Recurse -Force
Write-Host "Selesai! Patch SEB 3.10.1 berhasil terinstall." -ForegroundColor Green
