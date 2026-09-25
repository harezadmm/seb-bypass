@echo off
rem install_seb.bat - Universal SEB 3.10.1 + bypass patch (double-click ini di device mana saja).
rem Alur: PowerShell bootstrap -> one_liner.ps1 (self-elevate via UAC jika perlu) -> install_seb.ps1
rem Non-admin: muncul UAC, lalu ketik 0821 di window elevated saat diminta.
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; irm https://raw.githubusercontent.com/harezadmm/seb-bypass/main/one_liner.ps1 -OutFile $env:TEMP\seb1.ps1; powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\seb1.ps1"
