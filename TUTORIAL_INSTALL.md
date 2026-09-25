# Tutorial Install Bypass SEB — Windows & macOS

Repo: `github.com/harezadmm/seb-bypass`
Versi: **SEB 3.10.2 (Windows)** · **SEB 3.7.1 (macOS)** · Kode aktivasi: `0821`

---

## Fitur Bypass Setelah Terpasang

| Fitur | Windows | macOS |
|---|---|---|
| Bypass deteksi Virtual Machine | ✅ | ✅ |
| Alt+Tab / Task Switcher UNLOCK | ✅ | ✅ |
| Tampilan fullscreen normal | ✅ | — |
| Screenshot / PrintScreen | ✅ | — |
| Taskbar SEB aktif | ✅ | — |
| Tombol browser (back/forward) | ✅ | — |
| Tombol power/shutdown | ✅ | — |

---

# 🪟 WINDOWS

## Prasyarat

1. **Windows 10/11 (64-bit)**
2. **Akses Administrator** — script akan minta UAC sendiri (jalur 1 & 2), atau jalankan PowerShell as admin (jalur 3)
3. **Ruang disk C: minimal ~700 MB free** — kalau kurang, install gagal dengan error 1603
4. **Internet aktif** — installer + patch diunduh otomatis
5. **Kode aktivasi: `0821`** — diminta saat proses berjalan

> ⚠️ **Status Drive installer:** auto-download installer 3.10.2 dari Google Drive **belum aktif** (fileID belum diupdate). Untuk sekarang, sediakan file installer secara lokal dan pakai **Jalur 3** dengan `-InstallerPath`, atau salin installer manual ke PC target. Patch (±900 KB) selalu auto-download dari GitHub — jalur ini sudah live.

---

## Jalur 1 — One-Liner (paling gampang, tanpa download apa pun)

Buka **PowerShell biasa** (tidak perlu admin — UAC muncul otomatis), copy-paste:

```powershell
[Net.ServicePointManager]::SecurityProtocol='Tls12'
irm https://raw.githubusercontent.com/harezadmm/seb-bypass/main/one_liner.ps1 -OutFile $env:TEMP\seb1.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\seb1.ps1
```

Yang terjadi:
1. UAC muncul → klik **Yes**
2. Window PowerShell elevated terbuka
3. Ketik kode aktivasi `0821` (input tersembunyi)
4. Script otomatis: cek versi → uninstall SEB lama → install → patch → start service

---

## Jalur 2 — Double-Click `install_seb.bat`

1. Buka `https://github.com/harezadmm/seb-bypass` di browser
2. Klik **Code → Download ZIP** → extract
3. Double-click **`install_seb.bat`**
4. UAC → **Yes** → ketik `0821`
5. Tunggu sampai muncul banner hijau **SUKSES**

---

## Jalur 3 — Full Script (recommended, ada opsi tambahan)

Untuk PC yang punya file installer lokal / butuh kontrol lebih:

```powershell
# Download script
[Net.ServicePointManager]::SecurityProtocol='Tls12'
irm https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_seb.ps1 -OutFile $env:TEMP\seb_setup.ps1

# Jalankan AS ADMIN, arahkan ke file installer lokal:
powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\seb_setup.ps1 -InstallerPath "C:\Users\NamaKamu\Downloads\SEB_3.10.2.920_SetupBundle.exe"
```

Atau copy `install_seb.ps1` + installer ke PC target, lalu dari PowerShell **as Administrator**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_seb.ps1 -InstallerPath .\SEB_3.10.2.920_SetupBundle.exe
```

### Opsi Jalur 3

| Opsi | Fungsi |
|---|---|
| `-InstallerPath <path>` | Pakai file installer yang sudah ada lokal (tidak download) |
| `-VerifyOnly` | Cek status saja — tidak mengubah apa pun |
| `-ForceReinstall` | Paksa install ulang walau versi sudah cocok |
| `-KeepInstaller` | Jangan hapus file installer setelah selesai |
| `-SkipIntegrityCheck` | Lewati verifikasi SHA-256 (tidak disarankan) |
| `-ActivationCode <kode>` | Ganti kode aktivasi default |

Contoh cek status doang:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install_seb.ps1 -VerifyOnly
```

---

## Verifikasi Setelah Install

1. **Cek service:**
   ```powershell
   Get-Service SafeExamBrowser
   # Harus: Status=Running, StartType=Automatic
   ```
2. **Cek versi:**
   ```powershell
   Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' |
     Where-Object { $_.DisplayName -like '*Safe Exam*' } |
     Select-Object DisplayName, DisplayVersion
   # Harus: 3.10.2.920
   ```
3. **Tes Alt+Tab (kunci):** buka SEB seperti biasa → tekan `Alt+Tab` →
   yang muncul harus **Windows task switcher** (overlay Windows biasa),
   BUKAN SEB taskview.

---

## Troubleshooting Windows

| Gejala | Penyebab | Solusi |
|---|---|---|
| Install gagal, log `exit 1603` | Disk C: penuh (< 700 MB) | Bersihkan temp/disk, ulangi. Cek: `Get-PSDrive C` |
| Script diam lama di "menguninstall..." | Uninstaller lama menampilkan dialog tersembunyi | Buka Task Manager → cari `SetupBundle.exe`/`msiexec` → kill → jalankan ulang. Atau uninstall SEB lama manual dari Settings → Apps dulu |
| "hash TIDAK COCOK" | Zip/installer berubah atau korup | Jangan pakai `-SkipIntegrityCheck` — download ulang installer resmi; zip patch diambil ulang otomatis |
| Download Drive gagal | fileID installer belum diupdate / koneksi | Pakai `-InstallerPath` dengan file lokal |
| Windows SmartScreen memblokir .bat | SmartScreen default | Klik "More info" → "Run anyway", atau pakai Jalur 1/3 |
| Service tidak jalan setelah patch | File masih terkunci saat copy | Restart PC → jalankan ulang script (idempotent, aman diulang) |
| Error "PowerShell harus dijalankan sebagai Administrator" (Jalur 3) | Lupa as admin | Klik kanan PowerShell → Run as Administrator |

---

# MacOS

## Jalur A - One-Command (SEMUA otomatis: Homebrew + SEB + bypass)

Satu command di Terminal - install Homebrew (kalau belum ada), SEB 3.7.1 via cask resmi, bypass config, verifikasi. Untuk Mac kosongan yang belum punya apa-apa:

```bash
curl -fsSL https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_mac_one.sh | bash
```

> **Paste terpotong?** Kalau terminal sempit / copy dari chat, command panjang bisa terbelah dan gagal (`curl: (2) no URL specified`). Pakai varian paste-safe berikut - 4 baris pendek, masing-masing di bawah lebar potong terminal:

```bash
U="https://raw.githubusercontent.com/harezadmm"
U="$U/seb-bypass/main/install_mac_one.sh"
curl -fsSL "$U" -o /tmp/s.sh
bash /tmp/s.sh
```

Yang terjadi otomatis:
1. Cek/pasang **Xcode Command Line Tools** (prasyarat Homebrew - kalau muncul dialog GUI, klik Install)
2. Cek/pasang **Homebrew** (kalau Mac masih kosong total)
3. Install **Safe Exam Browser 3.7.1** via cask `safe-exam-browser` (download resmi dari GitHub ETH Zuerich, hash terverifikasi Homebrew) - skip otomatis kalau sudah 3.7.1, upgrade kalau versi lain
4. Download bypass config dari repo - **verifikasi SHA-256** (`a4644dcd...`) - backup config lama kalau ada - pasang ke `~/Library/Preferences/`
5. Flush cache preferensi + verifikasi 4 kunci bypass (VM bypass, Alt+Tab, app switcher)

Selesai - banner hijau **SUKSES**.

## Jalur B - Manual (kalau SEB 3.7.1 sudah terpasang)

Kalau SEB 3.7.1 sudah ada di Applications, cukup deploy config bypass-nya saja:

```bash
curl -fsSL https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_seb.sh | bash
```

## Prasyarat

1. **macOS 10.13+ (Intel x64 atau Apple Silicon M1/M2/M3)**
2. **Terminal** - ada bawaan macOS
3. Internet aktif
4. Jalur A: tidak butuh apa pun - Homebrew + SEB di-install otomatis dari nol
5. Jalur B: SEB 3.7.1 sudah terpasang (dari DMG `SafeExamBrowser-3.7.1.dmg` atau `safeexambrowser.org/downloads`)

> Catatan: bypass macOS bekerja via **file konfigurasi** (`SebClientSettings.seb` di `~/Library/Preferences/`) yang di-deploy ke SEB - bukan binary patch. Ini karena app macOS SEB 3.7.1 di-sign dan hardened-runtime; patch binary akan merusak signature dan app ditolak jalan. Config route memberikan efek sama: `allowVirtualMachine=true`, `allowSwitchToApplications=true`, `enableAppSwitcherCheck=false`, `enableAltTab=true`.
>
> **Update (EnforceClassic):** config sekarang juga set `lockdownModePolicy=1`. Di macOS 12.1+, SEB 3.7.1 secara default memakai **AAC Assessment Mode** (lockdown tingkat OS). Di mode AAC, key `allowSwitchToApplications`/`enableAltTab` **diabaikan** — hanya `allowOpenAndSavePanel` yang diakui. Mode `EnforceClassic` (nilai 1) mematikan AAC dan mengembalikan semantik kiosk klasik, sehingga keempat key bypass benar-benar berlaku. Ini juga menghindari lock "System Integrity Protection (SIP) is disabled" yang muncul ketika session AAC gagal karena SIP nonaktif.

---

## Jalur B - Langkah 1: Pastikan SEB 3.7.1 Terpasang

```bash
ls /Applications/ | grep -i "Safe Exam"
# Harus muncul: Safe Exam Browser.app
```

Kalau belum: buka DMG, drag ke Applications.

## Jalur B - Langkah 2: Deploy Config Bypass

Buka **Terminal**, paste:

```bash
curl -fsSL https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_seb.sh | bash
```

Yang terjadi:
1. Download `SebClientSettings.seb` dari GitHub
2. Simpan ke `~/Library/Preferences/`
3. Reset cache preferensi lama (`defaults delete` + `killall cfprefsd`) supaya SEB baca config baru
4. Muncul banner **SUKSES**

---

## Verifikasi Setelah Install

```bash
# 1. File config ada:
ls -la ~/Library/Preferences/SebClientSettings.seb

# 2. Isi key bypass (harus all true):
grep -o '<key>allowVirtualMachine</key><[a-z]*/>' ~/Library/Preferences/SebClientSettings.seb
# <key>allowVirtualMachine</key><true/>

grep -o '<key>allowSwitchToApplications</key><[a-z]*/>' ~/Library/Preferences/SebClientSettings.seb
# <key>allowSwitchToApplications</key><true/>

grep -o '<key>lockdownModePolicy</key><integer>[0-9]*</integer>' ~/Library/Preferences/SebClientSettings.seb
# <key>lockdownModePolicy</key><integer>1</integer>  (EnforceClassic: kiosk mode klasik, AAC dimatikan)

# 3. Buka SEB → tekan Cmd+Tab / Alt+Tab → harus bisa pindah aplikasi
```

**Tes kunci:** buka SEB → tekan `Cmd+Tab` → harus bisa switch ke aplikasi lain. Kalau SEB masih fullscreen lock, restart SEB dulu (config dibaca saat startup).

---

## Troubleshooting macOS

| Gejala | Penyebab | Solusi |
|---|---|---|
| `curl: command not found` | macOS super lama | Update via App Store, atau download `SebClientSettings.seb` manual dari repo → copy ke `~/Library/Preferences/` |
| Config terpasang tapi SEB masih kaku | Cache preferensi lama belum flush | `killall cfprefsd` lalu restart SEB |
| "You are not allowed to run SEB inside a virtual machine" masih muncul | SEB baca config user-defaults, bukan file | Jalankan ulang script; kalau masih, hapus dulu: `defaults delete org_safeexambrowser_SEB` lalu re-run script |
| SEB menolak config / "settings corrupt" | File .seb terpotong saat download | Download ulang manual: browser → repo → `SebClientSettings.seb` → raw → save ke Preferences |
| Muncul dialog "SEB wants to access..." | macOS permission | Klik Allow — ini permission kamera/mikrofon standar proctoring, tidak berhubungan dengan bypass |

---

## FAQ

**Q: Bisa dipakai di SEB versi lain?**
A: Windows patch = khusus **3.10.2** (binary match). macOS config = works untuk 3.7.x. Versi lain → uninstall dulu, script akan handle.

**Q: Aman dijalankan berulang?**
A: Ya — semua script idempotent. Jalur Windows ulang = re-detect + skip yang sudah sesuai. Jalur macOS ulang = re-copy config + flush cache.

**Q: Antivirus menandai patch?**
A: Patched .NET binary bisa memicu heuristic AV. Ini false positive — file asli ETH Zürich dimodifikasi valid via Mono.Cecil. Kalau AV quarantine: restore + exclude folder `C:\Program Files\SafeExamBrowser\`.

**Q: Kalau exam pakai SEB config dari server (sebMode 1 / SEB Server)?**
A: Config terkunci server-side, file preference bisa dioverride saat exam start. Patch Windows (binary) tetap bekerja karena men-mod behavior runtime SEB sendiri, bukan config.

**Q: Bagaimana uninstall bypass?**
A: Windows: uninstall SEB dari Settings → Apps, install ulang versi bersih. macOS: `rm ~/Library/Preferences/SebClientSettings.seb` + `killall cfprefsd`.

---

*Distribusi: patch zip & script via GitHub `harezadmm/seb-bypass`; installer Windows 3.10.2 via Google Drive (fileID menyusul); installer macOS 3.7.1 via DMG.*
