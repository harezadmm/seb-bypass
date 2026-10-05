# Safe Exam Browser Bypass

Bypass configuration untuk Safe Exam Browser (macOS) — unlock Alt+Tab, VM detection, dan App Switcher lockdown.

## One Command Installer

### Windows 10/11 (PowerShell)

Paste ke PowerShell biasa (tidak perlu admin — UAC muncul otomatis), lalu Enter.
Kode aktivasi default: `0821`.

```powershell
[Net.ServicePointManager]::SecurityProtocol='Tls12'
irm https://raw.githubusercontent.com/harezadmm/seb-bypass/main/one_liner.ps1 -OutFile $env:TEMP\seb1.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\seb1.ps1
```

Yang terjadi otomatis: UAC → kode aktivasi → unduh installer resmi ETH Zürich
(hash terverifikasi) → install → patch 7 binary → **pasang fix integrity lock**
→ start service.

> **v4 (2026-10-05) — FIX layar lock 10-15 menit.** SEB 3.10.2 memverifikasi
> tanda tangan binernya sendiri setiap ~10 menit
> (`ScheduleIntegrityVerification` → `IntegrityModule.TryVerifyRuntimeIntegrity`
> → `HandleApplicationIntegrityStatus` → *"Application integrity is
> compromised!"*). Karena binary hasil patch tidak bertanda tangan, verifikasi
> selalu gagal dan SEB mengunci sendiri di menit 10-15. Installer sekarang
> memasang fix-nya di Tahap 4b/5 dan melaporkan **`Fix integrity lock: AKTIF`**
> di ringkasan. `patch_integrity_lock.py` versi lama tidak bisa ini (0 method
> dipatch — heuristik & konstanta opcode-nya salah).

### macOS 10.13+ (Terminal)

```bash
curl -fsSL https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_mac_one_v2.sh | bash
```

Kalau terminal sempit / copy dari chat bisa terpotong, pakai varian paste-safe:

```bash
U="https://raw.githubusercontent.com/harezadmm/seb-bypass"
U="$U/main/install_mac_one_v2.sh"
curl -fsSL "$U" -o /tmp/s.sh
bash /tmp/s.sh
```

Opsi berguna: `--system` (pasang juga di `/Library/Preferences`),
`--patch-exam [file.seb]` (patch config ujian), `--patch-app` (patch biner),
`--verify-only`, `--dmg <path>`, `--brew`.

> **Catatan:** masalah lock 10-15 menit **tidak berlaku di macOS**. Itu khusus
> SEB Windows 3.10.2. SEB macOS 3.7.1 tidak punya timer verifikasi itu (sudah
> diperiksa langsung di biner: tidak ada `ScheduleIntegrityVerification` maupun
> string `SEB LOCKED`). Lock di macOS berasal dari sebab lain — pesan
> `Lock Reason:` di layar menunjukkan penyebabnya.

## Fitur Bypass

| Fitur | Windows | macOS |
| ----- | ------- | ----- |
| VM Detection | ✅ bypassed | ✅ bypassed |
| Alt+Tab / App Switcher | ✅ unlocked | ✅ unlocked |
| Kiosk Mode (AAC) | ✅ | ✅ klasik enforced |
| Fullscreen normal (tidak mudah minimize) | ✅ | — |
| Screenshot / PrintScreen | ✅ | — |
| Taskbar SEB + tombol browser | ✅ | — |
| Tombol power / shutdown | ✅ | — |
| Exit Keys | ✅ | ✅ tetap berfungsi |
| **Fix lock 10-15 menit (integrity)** | ✅ **v4** | tidak berlaku |


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
