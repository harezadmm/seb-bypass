# SEB Config Bypass Studio — Build

Aplikasi GUI untuk membuka `config.seb`, mendeteksi bagian yang terkunci,
memilih bypass, lalu menulis config baru. Sumber: `../seb_bypass_gui.py`

---

## Penting: PyInstaller tidak bisa cross-compile

`.exe` **wajib** dibangun di Windows. `.app`/`.dmg` **wajib** dibangun di macOS.
Tidak ada cara membuat `.exe` dari Mac tanpa Windows (Wine pun tidak didukung
untuk Tkinter).

Tiga cara mendapat `.exe`:

| Cara | Butuh Windows? | Hasil |
|---|---|---|
| GitHub Actions | tidak | `.exe` otomatis dari cloud |
| `build_windows.ps1` di PC Windows | ya | `.exe` lokal |
| Jalankan `seb_bypass_gui.py` langsung | tidak | butuh Python, bukan `.exe` |

---

## macOS — `.app` + `.dmg`

```bash
cd build
bash build_mac.sh
```

Menghasilkan:
- `build/dist/SEB Config Bypass Studio.app`
- `build/SEB Config Bypass Studio.dmg`  (~12 MB)

Script otomatis: membuat venv → pasang pyinstaller+pillow → buat ikon →
build → codesign ad-hoc → bungkus DMG.

**Buka pertama kali.** Aplikasi ditandatangani ad-hoc (bukan Developer ID),
jadi macOS bisa menolak. Cara membuka:

```bash
# klik kanan app -> Open -> Open
# atau hilangkan tanda karantina:
xattr -dr com.apple.quarantine "dist/SEB Config Bypass Studio.app"
```

---

## Windows — `.exe`

Di PC Windows (PowerShell):

```powershell
cd build
powershell -ExecutionPolicy Bypass -File build_windows.ps1
```

Menghasilkan: `build\dist\SEB Config Bypass Studio.exe` (~25–30 MB, satu file,
tanpa jendela konsol).

File `.exe` bisa dipindah ke PC mana pun — **tidak butuh Python terpasang**.

SmartScreen mungkin memperingatkan karena belum ditandatangani:
**More info → Run anyway**.

---

## Otomatis lewat GitHub Actions

Workflow siap pakai ada di **`build/ci/build.yml`**. File ini dibangun dan
diuji sebagai YAML, tapi belum aktif sebagai workflow karena token yang
dipakai untuk push tidak punya scope `workflow` (GitHub menolak
`.github/workflows/*` tanpa scope itu).

**Aktifkan (sekali saja):**

```bash
mkdir -p .github/workflows
cp build/ci/build.yml .github/workflows/build.yml
git add .github/workflows/build.yml
git commit -m "ci: aktifkan build workflow"
git push
```

Kalau push ditolak dengan pesan
*"refusing to allow an OAuth App to create or update workflow"*, tambahkan
scope `workflow` ke token:

```bash
gh auth refresh -s workflow      # lalu ikuti instruksi di browser
```

Atau tempel file itu lewat web GitHub:
**Add file → Create new file → `.github/workflows/build.yml`**.

**Setelah aktif:**

- Jalan otomatis kalau ada tag `v*`
- Bisa dipicu manual: tab **Actions** → **build-gui** → **Run workflow**
- Hasil diunggah sebagai artifact:
  - `SEB-Config-Bypass-Studio-Windows` → `.exe`
  - `SEB-Config-Bypass-Studio-macOS` → `.dmg` + `.app`
- Kalau dipicu tag, file ditempelkan ke GitHub Release

Contoh memicu lewat tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Setiap job menjalankan **smoke test headless** dulu (memuat config contoh,
menerapkan preset, memastikan output terbentuk) sebelum mengunggah artifact.

> Catatan: smoke test Windows memakai `Start-Process -Wait` karena `.exe` ini
> GUI (`console=False`) dan PowerShell **tidak** menunggu aplikasi GUI kalau
> dipanggil dengan `&`, sehingga test bisa lolos/gagal palsu.

---

## Ikon

`make_icon.py` membuat `assets/sebstudio.icns` (macOS) dan
`assets/sebstudio.ico` (Windows) — perisai dengan gembok terbuka.

```bash
python make_icon.py     # butuh pillow
```

---

## Struktur

```
build/
├── ci/build.yml            workflow GitHub Actions (salin ke .github/workflows/)
├── seb_bypass_gui.spec     spec PyInstaller (dipakai kedua platform)
├── build_mac.sh            build macOS
├── build_windows.ps1       build Windows
├── make_icon.py            pembuat ikon
└── assets/
    ├── sebstudio.icns      ikon macOS
    ├── sebstudio.ico       ikon Windows
    └── icon.png            pratinjau
```

---

## Mode CLI (tanpa GUI, berguna untuk otomasi)

Binary hasil build juga mendukung mode uji headless lewat variabel lingkungan
(dipakai smoke test CI):

```bash
SEB_GUI_SMOKE=/path/in.seb SEB_GUI_SMOKE_OUT=/path/out.seb \
  "./dist/SEB Config Bypass Studio.app/Contents/MacOS/SEB Config Bypass Studio"
```

Versi Python-nya punya CLI penuh:

```bash
python3 seb_bypass_gui.py --cli IN.seb OUT.seb --list
python3 seb_bypass_gui.py --cli IN.seb OUT.seb --preset recommended
python3 seb_bypass_gui.py --cli IN.seb OUT.seb --keys allowSwitchToApplications,allowVirtualMachine
```
