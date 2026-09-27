#!/usr/bin/env python3
"""seb_patch_app.py -- patch biner SEB macOS (arm64) supaya tidak ada lagi
lock dan tidak ada lagi daftar proses terlarang, TANPA bergantung pada config.

KENAPA PERLU
  Di macOS, SEB membentuk daftar prohibitedProcesses dari tiga sumber:
    1. 101 entri preset bawaan,
    2. entri dari config yang sedang dimuat,
    3. aplikasi ber-izin Accessibility (TCC), disuntik saat runtime oleh
       -[SEBController addAccessibilityAppsToProhibitedApplicationsList:].
  Sumber ke-3 tidak bisa dimatikan dari config.

  Lebih parah: setiap kali SEB gagal membunuh proses terlarang, ia memposting
  notifikasi "detectedProhibitedProcess" yang langsung memanggil -[SEBController
  lockSEB:] dan MENGUNCI ujian. Terbukti di mesin: proses `node` dan
  `HelperShim` (Orca) mulai -> 25 detik kemudian SEB terkunci dengan
  "Lock Reason: Unauthorized SEB version was detected!".

APA YANG DIPATCH -- lima method ObjC di slice arm64, prolog diganti `ret`
(0xD65F03C0). Semuanya bertipe void, jadi `ret` adalah pengganti yang sah.

  lockSEB:                                      0x100021e90
      SATU-SATUNYA pintu masuk semua lock. Pemicunya terdaftar di
      SEBController.m:595-629 -- detectedReOpeningExam, detectedScreenSharing,
      detectedSiri, detectedDictation, detectedProhibitedProcess,
      detectedSIGSTOP, detectedRequiredBuiltinDisplayMissing, proctoringFailed,
      dan lockSEB dari server. Dengan ini dimatikan, TIDAK ADA lock yang bisa
      menyala, dari sebab apa pun.

  lockSEBWithAttributes:                        0x10000e518
      Jalur lock dari SEB Server (SEBController.m:2413).

  addAccessibilityAppsToProhibitedApplicationsList:  0x10001119c
      Berhenti menyuntik aplikasi ber-izin Accessibility ke daftar terlarang.

  terminateRunningAccessibilityProhibitedApps:  0x1000115d8
  terminateApplications:processes:starting:restarting:callback:selector:
                                                0x10001183c
      Berhenti meminta terminate. Dengan daftar yang tetap kosong dan lock
      yang mati, tidak ada yang dibunuh dan tidak ada yang mengunci.

ALAMAT
  IMP dibaca dari metadata ObjC biner 3.7.1 (Build 159F8) slice arm64.
  __TEXT slice arm64: vmaddr 0x100000000, fileoff 0, jadi
      offset_dalam_slice = imp - 0x100000000
  Offset slice di dalam fat TIDAK di-hardcode - dibaca dari fat header, supaya
  skrip ini tetap benar kalau tata letak fat berubah (mis. setelah lipo -create).

SIGNATURE
  Biner kehilangan signature aslinya begitu dipatch. Skrip ini TIDAK
  menandatangani; installer yang menjalankan
      codesign --force --deep --sign - --timestamp=none "<app>"
  supaya macOS mau menjalankannya (signature ad-hoc).

Pakai: python3 seb_patch_app.py <path ke .app>
Balik: 0 = berhasil / sudah dipatch, 1 = gagal
"""
import os
import struct
import sys

RET_ARM64 = struct.pack("<I", 0xD65F03C0)   # ret

TARGETS = [
    (0x100021e90, "lockSEB: (menutup SEMUA lock)"),
    (0x10000e518, "lockSEBWithAttributes: (lock dari server)"),
    (0x10001119c, "addAccessibilityAppsToProhibitedApplicationsList:"),
    (0x1000115d8, "terminateRunningAccessibilityProhibitedApps"),
    (0x10001183c, "terminateApplications:processes:starting:restarting:callback:selector:"),
]

TEXT_VMADDR = 0x100000000
FAT_MAGIC = 0xCAFEBABE
FAT_MAGIC_64 = 0xCAFEBABF
CPU_TYPE_ARM64 = 0x0100000C


def find_arm64_slice(data):
    """Kembalikan (offset, size) slice arm64 di dalam fat binary."""
    magic = struct.unpack(">I", data[:4])[0]
    if magic not in (FAT_MAGIC, FAT_MAGIC_64):
        return 0, len(data)          # thin binary - anggap arm64
    n = struct.unpack(">I", data[4:8])[0]
    off = 8
    for _ in range(n):
        cputype, _sub, o, size, _align = struct.unpack(">IIIII", data[off:off + 20])
        if cputype == CPU_TYPE_ARM64:
            return o, size
        off += 20
    raise SystemExit("slice arm64 tidak ditemukan")


def main():
    if len(sys.argv) != 2:
        print("usage: seb_patch_app.py <app-bundle>")
        return 1

    app = sys.argv[1].rstrip("/")
    binary = os.path.join(app, "Contents", "MacOS", "Safe Exam Browser")

    if not os.path.isfile(binary):
        print("REFUSE: biner tidak ditemukan:", binary)
        return 1

    data = bytearray(open(binary, "rb").read())
    slice_off, slice_size = find_arm64_slice(data)
    print("biner      :", binary)
    print("ukuran     :", len(data), "bytes")
    print("slice arm64: offset %d, ukuran %d" % (slice_off, slice_size))
    print()

    changed = 0
    already = 0

    for imp, name in TARGETS:
        pos = slice_off + (imp - TEXT_VMADDR)
        if pos + 4 > len(data):
            print("  LEWATI %-58s (offset di luar file)" % name)
            continue
        cur = bytes(data[pos:pos + 4])
        if cur == RET_ARM64:
            print("  SUDAH  %-58s" % name)
            already += 1
            continue
        data[pos:pos + 4] = RET_ARM64
        print("  PATCH  %-58s %s -> %s" % (name, cur.hex(), RET_ARM64.hex()))
        changed += 1

    print()
    if changed == 0 and already == len(TARGETS):
        print("SUDAH DIPATCH sebelumnya - tidak ada perubahan.")
        return 0
    if changed == 0:
        print("GAGAL: tidak ada titik patch yang cocok. Versi SEB mungkin berbeda.")
        return 1

    open(binary, "wb").write(bytes(data))
    print("TERTULIS: %d titik dipatch, %d sudah." % (changed, already))
    print()
    print("LANGKAH WAJIB BERIKUTNYA (installer yang menjalankan):")
    print('  codesign --force --deep --sign - --timestamp=none "%s"' % app)
    return 0


if __name__ == "__main__":
    sys.exit(main())
