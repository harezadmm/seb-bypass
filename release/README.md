# SEB Bypass — Release v1.0.0

Semua artifact siap pakai, dikelompokkan per platform.

**Kode aktivasi installer Windows: `0821`**

---

## Windows

| File | Ukuran | Keterangan |
|---|---|---|
| `SEB Config Bypass Studio.exe` | 12 MB | GUI bypass config — **satu file, tidak butuh Python** |
| `seb_bypass_gui.py` | 41 KB | versi skrip (butuh Python 3) |

`.exe` sudah dibangun & diuji di Windows 11 x64 (Python 3.13, PyInstaller 6.22.3):
PE x64 valid, subsystem GUI (tanpa jendela konsol), smoke test exit 0.

SmartScreen mungkin memperingatkan karena belum ditandatangani:
**More info → Run anyway**.

### Installer bypass penuh (SEB 3.10.2)

```powershell
[Net.ServicePointManager]::SecurityProtocol='Tls12'
irm https://raw.githubusercontent.com/harezadmm/seb-bypass/main/one_liner.ps1 -OutFile $env:TEMP\seb1.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\seb1.ps1
```

---

## macOS

| File | Ukuran | Keterangan |
|---|---|---|
| `SEB Config Bypass Studio.app.zip` | 11 MB | GUI — extract lalu jalankan |
| `SEB Config Bypass Studio.dmg` | 12 MB | GUI versi DMG |
| `seb_bypass_gui.py` | 41 KB | versi skrip (butuh Python 3) |

`.app` ditandatangani ad-hoc (bukan Developer ID), jadi macOS bisa menolak
saat pertama dibuka:

```bash
xattr -dr com.apple.quarantine "SEB Config Bypass Studio.app"
# atau: klik kanan app -> Open -> Open
```

### Installer bypass (SEB 3.7.1)

```bash
curl -fsSL https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_mac_one_v2.sh | bash
```

---

## Config hasil bypass

| File | Untuk | `browserURLSalt` |
|---|---|---|
| `confignew.bypass.seb` | config ujian UNAIR (Moodle) | `False` — coba ini dulu |
| `confignew.bypass.salt-preserved.seb` | varian konservatif | `True` — kalau server menolak |
| `SebClientSettings.seb` | profil bypass umum | `False` |

Cukup buka file `.seb` langsung di SEB polos. Input asli tidak diubah.

`browserURLSalt` memengaruhi perhitungan Browser Exam Key. Varian `False`
mencegah popup macet saat startURL tanpa salt; varian `True` lebih aman kalau
LMS memvalidasi BEK.

---

## Patch Windows (SEB 3.10.2)

| File | Keterangan |
|---|---|
| `seb3.10.2_final_patch.zip` | patch dasar (VM, Alt+Tab, taskbar, screenshot) |
| `seb3.10.2_integrity_patched.zip` | patch dasar + fix lock 10-15 menit |
| `seb_integrity_fix.zip` | fix integrity saja (2 binary + Configuration.dll asli) |

`seb_integrity_fix.zip` memuat `SafeExamBrowser.Configuration.dll` **asli**
supaya instalasi yang rusak akibat fix v1 (InvalidProgramException) ikut
dipulihkan.

---

## Tentang lock screen 10-15 menit

SEB 3.10.2 memverifikasi tanda tangan binernya sendiri tiap ~10 menit
(`ScheduleIntegrityVerification`) dan mengunci karena binary patch tidak
bertanda tangan. Ditambah 5 jalur lock lain di `MonitoringResponsibility` —
salah satunya (`ApplicationMonitor_TerminationFailed`) **tidak punya kunci
config sama sekali**.

Fix menutup semuanya: **19 method** dipatch di 2 binary.
Detail: `build/README.md` dan docstring `seb_fix_integrity_lock.py`.

Config-only juga tersedia (tanpa patch) lewat GUI di atas — tapi jalur
`TerminationFailed` hanya bisa ditutup dengan patch biner.

---

## Checksums

Lihat `CHECKSUMS.txt`.

## Catatan kejujuran

- Verifikasi biner (PE/IL) dan smoke test dijalankan nyata. Uji akhir tetap
  di mesin ujian masing-masing.
- Screenshot GUI Windows belum bisa diambil (sesi SSH tanpa desktop) — yang
  terbukti: binary jalan, GUI init, logika benar.
