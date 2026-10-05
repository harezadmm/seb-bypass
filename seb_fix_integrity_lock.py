#!/usr/bin/env python3
"""
SEB 3.10.2.920 — REAL integrity-lock bypass (ECMA-335 IL patcher)
=================================================================
Menggantikan patch_integrity_lock.py yang TIDAK BERFUNGSI.

Kenapa yang lama gagal:
  * Mencari nama method sebagai literal ASCII " method " + UTF-16LE,
    padahal .NET menyimpan nama method sebagai UTF-8 di heap #Strings.
  * Konstanta opcode salah semua (RET=0x2A bukan 0x05; CALL=0x28 bukan 0x0C;
    ldc.i4.1=0x17 bukan 0x7001; NOP=0x00 bukan 0x90).
  * Nama target "TryVerifyCodeSignature" ada di Configuration.dll TAPI
    bukan satu-satunya jalur; handler lock di Client.exe tak tersentuh.
  Hasil: 0 method dipatch, lock 10-15 menit tetap muncul.

Apa yang dipatch (jalur lock integrity):
  SafeExamBrowser.Client.exe
    IntegrityResponsibility.HandleApplicationIntegrityStatus  void -> ret
    IntegrityResponsibility.HandleSessionIntegrityStatus      void -> ret
    IntegrityResponsibility.HandleRuntimeIntegrityStatus      void -> ret
    IntegrityResponsibility.ScheduleIntegrityVerification     void -> ret  (matikan timer)
  SafeExamBrowser.exe
    IntegrityResponsibility.HandleRuntimeIntegrityStatus      void -> ret
    IntegrityResponsibility.StartIntegrityMonitoring          void -> ret
  SafeExamBrowser.Configuration.dll
    ApplicationIntegrityOperation.TryVerifyCodeSignature      bool -> ldc.i4.1; ret
    ApplicationIntegrityOperation.TryVerifyRuntimeIntegrity   bool -> ldc.i4.1; ret
    ApplicationIntegrityOperation.TryVerifySessionIntegrity   bool -> ldc.i4.1; ret

Body IL ditulis ulang di tempat (code size tetap, sisa byte diisi `ret` 0x2A
sehingga stream tetap sah: ret berulang) supaya offset section EH/LocalVarSig
tidak bergeser dan tidak perlu menulis ulang method header.
"""
import os
import struct
import sys
import zipfile
import shutil

# (file, owner, method, expected_return)
TARGETS = [
    ("SafeExamBrowser.Client.exe", "IntegrityResponsibility", "HandleApplicationIntegrityStatus", "void"),
    ("SafeExamBrowser.Client.exe", "IntegrityResponsibility", "HandleSessionIntegrityStatus",     "void"),
    ("SafeExamBrowser.Client.exe", "IntegrityResponsibility", "HandleRuntimeIntegrityStatus",    "void"),
    ("SafeExamBrowser.Client.exe", "IntegrityResponsibility", "ScheduleIntegrityVerification",   "void"),
    ("SafeExamBrowser.exe",        "IntegrityResponsibility", "HandleRuntimeIntegrityStatus",    "void"),
    ("SafeExamBrowser.exe",        "IntegrityResponsibility", "StartIntegrityMonitoring",        "void"),
    ("SafeExamBrowser.Configuration.dll", "IntegrityModule", "TryVerifyCodeSignature",    "bool"),
    ("SafeExamBrowser.Configuration.dll", "IntegrityModule", "TryVerifyRuntimeIntegrity", "bool"),
    ("SafeExamBrowser.Configuration.dll", "IntegrityModule", "TryVerifySessionIntegrity", "bool"),
]

RET = b"\x2A"            # ret
TRUE_RET = b"\x17\x2A"   # ldc.i4.1 ; ret
NOP = b"\x00"

ET = {0x01: "void", 0x02: "bool", 0x03: "char", 0x04: "i1", 0x05: "u1", 0x06: "i2",
      0x07: "u2", 0x08: "i4", 0x09: "u4", 0x0A: "i8", 0x0B: "u8", 0x0C: "r4",
      0x0D: "r8", 0x0E: "string", 0x0F: "ptr", 0x10: "byref", 0x11: "valuetype",
      0x12: "class", 0x13: "var", 0x14: "array", 0x15: "genericinst", 0x16: "typedbyref",
      0x18: "intptr", 0x19: "uintptr", 0x1B: "fnptr", 0x1C: "object", 0x1D: "szarray",
      0x1E: "mvar"}


def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def u32(d, o): return struct.unpack_from("<I", d, o)[0]


def rva_to_off(d, secs, rva):
    for va, vs, raw, rs in secs:
        if va <= rva < va + max(vs, rs):
            return raw + (rva - va)
    return None


def parse_pe(d):
    if d[:2] != b"MZ":
        return None
    pe = u32(d, 0x3C)
    if d[pe:pe + 4] != b"PE\x00\x00":
        return None
    nsec = u16(d, pe + 6)
    optsz = u16(d, pe + 20)
    opt = pe + 24
    dd = opt + (96 if u16(d, opt) == 0x10B else 112)
    secoff = opt + optsz
    secs = [(u32(d, secoff + i * 40 + 12), u32(d, secoff + i * 40 + 8),
             u32(d, secoff + i * 40 + 20), u32(d, secoff + i * 40 + 16)) for i in range(nsec)]
    return {"sections": secs, "cor_rva": u32(d, dd + 14 * 8)}


def parse_metadata(d, pe):
    cor = rva_to_off(d, pe["sections"], pe["cor_rva"])
    if cor is None:
        return None
    cor = rva_to_off(d, pe["sections"], u32(d, cor + 8))
    if cor is None or d[cor:cor + 4] != b"BSJB":
        return None
    p = cor + 16 + u32(d, cor + 12) + 2
    n = u16(d, p); p += 2
    st = {}
    for _ in range(n):
        off = u32(d, p); size = u32(d, p + 4); p += 8
        nm = b""
        while d[p] != 0:
            nm += bytes([d[p]]); p += 1
        p = (p + 1 + 3) & ~3
        st[nm.decode()] = (cor + off, size)
    return st


def parse_tables(d, st):
    ts, _ = st["#~"]
    p = ts + 6
    heap = d[p]; p += 2                      # heap sizes + reserved
    valid = struct.unpack_from("<Q", d, p)[0]; p += 16
    rows = {}
    for t in range(64):
        if valid & (1 << t):
            rows[t] = u32(d, p); p += 4
    str_sz = 4 if heap & 1 else 2
    guid_sz = 4 if heap & 2 else 2
    blob_sz = 4 if heap & 4 else 2

    def idx(t): return 4 if rows.get(t, 0) >= 65536 else 2

    def coded(ts_, bits):
        return 4 if max(rows.get(t, 0) for t in ts_) >= (1 << (16 - bits)) else 2

    sizes = {
        0x00: 2 + str_sz + 3 * guid_sz,
        0x01: coded([0, 0x1A, 0x23, 1], 2) + 2 * str_sz,
        0x02: 4 + 2 * str_sz + coded([2, 1, 0x1B], 2) + idx(4) + idx(6),
        0x03: idx(4),
        0x04: 2 + str_sz + blob_sz,
        0x05: idx(6),
        0x06: 4 + 4 + str_sz + blob_sz + idx(8),
    }
    offs = {}; cur = p
    for t in range(64):
        if t in rows:
            offs[t] = cur
            cur += rows[t] * sizes.get(t, 0)
    return {"rows": rows, "offs": offs, "sizes": sizes, "str_sz": str_sz, "blob_sz": blob_sz}


def method_body(d, secs, rva):
    o = rva_to_off(d, secs, rva)
    if o is None or o >= len(d):
        return None
    b = d[o]
    if (b & 3) == 2:
        return o, 1, b >> 2
    if (b & 3) == 3:
        return o, (u16(d, o) >> 12) * 4, u32(d, o + 4)
    return None


def str_at(d, streams, i):
    sb = streams["#Strings"][0]
    return d[sb + i:d.index(b"\x00", sb + i)].decode("utf-8", "replace")


def ret_type(d, streams, sigidx):
    base = streams["#Blob"][0]
    b = d[base + sigidx]
    if b & 0x80 == 0:
        ln = b; p = base + sigidx + 1
    elif b & 0xC0 == 0x80:
        ln = ((b & 0x3F) << 8) | d[base + sigidx + 1]; p = base + sigidx + 2
    else:
        ln = ((b & 0x1F) << 24) | (d[base + sigidx + 1] << 16) | \
             (d[base + sigidx + 2] << 8) | d[base + sigidx + 3]; p = base + sigidx + 4
    sg = d[p:p + ln]
    if not sg:
        return "?"
    cc = sg[0]; q = 1
    if cc & 0x10:  # generic
        q += 1 if sg[q] < 0x80 else 2
    q += 1 if sg[q] < 0x80 else 2  # param count
    if q >= len(sg):
        return "?"
    return ET.get(sg[q], "0x%02x" % sg[q])


def owners(d, streams, tbl):
    t2, row2 = tbl["offs"][2], tbl["sizes"][2]
    md_sz = 4 if tbl["rows"].get(6, 0) >= 65536 else 2
    out = []
    for i in range(tbl["rows"][2]):
        o = t2 + i * row2
        nm = str_at(d, streams, u32(d, o + 4) if tbl["str_sz"] == 4 else u16(d, o + 4))
        first = struct.unpack_from("<I", d, o + row2 - md_sz)[0] if md_sz == 4 else u16(d, o + row2 - 2)
        out.append((first, nm))
    out.sort()
    return out


def owner_of(tds, row):
    cur = None
    for first, nm in tds:
        if first <= row:
            cur = nm
        else:
            break
    return cur


def patch_dir(src_dir):
    report = []
    for fname, owner, mname, want_ret in TARGETS:
        path = os.path.join(src_dir, fname)
        if not os.path.isfile(path):
            report.append((fname, mname, "FILE-MISSING", ""))
            continue
        d = bytearray(open(path, "rb").read())
        pe = parse_pe(d)
        st = parse_metadata(d, pe)
        tbl = parse_tables(d, st)
        tds = owners(d, st, tbl)
        t6, row6 = tbl["offs"][6], tbl["sizes"][6]
        hits = []
        for i in range(tbl["rows"][6]):
            o = t6 + i * row6
            nm = str_at(d, st, u32(d, o + 8) if tbl["str_sz"] == 4 else u16(d, o + 8))
            if nm != mname:
                continue
            if owner_of(tds, i + 1) != owner:
                continue
            hits.append((i + 1, u32(d, o), u16(d, o + 10) if tbl["blob_sz"] == 2 else u32(d, o + 10)))
        if not hits:
            report.append((fname, mname, "NOT-FOUND", ""))
            continue
        for row, rva, sigi in hits:
            got = ret_type(d, st, sigi)
            if got != want_ret:
                report.append((fname, mname, "RET-MISMATCH", "expected %s got %s" % (want_ret, got)))
                continue
            mb = method_body(d, pe["sections"], rva)
            if not mb or mb[2] < 2:
                report.append((fname, mname, "NO-BODY", ""))
                continue
            body, iloff, csize = mb
            p = body + iloff
            want = RET if want_ret == "void" else TRUE_RET
            if bytes(d[p:p + len(want)]) == want:
                report.append((fname, mname, "ALREADY", "csize=%d" % csize))
                continue
            d[p:p + csize] = want + RET * (csize - len(want))
            open(path, "wb").write(bytes(d))
            report.append((fname, mname, "PATCHED", "%s csize=%d @0x%x" % (want_ret, csize, p)))
    return report


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("usage: seb_fix_integrity_lock.py <dir-dengan-7-binary>")
        return 2
    src = sys.argv[1]
    print("=" * 74)
    print("  SEB 3.10.2.920 — REAL integrity-lock bypass")
    print("=" * 74)
    rep = patch_dir(src)
    ok = 0
    for f, m, st, extra in rep:
        flag = "[+]" if st in ("PATCHED", "ALREADY") else "[!]"
        print("  %s %-38s %-30s %-11s %s" % (flag, f, m, st, extra))
        if st in ("PATCHED", "ALREADY"):
            ok += 1
    print("-" * 74)
    print("  %d/%d target beres." % (ok, len(rep)))
    return 0 if ok == len(rep) else 1


if __name__ == "__main__":
    sys.exit(main())
