#!/usr/bin/env python3
"""seb_patch_app.py -- patch biner SEB macOS (arm64) supaya daftar proses
terlarang tidak pernah berlaku, TANPA bergantung pada config apa pun.

KENAPA
  Di macOS, daftar prohibitedProcesses dibentuk dari beberapa sumber:
    1. entri preset bawaan SEB (101 entri macOS),
    2. entri dari config yang sedang dimuat,
    3. aplikasi yang punya izin Accessibility (TCC) - disuntik saat runtime
       oleh -[SEBController addAccessibilityAppsToProhibitedApplicationsList:].
  Sumber ke-3 tidak bisa dimatikan dari config kalau config yang menang tidak
  memuat detectAccessibilityApps. Karena itu masalah ini berulang setiap kali
  file config berganti.

APA YANG DIPATCH
  Tiga method ObjC di slice arm64 diganti prolog-nya dengan `ret` (0xD65F03C0),
  sehingga seluruhnya menjadi no-op:

    -[SEBController addAccessibilityAppsToProhibitedApplicationsList:]  (v16@0:8)
    -[SEBController terminateRunningAccessibilityProhibitedApps]        (v16@0:8)
    -[SEBController terminateApplications:processes:starting:restarting:callback:selector:]
                                                                       (v56@0:8...)

  Ketiganya bertipe void, jadi `ret` langsung adalah pengganti yang sah.
  Setelah ini, apa pun config yang dibuka, tidak ada aplikasi yang disuntik ke
  daftar terlarang dan tidak ada yang diminta terminate.

ALAMAT
  IMP diambil dari metadata ObjC biner 3.7.1 (Build 159F8) slice arm64:

    0x10001119c   addAccessibilityAppsToProhibitedApplicationsList:
    0x1000115d8   terminateRunningAccessibilityProhibitedApps
    0x10001183c   terminateApplications:processes:starting:restarting:callback:selector:

  __TEXT slice arm64: vmaddr 0x100000000, fileoff 0, jadi
    offset_dalam_slice = imp - 0x100000000
  Offset slice di dalam fat TIDAK di-hardcode - dibaca dari fat header, supaya
  skrip ini tetap benar kalau tata letak fat berubah (mis. setelah lipo -create).

SIGNATURE
  Biner kehilangan signature aslinya (TeamIdentifier 6F38DNSC7X) begitu dipatch.
  Skrip ini TIDAK menandatangani; installer yang menjalankan
    codesign --force --deep --sign - --timestamp=none "<app>"
  untuk memberi signature ad-hoc, supaya macOS mau menjalankannya.

  Konsekuensi: hardened runtime dan entitlements asli hilang. Gatekeeper bisa
  meminta "Open Anyway" satu kali.

Pakai: python3 seb_patch_app.py <path ke .app>
Balik: 0 = berhasil / sudah dipatch, 1 = gagal
"""
import os
import struct
import sys

RET_ARM64 = struct.pack("<I", 0xD65F03C0)   # ret

TARGETS = [
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
        # bukan fat - anggap thin arm64
        return 0, len(data)
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
        inner = imp - TEXT_VMADDR
        pos = slice_off + inner
        if pos + 4 > len(data):
            print("  LEWATI %-58s (offset di luar file)" % name)
            continue
        cur = bytes(data[pos:pos + 4])
        if cur == RET_ARM64:
            print("  SUDAH %-58s" % name)
            already += 1
            continue
        data[pos:pos + 4] = RET_ARM64
        print("  PATCH %-58s %s -> %s" % (name, cur.hex(), RET_ARM64.hex()))
        changed += 1

    if changed == 0 and already == len(TARGETS):
        print()
        print("SUDAH DIPATCH sebelumnya - tidak ada perubahan.")
        return 0

    if changed == 0:
        print()
        print("GAGAL: tidak ada titik patch yang cocok. Versi SEB mungkin berbeda.")
        return 1

    open(binary, "wb").write(bytes(data))
    print()
    print("TERTULIS: %d titik dipatch, %d sudah." % (changed, already))
    print()
    print("LANGKAH WAJIB BERIKUTNYA (installer yang menjalankan):")
    print('  codesign --force --deep --sign - --timestamp=none "%s"' % app)
    print("Tanpa re-sign, macOS akan menolak menjalankannya.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
