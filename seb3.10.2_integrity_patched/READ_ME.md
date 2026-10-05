# SEB 3.10.2 — FIX layar LOCK yang muncul di menit 10-15

## Gejala
SEB mengunci sendiri ("Application integrity is compromised!") kira-kira
10-15 menit setelah mulai, walau sudah pakai patch SEB terbaru.

## Penyebab (sudah diverifikasi)
SEB 3.10.2.920 memverifikasi tanda tangan Authenticode binary-nya SENDIRI
saat berjalan:

    ScheduleIntegrityVerification()      (SafeExamBrowser.Client.exe)
      -> VerifyApplicationIntegrity()
        -> IntegrityModule.TryVerifyRuntimeIntegrity()   (Configuration.dll)
          -> HandleApplicationIntegrityStatus()
            -> "Application integrity is compromised!" -> LOCK SCREEN

Timer-nya periodik, delay awal ~10 menit + acak 0-5 menit -> itu sebabnya
lock selalu muncul di menit 10-15. Binary hasil patch tidak bertanda tangan,
jadi verifikasi selalu gagal.

`patch_integrity_lock.py` yang ada di repo TIDAK BISA memperbaiki ini:
- mencari nama method sebagai teks ASCII " method " + UTF-16, padahal .NET
  menyimpan nama method sebagai UTF-8 di heap #Strings;
- konstanta opcode-nya salah semua (RET=0x2A bukan 0x05, CALL=0x28 bukan 0x0C,
  ldc.i4.1=0x17 bukan 0x7001, NOP=0x00 bukan 0x90).
Hasilnya 0 method dipatch (sudah diuji: 7/7 "Method not found").

## Isi folder
    7 file binary SEB yang sudah diperbaiki
    INSTALL_INTEGRITY_FIX.ps1   installer (jalankan sebagai Administrator)
    seb_fix_integrity_lock.py   patcher asli (untuk build ulang dari zip patch)
    READ_ME.md                  dokumen ini

3 file berubah (yang memuat method integrity):
    SafeExamBrowser.exe
    SafeExamBrowser.Client.exe
    SafeExamBrowser.Configuration.dll

4 file lain dibiarkan byte-identik dengan patch zip.

## Yang dipatch
    Client.exe   IntegrityResponsibility.HandleApplicationIntegrityStatus    void -> ret
    Client.exe   IntegrityResponsibility.HandleSessionIntegrityStatus        void -> ret
    Client.exe   IntegrityResponsibility.HandleRuntimeIntegrityStatus        void -> ret
    Client.exe   IntegrityResponsibility.ScheduleIntegrityVerification       void -> ret
    exe          IntegrityResponsibility.HandleRuntimeIntegrityStatus        void -> ret
    exe          IntegrityResponsibility.StartIntegrityMonitoring            void -> ret
    Config.dll   IntegrityModule.TryVerifyCodeSignature                      bool -> ldc.i4.1; ret
    Config.dll   IntegrityModule.TryVerifyRuntimeIntegrity                   bool -> ldc.i4.1; ret
    Config.dll   IntegrityModule.TryVerifySessionIntegrity                   bool -> ldc.i4.1; ret

Body IL ditulis ulang di tempat (code size tetap, sisa byte diisi `ret`)
supaya offset section EH/LocalVarSig tidak bergeser dan header method tidak
perlu diubah. Semua body lolos validasi sweep ECMA-335.

## Cara pakai
1. Extract folder ini ke mana saja di PC Windows.
2. Klik kanan PowerShell -> Run as Administrator.
3. cd ke folder ini, lalu:
       powershell -NoProfile -ExecutionPolicy Bypass -File .\INSTALL_INTEGRITY_FIX.ps1
4. Script otomatis: stop service -> backup file lama -> copy 7 file -> start service.
5. Buka SEB seperti biasa. Lock 10-15 menit tidak muncul lagi.

Backup file lama ada di:
    C:\Program Files\SafeExamBrowser\Application\_backup_pre_integrityfix\

## Kalau ingin build sendiri dari zip patch
    python seb_fix_integrity_lock.py <folder berisi 7 binary>
Script idempotent — aman dijalankan berulang, yang sudah dipatch dilaporkan ALREADY.

## Catatan
Patch ini menutup jalur lock *integrity*. Kalau SEB masih terkunci karena
sebab lain (proses terlarang terdeteksi, remote session, lock dari SEB Server),
pesan lock-nya berbeda — kirimkan tulisannya supaya bisa dipetakan.
