# SEB 3.10.2 — FIX layar LOCK 10-15 menit + pemulihan Startup Error

## Dua masalah, satu paket

### 1. Lock tiap 10-15 menit
SEB 3.10.2.920 memverifikasi tanda tangan Authenticode binary-nya SENDIRI
saat berjalan, berulang tiap ~10 menit + acak 0-5 menit:

    ScheduleIntegrityVerification()               (Client.exe)
      -> VerifyApplicationIntegrity()
        -> IntegrityModule.TryVerifyRuntimeIntegrity()   (Configuration.dll)
          -> HandleApplicationIntegrityStatus()
            -> "Application integrity is compromised!" -> LOCK

Binary hasil patch tidak bertanda tangan, jadi verifikasi selalu gagal.

### 2. "Startup Error" / InvalidProgramException (bug fix v1)
Fix v1 menulis `ret` ke SELURUH body method `bool` yang punya blok try/catch
(`TryVerifyCodeSignature`, `TryVerifyRuntimeIntegrity`). Handler catch wajib
diawali `pop`/`stloc`; `ret` di dalamnya = IL tidak valid:

    System.InvalidProgramException:
    Common Language Runtime detected an invalid program.
      at Integrity.IntegrityModule.TryVerifyCodeSignature(Boolean&)
      at Bootstrap.ApplicationIntegrityOperation.Perform()

## Cara kerja fix v2 (IL-safe)
HANYA method PEMANGGIL yang **void** dan **tanpa blok try/catch** diganti
`ret`. Method verifier `bool` yang ber-EH TIDAK disentuh sama sekali.
Mematikan pemanggil sudah cukup: handler tak pernah dipanggil, timer tak
pernah dijadwalkan. Setiap target diverifikasi `void` + `EH=0` SEBELUM
ditulis — kalau tidak memenuhi, dilewati, bukan dirusak.

Yang dipatch (13 method, semua void & EH=0):
    SafeExamBrowser.exe
      ApplicationIntegrityOperation.VerifyCodeSignature   <- pemicu startup
      IntegrityResponsibility.HandleRuntimeIntegrityStatus
      IntegrityResponsibility.StartIntegrityMonitoring
    SafeExamBrowser.Client.exe
      IntegrityResponsibility.VerifyApplicationIntegrity
      IntegrityResponsibility.VerifySessionIntegrity
      IntegrityResponsibility.HandleApplicationIntegrityStatus
      IntegrityResponsibility.HandleSessionIntegrityStatus
      IntegrityResponsibility.HandleRuntimeIntegrityStatus
      IntegrityResponsibility.ScheduleIntegrityVerification
      IntegrityResponsibility.StartIntegrityMonitoring
      IntegrityResponsibility.UpdateSessionIntegrity
      IntegrityResponsibility.Assume
      IntegrityResponsibility.Timer_Elapsed

`SafeExamBrowser.Configuration.dll` di paket ini = **ASLI (unpatched)**,
supaya instalasi yang rusak akibat v1 ikut dipulihkan.

## Cara pakai
1. Extract folder ini di PC Windows.
2. PowerShell **as Administrator**, cd ke folder ini:
       powershell -NoProfile -ExecutionPolicy Bypass -File .\INSTALL_INTEGRITY_FIX.ps1
3. Script: stop service -> backup -> copy -> start service.
4. Buka SEB. Startup Error hilang, lock 10-15 menit tidak muncul.

Backup: `C:\Program Files\SafeExamBrowser\Application\_backup_pre_integrityfix\`

## Build sendiri dari zip patch
    python seb_fix_integrity_lock.py <folder berisi 7 binary>
Idempotent — aman dijalankan berulang.

## Batas kejujuran
Verifikasi di sini **statis** (struktur IL + korektnes patch), bukan menjalankan
SEB. Uji akhir ada di PC Windows. Kalau masih ada lock, kirim tulisan persis
di layar lock-nya — lock dari sebab lain (proses terlarang, remote session,
SEB Server) punya pesan berbeda.
