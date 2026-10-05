# seb-toggle — setup

CLI untuk membaca konfigurasi Safe Exam Browser (`.seb`), memindai restriksi yang aktif,
mem-toggle-nya secara interaktif, dan menulis hasilnya ke **file baru**. Input tidak pernah
diedit di tempat.

Registry key/mapper/default diambil dari hasil dekompilasi SEB 3.10.2, bukan dari daftar
yang diketik manual.

---

## 1. Kebutuhan

- **Python 3.8+** (dipakai `Path.unlink(missing_ok=True)` dan f-string).
- **Tanpa dependensi pihak ketiga.** Hanya stdlib: `plistlib`, `argparse`, `base64`, `pathlib`,
  `json`, `re`, `os`, `sys`. GUI memakai `tkinter`, yang sudah ikut dalam installer Python resmi
  (di Linux kadang perlu paket terpisah — lihat §4b).
- Terminal yang mendukung ANSI kalau ingin warna (Windows 10+, Windows Terminal, Orca).

Cek versi:

```bash
python --version
```

## 2. Isi folder

| File | Peran |
|---|---|
| `seb_toggle.py` | CLI utama. Satu file, mandiri. |
| `seb_gui.py` | GUI Tkinter. Memakai `seb_toggle.py` sebagai mesin — tidak ada logika ganda. |
| `seb_registry.json` | **Artefak generated.** Sumber data key/mapper/default. Dibaca saat runtime. |
| `build_registry.py` | Regenerasi `seb_registry.json` dari tree dekompilasi. |
| `plan.md` | Dokumen desain + angka ground truth + rencana verifikasi. |
| `enums_reference.json` | 17 enum publik SEB beserta member-nya. Referensi untuk `ENUM_SPACES`, bukan dibaca runtime. |
| `seb.cmd` | Launcher Windows (CLI). |
| `seb_gui.cmd` | Launcher Windows (GUI). |
| `seb` | Launcher bash. |
| `dist/` | Hasil build siap pakai — lihat §2b. |
| `SEB Toggle.command` | **Launcher macOS.** Double-click di Finder; butuh Python 3 + tkinter. |
| `build-macos.sh` | Build `SEB Toggle.app` di macOS. Memilih Python ber-Tk modern sendiri. |

| `make_icon.py`, `seb.ico`, `icons/` | Generator + aset ikon. |
| `tools/` | Utilitas bantu — lihat §2c. |
| `setup.md` | Dokumen ini. |

### 2b. Isi `dist/`

```
dist/
  windows/
    SEB-Toggle.exe        GUI, tanpa console - double-click untuk buka
    seb-toggle-cli.exe    CLI
  macos/
    SEB Toggle.app        siap dipakai (arm64 / Apple Silicon)
    seb-macos.tar.gz      arsip asli - pakai INI kalau memindahkan antar mesin
    seb-toggle-cli        CLI untuk macOS
```

### 2c. Isi `tools/`

| File | Fungsi |
|---|---|
| `manifest.py` | Cetak manifest tree (D/F/L + ukuran + target symlink). Dipakai untuk membuktikan salinan antar-mesin identik. |
| `inspect_seb.py` | Baca file `.seb` dan laporkan formatnya (plist / container / terenkripsi), jumlah key, dan nilai key penting. **Hanya membaca** — tidak pernah menulis. |

### 2d. Kenapa sumber tidak dipindah ke subfolder

`seb_toggle.py` menemukan registry lewat `Path(__file__).with_name("seb_registry.json")`, dan
`seb_gui.py` meng-import `seb_toggle` dari folder yang sama. Jadi `seb_toggle.py`,
`seb_gui.py`, dan `seb_registry.json` **wajib** satu folder. Memindahkannya ke `src/` akan
memutus keduanya.

`seb_toggle.py` menunjuk registry lewat `Path(__file__).with_name("seb_registry.json")` — jadi
folder ini bisa dipindah ke mana saja atau di-rename, dan tetap jalan. Tidak ada path absolut
yang ditanam.

## 3. Instalasi

Tidak ada langkah build. Salin folder ini, lalu:

```bash
cd seb-toggle
python seb_toggle.py --help
```

Launcher (opsional):

- Windows: `seb.cmd --help`
- Linux/macOS: `chmod +x seb && ./seb --help`

## 3b. Pakai tanpa Python (executable)

### Windows

Double-click **`dist/windows/SEB-Toggle.exe`**. Tidak perlu Python, tidak perlu terminal.

CLI-nya juga tersedia sebagai exe:

```cmd
dist\windows\seb-toggle-cli.exe "C:\path\ke\config.seb" --scan
dist\windows\seb-toggle-cli.exe "C:\path\ke\config.seb" --unlock-all -y -o terbuka.seb
```

**Run pertama lambat — ini normal.** Di mesin uji: 22,6 detik pada launch pertama, 6,9 detik
pada kedua. Sebabnya bundel *onefile* mengekstrak ~12 MB ke folder temp, dan Windows Defender
memindai binary baru. Jendela akan muncul; tunggu, jangan klik dua kali berulang.

**Peringatan SmartScreen.** Exe ini tidak ditandatangani. Kalau muncul
"Windows protected your PC" → **More info** → **Run anyway**.

### macOS

Dua cara, pilih satu:

**A. Tanpa build — langsung pakai** (butuh Python 3 + tkinter, mis. installer resmi dari python.org):

Double-click **`SEB Toggle.command`** di Finder.

Kalau macOS menolak membukanya: klik kanan → **Open** → **Open** lagi. Atau lewat Terminal:

```bash
chmod +x "SEB Toggle.command" && ./"SEB Toggle.command"
```

**B. Pakai `.app` yang sudah dibuild** — hasilnya ada di folder `dist/macos/`:

```
dist/macos/SEB Toggle.app      siap dipakai (arm64 / Apple Silicon)
dist/macos/seb-macos.tar.gz    arsip asli - pakai INI kalau memindahkan antar mesin
dist/macos/seb-toggle-cli      CLI untuk macOS
```

Salin `dist/macos/SEB Toggle.app` ke `/Applications`, lalu double-click.

> **Penting soal symlink.** Sebuah `.app` macOS berisi symlink. Kalau tree-nya disalin
> antar-filesystem (zip, flashdisk FAT, Windows), symlink bisa rusak dan app tidak akan jalan.
> Untuk memindahkan antar mesin, **pakai `dist/macos/seb-macos.tar.gz`** dan ekstrak di Mac:
>
> ```bash
> tar xzf seb-macos.tar.gz     # menghasilkan SEB Toggle.app + seb-toggle-cli
> ```

**Hanya Apple Silicon (arm64).** Build ini dibuat di Mac M-series. Untuk Mac Intel,
build sendiri di mesin itu dengan cara C.

**C. Build sendiri** (untuk Mac Intel, atau ingin membangun ulang):

```bash
cd seb-toggle
chmod +x build-macos.sh
./build-macos.sh
```

Hasilnya `dist/macos/SEB Toggle.app` — geser ke `/Applications`, lalu double-click.

Skrip memilih Python-nya sendiri dan hanya menerima **Python >= 3.9 dengan Tk >= 8.6**.
Python bawaan Apple (`/usr/bin/python3`) memakai Tk 8.5 yang usang dan **akan ditolak** —
skrip memberi tahu cara memasang yang benar. Ia juga membuat venv sendiri (`.venv-build`),
jadi Python sistem tidak dikotori.

PyInstaller tidak bisa cross-compile: binary macOS tidak mungkin dibuat dari Windows.
Itulah sebabnya `.app` di `dist/macos/` dibangun langsung di Mac kamu.

**Gatekeeper.** `.app` yang belum ditandatangani akan diblokir saat pertama dibuka:
klik kanan → **Open** → **Open**. Atau sekali saja di Terminal:

```bash
xattr -dr com.apple.quarantine "dist/macos/SEB Toggle.app"
```

## 4. Mulai cepat

```bash
# 1. Pindai saja — read-only, tidak menulis apa pun
python seb_toggle.py "C:/path/ke/config.seb" --scan

# 2. Toggle interaktif
python seb_toggle.py "C:/path/ke/config.seb"

# 3. Toggle non-interaktif, satu key
python seb_toggle.py "C:/path/ke/config.seb" -s downloadPDFFiles=true -y -o hasil.seb

# 4. Buka semua batasan sekaligus
python seb_toggle.py "C:/path/ke/config.seb" --unlock-all -y -o terbuka.seb

# 5. Bandingkan dua config
python seb_toggle.py --diff hasil.seb "C:/path/ke/config.seb"
```

## 4b. GUI (Tkinter)

```bash
python seb_gui.py
```

Atau `seb_gui.cmd` (Windows) / `./seb-gui` (bash). Bisa juga langsung membuka satu file:

```bash
python seb_gui.py "C:/path/ke/config.seb"
```

Isi jendela:

| Bagian | Fungsi |
|---|---|
| Baris **File** | Pilih + Muat config. Ringkasan `originatorVersion`, ukuran, jumlah key. |
| Chip warna | Jumlah key yang memblokir / mengizinkan / mode / diabaikan / absen. |
| **Buka Semua Batasan** | Antrekan seluruh profil relaksasi (sama dengan `--unlock-all`). |
| **Pilih yang memblokir** | Centang semua key yang sekarang `False` (47 di `config (1)`). |
| **Kosongkan** | Batalkan semua pilihan. |
| Filter | "Hanya yang memblokir" dan kotak pencarian (cocok pada nama key dan property). |
| Tabel | Dikelompokkan per kategori. Klik kolom **✓** atau **klik-ganda** untuk toggle. |
| Panel bawah | Preview `key: lama → baru` yang akan ditulis. |
| Baris **Output** | Tujuan penulisan + tombol **TULIS FILE**. |

Perilaku yang sama dengan CLI tetap berlaku: preview selalu terlihat sebelum menulis, file input
tidak pernah diubah, dan setelah menulis ada 5 assertion self-verification. Kalau config
mendeklarasikan enkripsi, tombol **TULIS FILE** dimatikan dan alasannya ditampilkan.

Tak ada logika baru di GUI — `seb_gui.py` memanggil `Registry`, `scan`, `build_unlock`,
`write_output`, dan `verify` dari `seb_toggle.py`. Perbaikan di CLI otomatis berlaku di GUI.

## 5. Referensi CLI

```
seb_toggle.py <file.seb> [options]

  (tanpa flag)              pindai, lalu toggle interaktif
  --scan                    laporan saja, tanpa prompt
  --only-ignored            hanya 69 key legacy
  -c, --category <nama>     sempitkan menu toggle ke satu kategori registry
  -s, --set KEY=VALUE       toggle non-interaktif; bisa diulang
  -a, --add-missing         izinkan menulis key yang belum ada di file
  -y, --yes                 lewati prompt konfirmasi
  -o, --out <path>          default: <nama>.modified.seb
  --diff <other.seb>        bandingkan dua config, laporkan key yang berbeda
  --unlock-all              antrekan profil relaksasi penuh (screenshot, keyboard, VM, blokir aplikasi)
  --no-color                matikan warna ANSI
  -h, --help                bantuan
```

**Nama output default.** Tanpa `-o`: `--scan` tidak menulis apa pun; toggle menulis
`<nama>.modified.seb` di folder yang sama dengan input.

## 6. Alur interaktif

1. Laporan scan dicetak.
2. Menu toggle muncul, dikelompokkan per kategori, bernomor, menampilkan nilai sekarang dan
   restriksi yang dikontrol. Hanya key boolean yang benar-benar ada di file yang bisa di-toggle.
3. Masukkan pilihan di prompt `select>`, akhiri dengan `done`:

   | Input | Arti |
   |---|---|
   | `3` | satu entri |
   | `3,7,12` | beberapa entri |
   | `12-18` | rentang |
   | `all` | semua |
   | `none` | tidak ada |
   | `done` | selesai memilih, lanjut ke preview |

4. Preview diff dicetak: `key: old → new`, penambahan ditandai `[ADDITION]`.
5. Prompt `write? [y/N]` — `y` menulis file baru, `n` kembali ke menu tanpa menyentuh disk.

Artinya: `3` lalu `done` lalu `y` menulis satu perubahan; `3` lalu `done` lalu `n` membatalkan.

## 6b. Profil relaksasi — buka semua batasan

Satu perintah untuk membuka seluruh permukaan batasan: screenshot, tombol keyboard, menu OS,
virtual machine, screen sharing, fitur browser, clipboard, dan daftar blokir aplikasi.

```bash
python seb_toggle.py config.seb --unlock-all -y -o terbuka.seb
```

Atau interaktif — ketik `unlock` di prompt `select>`:

```
select> unlock
select> done
```

Preview tetap muncul sebelum menulis. Di `config (1)` profil ini mengubah **34 key**:
36 entri `prohibitedProcesses` dinonaktifkan, `enablePrintScreen` / `allowScreenSharing` /
`allowVirtualMachine` dibuka, `createNewDesktop` dimatikan.

**Ini bukan "set semua boolean ke True".** Beberapa key justru lebih permisif saat `False`, dan
beberapa bukan batasan sama sekali. Key berikut **sengaja tidak** dibalik ke `True`:

| Key | Alasan |
|---|---|
| `killExplorerShell` | `True` = membunuh Explorer = makin ketat. Nilai permisif `False`. |
| `URLFilterEnable`, `URLFilterEnableContentFilter` | `True` = menyalakan filter URL. Nilai permisif `False`. |
| `audioMute` | `True` = mute. Nilai permisif `False`. |
| `createNewDesktop`, `removeBrowserProfile`, `newBrowserWindowByLinkBlockForeign` | dibalik ke `False`, bukan `True`. |
| `touchOptimized`, `browserViewMode`, `sebMode`, `sebConfigPurpose` | enum, bukan bit. Tidak disentuh. |
| `audioSetVolumeLevel`, `allowedDisplaysMaxNumber`, `browserUserAgentWinDesktopMode` | nilai/level, bukan on-off. |
| `quitURLRestart`, `restartExamUseStartURL`, `setVmwareConfiguration`, `startURLAppendQueryParameter`, `useTemporaryDownUploadDirectory` | perilaku sesi, bukan batasan; arah ambigu — tidak ditebak. |

Key yang **absen** dari file tidak ditambahkan. Untuk memaksa nilai eksplisit pada key absen
(mis. `clipboardPolicy`, yang tidak ada di `config (1)`), pakai `-a`:

```bash
python seb_toggle.py config.seb -a -s clipboardPolicy=Allow -y -o out.seb
```

Menjalankan profil dua kali bersifat no-op — yang kedua melaporkan 0 perbedaan.

**Batas yang jujur.** 16 key ter-inversi di registry (mis. `downloadPDFFiles`) punya dua
pembacaan yang bertentangan: nama key bilang `True` = boleh, mapper C# bilang
`AllowPdfReader = !flag`. Profil ini memakai **semantik nama key** — sama dengan kolom
`EFFECTIVE` di laporan, dan konsisten dengan config ujian yang memang memblokir PDF. Verifikasi
hasilnya di klien SEB sebelum dipakai.

## 7. Pola nilai

- Boolean: `True` **permits**, `False` **restricts** (plan.md §4.1 — polaritas langsung dari
  nilai mentah; tabel inversi 16 mapper hanya metadata tampilan dan tidak dipakai logika toggle).
- Key enum (`sebMode`, `sebConfigPurpose`, `clipboardPolicy`, `allowVirtualMachine`,
  `browserViewMode`, `touchOptimized`) dirender sebagai label semantik: `Normal`/`Server`,
  `Exam`/`ConfigureClient`, `Allow`/`Block`/`Isolated`, `Allow`/`Deny`, `Windowed`/`FullScreen`,
  `Desktop`/`Mobile`.
- Nilai non-boolean (`startURL`, `proxies`, `prohibitedProcesses`, …) hanya ditampilkan, tidak
  bisa di-toggle.
- Key yang tidak ada di file **tidak** ditulis kecuali `-a` diberikan.

## 8. Exit code

| Kode | Arti |
|---|---|
| `0` | sukses |
| `1` | dibatalkan user (`n` di prompt, atau tidak ada perubahan yang dipilih) |
| `2` | penolakan — format tidak dikenali, key tidak ada tanpa `-a`, atau output == input |
| `3` | config mendeklarasikan enkripsi; berhenti sebelum fase toggle |
| `4` | assertion self-verifikasi gagal; file output dihapus |

## 9. Kasus yang ditolak bersih (tanpa traceback)

| Input | Perilaku |
|---|---|
| Container biner SEB (`plnd`/`pswd`/`pwcc`/`pkhs`/`phsk`) | exit `2`, "Out of scope - refusing." |
| Bukan plist / byte pendek | exit `2`, byte awal dilaporkan dalam hex |
| `useAsymmetricOnlyEncryption = True` | exit `3`, peringatan, berhenti sebelum toggle |
| `-o` menunjuk file input | exit `2`, menolak menulis di tempat |

## 10. Self-verification (5 assertion)

Sebelum melaporkan sukses, tool membuka ulang file output dan memastikan:

1. Setiap key yang dimaksud berubah ke nilai yang dimaksud.
2. Tidak ada key lain yang berubah — perbandingan set key dan nilai penuh terhadap input.
3. Tidak ada key ditambahkan kecuali `--add-missing` diberikan.
4. `startURL` dan semua key non-terpilih byte-identik nilainya.
5. Delta byte dan delta jumlah key dilaporkan.

Kalau salah satu gagal: output dihapus, assertion yang dilanggar dicetak, exit `4`.

## 11. Regenerasi registry

Hanya perlu kalau tree dekompilasi berubah. Butuh hasil dekompilasi SEB 3.10.2 (folder yang
memuat `SafeExamBrowser.Configuration/SafeExamBrowser.Configuration.ConfigurationData`):

```bash
python build_registry.py "D:/Downloads_Sorted_Codex/Folders/SEB/research/seb3.10.2_decompiled"
```

Output default `seb_registry.json` di cwd; override dengan `-o`. Angka yang harus keluar:

```
keys               : 217
categories         : 33
declarations       : 219      (categories menjumlah 219, keys 217 — selisih 2 by design)
dispatch edges     : 142
mapper methods     : 140
inverted methods   : 16
defaults leaves    : 149
global handlers    : 2
const_collisions   : 2
```

Selisih 217 vs 219 bukan bug: dua wire value (`"active"`, `"allowScreenSharing"`) masing-masing
dideklarasikan dua const di `Keys.cs`. `keys` memakai `setdefault` (satu kategori menang),
`categories` mencatat semua deklarasi, dan `const_collisions` menyimpannya supaya tetap
auditable.

## 12. Warna

Warna aktif hanya saat stdout adalah terminal. Kalau output di-pipe atau di-redirect, warna
otomatis mati — sehingga skrip yang mem-parsing output tidak terpengaruh.

| Kontrol | Efek |
|---|---|
| `--no-color` | matikan paksa |
| `NO_COLOR=1` | matikan (konvensi standar) |
| `SEB_FORCE_COLOR=1` | nyalakan paksa meski bukan TTY (hook debug) |

Status berwarna: `PERMISSIVE` hijau, `RESTRICTION` merah, `RESTRICTION SEB default` kuning,
`RESTRICTION author-imposed` merah tebal, `MODE-SELECTOR` cyan, `IGNORED-BY-3.10.2` abu-abu.

## 13. Troubleshooting

| Gejala | Penyebab | Aksi |
|---|---|---|
| `FileNotFoundError: seb_registry.json` | registry tidak ada di folder script | jalankan §11 |
| Tidak ada warna | output di-pipe, atau terminal tanpa VT | pakai `SEB_FORCE_COLOR=1`, atau abaikan |
| `REFUSED: ... not in the file` | key belum ada di config | tambahkan `-a` kalau memang mau menambah |
| Exit `3` pada `SebClientSettings.seb` | file itu mendeklarasikan enkripsi | sesuai desain — berhenti sebelum toggle |
| Angka registry berbeda | tree dekompilasi berbeda versi | bandingkan dengan daftar di §11 |

## 14. Verifikasi mandiri

Angka ground truth dan skrip reproduksi ada di `plan.md` §11. Untuk memastikan tool masih
benar setelah diubah:

```bash
python seb_toggle.py "config (1).seb" --scan -o a.seb
python seb_toggle.py --diff a.seb "config (1).seb"                  # harap: 0 key berbeda
python seb_toggle.py "config (1).seb" -s downloadPDFFiles=true -y -o b.seb
python seb_toggle.py --diff b.seb "config (1).seb"                  # harap: 1 (downloadPDFFiles)
python seb_toggle.py "config (1).seb" --only-ignored                # harap: 69 key
```
