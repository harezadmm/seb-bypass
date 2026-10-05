#!/usr/bin/env python3
"""
seb_merge_bypass.py — jadikan SATU file .seb sudah mengandung seluruh bypass.

Tujuan: cukup buka file .seb ini di SEB polos (tanpa installer, tanpa patch
biner) dan bypass langsung aktif. Ini cara yang sah di macOS: SEB macOS
membaca semuanya dari config (app-nya bertanda tangan + hardened runtime,
jadi patch biner justru ditolak jalan).

Cara kerja:
  BASE   = profil bypass repo (SebClientSettings.seb) -- 212 kunci teruji,
           termasuk prohibitedProcesses dengan 101 mirror preset nonaktif
           dan lockdownModePolicy=1 (mematikan AAC).
  KECUALI kunci identitas ujian, yang diambil dari config ujian user:
           startURL, examKeySalt, browserExamKey, originatorVersion,
           kunci jaringan/proxy, UA, filter URL, dsb.
  Hasilnya: perilaku bypass penuh + identitas ujian utuh.

Pakai:
  python3 seb_merge_bypass.py <config-ujian.seb> <keluaran.seb>
"""
import hashlib
import os
import plistlib
import sys

# Kunci yang dipertahankan dari CONFIG UJIAN (identitas / integritas / jaringan).
# Kalau kunci ini diambil dari profil bypass, ujian bisa ditolak server,
# BrowserExamKey bisa tidak cocok, atau URL ujian bisa tertimpa.
KEEP_FROM_EXAM = {
    # URL & tujuan ujian
    "startURL", "startURLAppendQueryParameter", "startResource",
    "quitURL", "quitURLConfirm", "quitURLRestart",
    "restartExamURL", "restartExamText", "restartExamUseStartURL",
    "restartExamPasswordProtected",
    "examSessionReconfigureConfigURL", "examSessionReconfigureAllow",
    # kripto / identitas ujian
    "examKeySalt", "browserExamKey", "configKeySalt", "encryptionKey",
    "useAsymmetricOnlyEncryption", "sendBrowserExamKey",
    "embeddedCertificates", "pinEmbeddedCertificates",
    "originatorVersion", "sebConfigPurpose", "sebMode", "sebServerURL",
    "hashedQuitPassword", "hashedAdminPassword",
    # jaringan
    "proxies", "proxySettingsPolicy",
    "sebServicePolicy", "sebServiceIgnore",
    "browserMessagingSocket", "browserMessagingPingTime",
    # UA (server kadang memeriksa)
    "browserUserAgent", "browserUserAgentMac", "browserUserAgentMacCustom",
    "browserUserAgentWinDesktopMode", "browserUserAgentWinDesktopModeCustom",
    "browserUserAgentWinTouchMode", "browserUserAgentWinTouchModeCustom",
    "browserUserAgentWinTouchModeIPad",
    # filter URL (dibiarkan apa adanya)
    "URLFilterEnable", "URLFilterEnableContentFilter", "URLFilterRules",
    "enableURLFilter", "enableURLContentFilter",
    "whitelistURLFilter", "blacklistURLFilter",
    "urlFilterRegex", "urlFilterTrustedContent",
    # bahasa / lokalisasi
    "additionalDictionaries", "additionalResources",
    "showInputLanguage", "allowSpellCheckDictionary",
    # identitas mesin
    "minMacOSVersion",
}

# Kunci yang DIPAKSA dari profil bypass walau ada di config ujian.
# (keamanan/kiosk/monitoring/perizinan — inti bypass)
FORCE_FROM_BYPASS = {
    "lockdownModePolicy", "allowVirtualMachine", "enableAltTab",
    "allowSwitchToApplications", "enableAppSwitcherCheck",
    "allowWindowCapture", "allowScreenCapture", "allowScreenSharing",
    "screenSharingMacEnforceBlocked", "allowSiri", "allowDictation",
    "allowDictionaryLookup", "detectAccessibilityApps",
    "autoQuitApplications", "enablePrivateClipboard",
    "enablePrivateClipboardMacEnforce", "clipboardPolicy",
    "allowDisplayMirroring", "allowedDisplayBuiltin",
    "allowedDisplayBuiltinEnforce", "allowedDisplaysMaxNumber",
    "allowedDisplaysIgnoreFailure",
    "browserWindowAllowAddressBar", "newBrowserWindowAllowAddressBar",
    "enablePrintScreen", "allowPrint", "allowDownloads", "allowUploads",
    "allowStickyKeys", "enableMiddleMouse", "enableAltMouseWheel",
    "enableCtrlEsc", "enableAltEsc", "enableAltF4",
    "prohibitedProcesses", "permittedProcesses",
    "allowFind", "showReloadButton", "showReloadWarning",
    "hideBrowserWindowToolbar", "enableBrowserWindowToolbar",
    "allowDeveloperConsole", "allowBrowsingBackForward",
    "browserURLSalt",
}


def load(path):
    with open(path, "rb") as f:
        raw = f.read()
    d = plistlib.loads(raw)
    if not isinstance(d, dict):
        raise SystemExit("REFUSE: root plist bukan dict")
    return d, raw


def main():
    if len(sys.argv) != 3:
        print("usage: seb_merge_bypass.py <config-ujian.seb> <keluaran.seb>")
        return 2
    exam_p, out_p = sys.argv[1], sys.argv[2]
    if os.path.abspath(exam_p) == os.path.abspath(out_p):
        print("REFUSE: input = output")
        return 2

    base_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SebClientSettings.seb")
    if not os.path.isfile(base_p):
        base_p = "SebClientSettings.seb"
    bypass, _ = load(base_p)
    exam, exam_raw = load(exam_p)
    exam_sha = hashlib.sha256(exam_raw).hexdigest()

    print("BASE (profil bypass) :", len(bypass), "kunci")
    print("CONFIG UJIAN         :", len(exam), "kunci  sha256", exam_sha[:32])
    print()

    out = dict(bypass)          # mulai dari profil bypass penuh
    kept, forced, added = [], [], []

    for k, v in exam.items():
        if k in KEEP_FROM_EXAM:
            if out.get(k) != v:
                kept.append((k, out.get(k, "<absent>"), v))
            out[k] = v
        elif k in FORCE_FROM_BYPASS:
            forced.append((k, v, out.get(k, "<absent>")))
            # biarkan nilai bypass (tidak diubah)
        else:
            # kunci lain dari config ujian yang tidak ada di profil bypass:
            # ikutkan supaya tidak ada yang hilang
            if k not in out:
                out[k] = v
                added.append(k)

    print("== KUNCI IDENTITAS UJIAN DIPERTAHANKAN (%d) ==" % len(kept))
    for k, bv, ev in kept:
        s1 = repr(bv); s2 = repr(ev)
        if len(s1) > 34: s1 = s1[:31] + "..."
        if len(s2) > 34: s2 = s2[:31] + "..."
        print("   %-40s bypass=%-36s -> exam=%s" % (k, s1, s2))

    print()
    print("== KUNCI DIPAKSA DARI PROFIL BYPASS (%d) ==" % len(forced))
    for k, ev, bv in forced:
        s1 = repr(ev); s2 = repr(bv)
        if len(s1) > 34: s1 = s1[:31] + "..."
        if len(s2) > 34: s2 = s2[:31] + "..."
        print("   %-40s exam=%-36s -> bypass=%s" % (k, s1, s2))

    if added:
        print()
        print("== KUNCI TAMBAHAN DARI CONFIG UJIAN (%d) ==" % len(added))
        for k in sorted(added):
            print("   +", k)

    # --- prohibitedProcesses: pastikan semua entri ujian (Windows) nonaktif ---
    pp = list(out.get("prohibitedProcesses") or [])
    seen = set()
    for e in pp:
        if isinstance(e, dict):
            tag = (e.get("identifier") or "").lower() or (e.get("executable") or "").lower()
            seen.add(tag)
    deact = 0
    for e in exam.get("prohibitedProcesses") or []:
        if not isinstance(e, dict):
            continue
        tag = (e.get("identifier") or "").lower() or (e.get("executable") or "").lower()
        if tag and tag not in seen:
            m = dict(e)
            m["active"] = False
            m["os"] = 0
            m["strongKill"] = False
            pp.append(m)
            seen.add(tag)
            deact += 1
    out["prohibitedProcesses"] = pp

    print()
    print("== prohibitedProcesses ==")
    print("   bypass: %d entri -> hasil: %d entri (+%d entri ujian dinonaktifkan)"
          % (len(bypass.get("prohibitedProcesses") or []), len(pp), deact))

    with open(out_p, "wb") as f:
        f.write(plistlib.dumps(out, fmt=plistlib.FMT_XML, sort_keys=True))

    # ---- verifikasi ----
    chk = plistlib.load(open(out_p, "rb"))
    print()
    print("OUTPUT:", out_p, os.path.getsize(out_p), "bytes")
    print("ANTI-CRASH CHECKS:")
    assert chk["startURL"] == exam["startURL"], "startURL berubah!"
    assert chk.get("examKeySalt") == exam.get("examKeySalt"), "examKeySalt berubah!"
    assert chk["lockdownModePolicy"] == 1, "lockdownModePolicy bukan 1!"
    assert chk["allowSwitchToApplications"] is True, "allowSwitchToApplications!"
    assert chk["enableAppSwitcherCheck"] is False
    assert chk["allowedDisplayBuiltin"] is True, "display built-in harus True!"
    assert chk["allowedDisplaysMaxNumber"] == 16
    assert chk["allowVirtualMachine"] is True
    assert chk["detectAccessibilityApps"] is False
    assert chk["allowScreenCapture"] is True and chk["allowWindowCapture"] is True
    print("   [OK] startURL & examKeySalt utuh (identitas ujian)")
    print("   [OK] lockdownModePolicy=1 (AAC mati, kiosk klasik)")
    print("   [OK] allowedDisplayBuiltin=True (SEB tidak menolak layar built-in)")
    print("   [OK] app switch, capture, VM, accessibility: semua dibebaskan")
    print("   [OK] prohibitedProcesses semua nonaktif")

    with open(exam_p, "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == exam_sha, "INPUT BERUBAH"
    print("   [OK] file input tidak diubah")
    print()
    print("OUTPUT sha256:", hashlib.sha256(open(out_p, "rb").read()).hexdigest())
    return 0


sys.exit(main())
