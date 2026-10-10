#!/usr/bin/env python3
"""
SEB Config Bypass Studio
========================
GUI untuk membuka config.seb apa pun, mendeteksi bagian yang terkunci,
memilih bypass yang diinginkan, lalu menulis file .seb baru.

  python3 seb_bypass_gui.py                      # buka GUI
  python3 seb_bypass_gui.py --cli IN.seb OUT.seb --preset recommended
  python3 seb_bypass_gui.py --cli IN.seb OUT.seb --list
  python3 seb_bypass_gui.py --cli IN.seb OUT.seb --keys allowSwitchToApplications,allowVirtualMachine

File input TIDAK PERNAH diubah. Output ditulis sebagai plist XML.
Tanpa dependensi luar selain Python 3 (tkinter bawaan untuk GUI).
"""
import argparse
import hashlib
import os
import plistlib
import sys

VERSION = "1.0.0"

# ============================================================================
# KATEGORI
# ============================================================================
CATEGORIES = [
    "Lock Screen & Integritas",
    "Kiosk & Sistem",
    "Ganti Aplikasi & Tombol",
    "Screenshot & Capture",
    "Clipboard",
    "Proses & Monitoring",
    "Layar (Display)",
    "Browser & Navigasi",
    "Download / Upload / Print",
    "Password & Keluar",
    "Sensor & Privasi",
    "URL Filter",
]

# risk: low = rekomendasi, medium = mengubah perilaku/hash, high = bisa
# mempengaruhi integritas ujian (mis. melepas filter URL)
RULES = []


def R(key, cat, label, why, value, locked, risk="low", plat="both", action="set"):
    RULES.append({
        "key": key, "cat": cat, "label": label, "why": why,
        "value": value, "locked": locked, "risk": risk,
        "plat": plat, "action": action,
    })


# ---------------------------------------------------------------- Lock Screen
R("lockdownModePolicy", "Lock Screen & Integritas",
  "Matikan AAC, pakai kiosk klasik",
  "Di macOS 12.1+ SEB memakai AAC (lockdown tingkat OS). Dalam mode AAC, "
  "kunci bypass lain (Cmd+Tab, Alt+Tab) DIABAIKAN. Nilai 1 = EnforceClassic.",
  1, {"absent": True, "ne": 1}, risk="low", plat="mac")
R("allowVirtualMachine", "Lock Screen & Integritas",
  "Izinkan jalan di Virtual Machine",
  "Tanpa ini SEB menolak start di Parallels/VMware/VirtualBox.",
  True, {"eq": False}, risk="low")
R("enableCursorVerification", "Lock Screen & Integritas",
  "Matikan verifikasi kursor",
  "Perubahan kursor memicu lock screen (jalur Sentinel_CursorChanged).",
  False, {"eq": True}, risk="low", plat="win")
R("enableSessionVerification", "Lock Screen & Integritas",
  "Matikan verifikasi sesi",
  "Aktif hanya bila ada password quit; memicu lock integritas sesi.",
  False, {"eq": True}, risk="low", plat="win")
R("allowStickyKeys", "Lock Screen & Integritas",
  "Sticky keys jangan memicu lock",
  "Sticky keys berubah -> lock screen (Sentinel_StickyKeysChanged).",
  True, {"eq": False}, risk="low", plat="win")
R("disableSessionChangeLockScreen", "Lock Screen & Integritas",
  "Jangan lock saat switch user / session",
  "Lock saat user lock/switch session dimatikan.",
  True, {"eq": False}, risk="low", plat="win")
R("sebServiceIgnore", "Lock Screen & Integritas",
  "Abaikan service (matikan monitoring ease-of-access)",
  "Monitoring ease-of-access adalah salah satu jalur lock screen.",
  True, {"eq": False}, risk="low", plat="win")

# ---------------------------------------------------------------------- Kiosk
R("killExplorerShell", "Kiosk & Sistem",
  "Jangan bunuh Windows Explorer",
  "Explorer dibiarkan hidup (taskbar/desktop tetap ada).",
  False, {"eq": True}, risk="medium", plat="win")
R("showTaskBar", "Kiosk & Sistem", "Tampilkan taskbar",
  "Taskbar SEB ditampilkan.", True, {"eq": False}, risk="low")
R("showTime", "Kiosk & Sistem", "Tampilkan jam",
  "Jam di taskbar SEB.", True, {"eq": False}, risk="low")
R("showSideMenu", "Kiosk & Sistem", "Tampilkan side menu",
  "Menu samping SEB.", True, {"eq": False}, risk="low")
R("enableStartMenu", "Kiosk & Sistem", "Izinkan Start Menu",
  "Start menu Windows diizinkan.", True, {"eq": False}, risk="medium", plat="win")
R("enableWindowsUpdate", "Kiosk & Sistem", "Jangan blokir Windows Update",
  "Windows Update tidak diblokir.", True, {"eq": False}, risk="low", plat="win")
R("createNewDesktop", "Kiosk & Sistem",
  "Jangan pakai desktop terpisah (klasik)",
  "SEB tidak membuat desktop Windows terpisah. Bisa mengubah perilaku kiosk.",
  False, {"eq": True}, risk="high", plat="win")

# --------------------------------------------------- Ganti aplikasi & tombol
R("allowSwitchToApplications", "Ganti Aplikasi & Tombol",
  "Izinkan pindah aplikasi (Cmd+Tab / Alt+Tab)",
  "Kunci utama untuk bisa berpindah ke aplikasi lain.",
  True, {"eq": False}, risk="low")
R("enableAppSwitcherCheck", "Ganti Aplikasi & Tombol",
  "Matikan cek app-switcher",
  "Cek ini bisa membuat SEB keluar sendiri.", False, {"eq": True}, risk="low")
R("enableAltTab", "Ganti Aplikasi & Tombol", "Izinkan Alt+Tab",
  "Alt+Tab tidak diblokir.", True, {"eq": False}, risk="low")
R("enableAltEsc", "Ganti Aplikasi & Tombol", "Izinkan Alt+Esc",
  "Alt+Esc tidak diblokir.", True, {"eq": False}, risk="low")
R("enableCtrlEsc", "Ganti Aplikasi & Tombol", "Izinkan Ctrl+Esc",
  "Ctrl+Esc tidak diblokir.", True, {"eq": False}, risk="low")
R("enableAltF4", "Ganti Aplikasi & Tombol", "Izinkan Alt+F4",
  "Alt+F4 tidak diblokir.", True, {"eq": False}, risk="low")
R("enableAltMouseWheel", "Ganti Aplikasi & Tombol", "Izinkan Alt+scroll",
  "Alt+scroll tidak diblokir.", True, {"eq": False}, risk="low")
R("enableEsc", "Ganti Aplikasi & Tombol", "Izinkan tombol Esc",
  "Esc tidak diblokir.", True, {"eq": False}, risk="low")
R("enableMiddleMouse", "Ganti Aplikasi & Tombol", "Izinkan klik tengah",
  "Tombol mouse tengah diizinkan.", True, {"eq": False}, risk="low")
R("enableRightMouse", "Ganti Aplikasi & Tombol", "Izinkan klik kanan",
  "Klik kanan diizinkan.", True, {"eq": False}, risk="low")
R("ignoreExitKeys", "Ganti Aplikasi & Tombol", "Jangan abaikan tombol exit",
  "Bila True, tombol exit diabaikan (susah keluar).",
  False, {"eq": True}, risk="low")
for _i in range(1, 13):
    R("enableF%d" % _i, "Ganti Aplikasi & Tombol", "Izinkan F%d" % _i,
      "Tombol F%d tidak diblokir." % _i, True, {"eq": False}, risk="low")

# -------------------------------------------------------- Screenshot/Capture
R("allowWindowCapture", "Screenshot & Capture", "Izinkan capture window",
  "Kunci capture tingkat jendela (macOS).", True, {"eq": False, "absent": True}, risk="low", plat="mac")
R("allowScreenCapture", "Screenshot & Capture", "Izinkan screen capture",
  "Screenshot diizinkan.", True, {"eq": False, "absent": True}, risk="low", plat="mac")
R("allowScreenSharing", "Screenshot & Capture", "Matikan deteksi remote / screen sharing",
  "Kunci ini = EnableRemoteConnections (Keys.cs:307). Bila False, SEB "
  "mengaktifkan DisableRemoteConnections dan MEMBLOKIR start saat mendeteksi "
  "sesi remote (RemoteSessionOperation.cs:50 -> detector.IsRemoteSession()). "
  "Di macOS jalur yang sama membuat SEB mengunci diri saat Screen Sharing / "
  "Remote Management aktif. Set True untuk mematikan deteksi ini.",
  True, {"eq": False, "absent": True}, risk="low")
R("screenSharingMacEnforceBlocked", "Screenshot & Capture",
  "Jangan paksa blokir screen sharing (macOS)",
  "Kunci kedua (OR) untuk jalur screen sharing.", False, {"eq": True, "absent": True}, risk="low", plat="mac")
R("enablePrintScreen", "Screenshot & Capture", "Izinkan PrintScreen",
  "PrintScreen tidak diblokir.", True, {"eq": False}, risk="low")
R("allowFlashFullscreen", "Screenshot & Capture", "Izinkan Flash fullscreen",
  "Flash boleh fullscreen.", True, {"eq": False}, risk="low")

# ------------------------------------------------------------------ Clipboard
R("enablePrivateClipboard", "Clipboard", "Matikan clipboard privat",
  "Clipboard privat membuat copy/paste dari luar SEB hilang.",
  False, {"eq": True}, risk="low")
R("enablePrivateClipboardMacEnforce", "Clipboard",
  "Matikan paksa clipboard privat (macOS)",
  "Operand kedua (OR) di SEBAbstractWebView.m:98. Default @YES = memblokir. "
  "Kalau kunci ini TIDAK ADA di config, SEB memakai default @YES sehingga "
  "copy/paste tetap mati walau enablePrivateClipboard=False.",
  False, {"eq": True, "absent": True}, risk="low", plat="mac")
R("clipboardPolicy", "Clipboard", "Clipboard: Allow",
  "0=Allow, 1=Block, 2=SEBOnly. Default SEB adalah SEBOnly (2) = memblokir. "
  "Kalau kunci ini TIDAK ADA di config, SEB memakai SEBOnly, sehingga "
  "copy/paste dari luar SEB tetap mati.",
  0, {"in": [1, 2], "absent": True}, risk="low")

# ------------------------------------------------------- Proses & Monitoring
R("__DEACTIVATE_PROCESSES__", "Proses & Monitoring",
  "Nonaktifkan SEMUA proses terlarang",
  "Setiap entri prohibitedProcesses dibuat active=False, os=0. Ini menutup "
  "jalur lock 'termination failed' yang TIDAK punya kunci config lain.",
  None, {"special": "procs"}, risk="low", action="deactivate_procs")
R("monitorProcesses", "Proses & Monitoring", "Matikan monitoring proses",
  "Menghentikan pemantauan proses terlarang (Windows).",
  False, {"eq": True}, risk="medium", plat="win")
R("detectStoppedProcess", "Proses & Monitoring", "Matikan deteksi proses berhenti",
  "SEB tidak mengunci saat proses dihentikan.", False, {"eq": True}, risk="medium", plat="win")
R("__REMOTE_SESSION_DETECT__", "Proses & Monitoring",
  "Matikan deteksi sesi remote (RDP / VNC / TeamViewer)",
  "Pintasan untuk allowScreenSharing=True. Di Windows: "
  "RemoteSessionOperation.cs:50 memblokir start bila DisableRemoteConnections "
  "aktif dan IsRemoteSession() true (RDP/VNC/sesi remote). Di macOS: SEB "
  "mengunci diri saat Screen Sharing / Remote Management terdeteksi. "
  "Menyalakan ini mematikan seluruh jalur deteksi tersebut.",
  None, {"special": "remote"}, risk="low", action="set_remote_off")
R("detectAccessibilityApps", "Proses & Monitoring",
  "Jangan bunuh aplikasi ber-Izin Accessibility",
  "Membebaskan CleanShot X dan alat bantu lain (macOS).",
  False, {"eq": True, "absent": True}, risk="low", plat="mac")
R("autoQuitApplications", "Proses & Monitoring", "Jangan auto-quit aplikasi lain",
  "SEB tidak menutup aplikasi lain saat mulai.", False, {"eq": True, "absent": True}, risk="low", plat="mac")

# ----------------------------------------------------------------------- Layar
R("allowedDisplaysMaxNumber", "Layar (Display)", "Izinkan banyak layar",
  "Nilai 1 mematikan layar kedua / Sidecar.", 16, {"lt": 2}, risk="low")
R("allowDisplayMirroring", "Layar (Display)", "Izinkan display mirroring",
  "Mirroring tidak dipaksa dibongkar.", True, {"eq": False}, risk="low", plat="mac")
R("allowedDisplayBuiltin", "Layar (Display)", "Pakai display built-in",
  "PENTING: False = SEB MENOLAK layar built-in. Di MacBook berlayar "
  "built-in tunggal, SEB loop dan window tidak pernah muncul.",
  True, {"eq": False}, risk="low", plat="mac")
R("allowedDisplayBuiltinEnforce", "Layar (Display)", "Matikan penegakan display built-in",
  "Bila built-in tidak ada, jangan kunci layar.", False, {"eq": True}, risk="low", plat="mac")
R("allowedDisplaysIgnoreFailure", "Layar (Display)", "Abaikan kegagalan konfigurasi display",
  "Mencegah lock 'display configuration' saat resolusi berubah.",
  True, {"eq": False}, risk="low")

# --------------------------------------------------------------------- Browser
R("browserWindowAllowAddressBar", "Browser & Navigasi", "Izinkan address bar",
  "Address bar di jendela utama.", True, {"eq": False}, risk="low")
R("newBrowserWindowAllowAddressBar", "Browser & Navigasi", "Izinkan address bar (jendela baru)",
  "Address bar di jendela baru.", True, {"eq": False}, risk="low")
R("allowBrowsingBackForward", "Browser & Navigasi", "Izinkan tombol back/forward",
  "Navigasi maju/mundur.", True, {"eq": False}, risk="low")
R("allowDeveloperConsole", "Browser & Navigasi", "Izinkan developer console",
  "Console browser.", True, {"eq": False}, risk="medium")
R("allowFind", "Browser & Navigasi", "Izinkan Find (Ctrl+F)",
  "Pencarian di halaman.", True, {"eq": False}, risk="low")
R("allowPreferencesWindow", "Browser & Navigasi", "Izinkan jendela Preferences",
  "Jendela preferensi SEB.", True, {"eq": False}, risk="low")
R("newBrowserWindowByLinkPolicy", "Browser & Navigasi", "Popup link: Allow",
  "0=Block, 1=SameWindow, 2=Allow.", 2, {"in": [0, 1]}, risk="low")
R("newBrowserWindowByScriptPolicy", "Browser & Navigasi", "Popup script: Allow",
  "0=Block, 1=SameWindow, 2=Allow.", 2, {"in": [0, 1]}, risk="low")
R("blockPopUpWindows", "Browser & Navigasi", "Jangan blokir popup",
  "Popup diizinkan.", False, {"eq": True}, risk="low")
R("enableZoomPage", "Browser & Navigasi", "Izinkan zoom halaman",
  "Zoom halaman.", True, {"eq": False}, risk="low")
R("enableZoomText", "Browser & Navigasi", "Izinkan zoom teks",
  "Zoom teks.", True, {"eq": False}, risk="low")
R("enableJavaScript", "Browser & Navigasi", "Izinkan JavaScript",
  "JavaScript aktif. Sebagian sistem ujian butuh ini.", True, {"eq": False}, risk="medium")
R("enablePlugIns", "Browser & Navigasi", "Izinkan plug-in",
  "Plug-in browser.", True, {"eq": False}, risk="medium")
R("allowPDFPlugIn", "Browser & Navigasi", "Izinkan PDF plug-in",
  "Plug-in PDF.", True, {"eq": False}, risk="low")
R("downloadPDFFiles", "Browser & Navigasi", "Izinkan unduh PDF",
  "PDF boleh diunduh.", True, {"eq": False}, risk="low")
R("allowPDFReaderToolbar", "Browser & Navigasi", "Izinkan toolbar PDF reader",
  "Toolbar pembaca PDF.", True, {"eq": False}, risk="low")
R("browserURLSalt", "Browser & Navigasi", "Perbaiki popup macet saat startURL tanpa salt",
  "True memakai URL penuh sebagai salt BrowserExamKey. True + startURL tanpa "
  "salt pernah menyebabkan popup macet saat startup. MENGUBAH nilai ini "
  "mengubah perhitungan Browser Exam Key.",
  False, {"eq": True}, risk="medium")

# ------------------------------------------------------- Download/Upload/Print
R("allowDownUploads", "Download / Upload / Print", "Izinkan download & upload",
  "Aktivitas unduh/unggah.", True, {"eq": False}, risk="low")
R("allowDownloads", "Download / Upload / Print", "Izinkan download",
  "Unduhan diizinkan.", True, {"eq": False}, risk="low")
R("allowUploads", "Download / Upload / Print", "Izinkan upload",
  "Unggahan diizinkan.", True, {"eq": False}, risk="low")
R("allowPrint", "Download / Upload / Print", "Izinkan print",
  "Mencetak diizinkan.", True, {"eq": False}, risk="low")
R("openDownloads", "Download / Upload / Print", "Buka folder download",
  "Folder unduhan dibuka otomatis.", True, {"eq": False}, risk="low")
R("allowCustomDownUploadLocation", "Download / Upload / Print", "Izinkan lokasi unduh kustom",
  "Pemilihan lokasi unduh/unggah.", True, {"eq": False}, risk="low")

# ------------------------------------------------------------ Password & Keluar
R("hashedQuitPassword", "Password & Keluar", "Hapus password quit",
  "Bila terisi, keluar dari SEB memerlukan password.",
  "", {"nonempty": True}, risk="medium", action="clear")
R("hashedAdminPassword", "Password & Keluar", "Hapus password admin",
  "Bila terisi, pengaturan SEB dikunci password.",
  "", {"nonempty": True}, risk="medium", action="clear")
R("quitURL", "Password & Keluar", "Keluar tanpa harus membuka URL",
  "Bila terisi, SEB hanya bisa ditutup setelah membuka URL itu.",
  "", {"nonempty": True}, risk="medium", action="clear")
R("allowQuit", "Password & Keluar", "Izinkan keluar",
  "Tombol keluar tersedia.", True, {"eq": False}, risk="low")
R("examSessionReconfigureAllow", "Password & Keluar", "Izinkan rekonfigurasi sesi",
  "Mengizinkan penggantian config saat sesi berjalan.",
  True, {"eq": False}, risk="high")

# ------------------------------------------------------------- Sensor & Privasi
R("allowSiri", "Sensor & Privasi", "Izinkan Siri",
  "Bila False, SEB keluar sendiri saat Siri aktif (macOS).",
  True, {"eq": False}, risk="low", plat="mac")
R("allowDictation", "Sensor & Privasi", "Izinkan dictation",
  "Bila False, SEB keluar sendiri saat dictation aktif (macOS).",
  True, {"eq": False}, risk="low", plat="mac")
R("allowDictionaryLookup", "Sensor & Privasi", "Izinkan kamus / lookup",
  "SEB membunuh LookupViewService bila False (macOS).",
  True, {"eq": False, "absent": True}, risk="low", plat="mac")
R("allowAudioCapture", "Sensor & Privasi", "Izinkan audio capture",
  "Perekaman audio diizinkan.", True, {"eq": False}, risk="low")
R("allowVideoCapture", "Sensor & Privasi", "Izinkan video capture",
  "Perekaman video diizinkan.", True, {"eq": False}, risk="low")
R("allowWlan", "Sensor & Privasi", "Izinkan WLAN",
  "WiFi diizinkan.", True, {"eq": False}, risk="low")

# ------------------------------------------------------------------- URL Filter
R("URLFilterEnable", "URL Filter", "Matikan URL filter",
  "Filter URL dimatikan (bisa membuka situs yang diblokir ujian).",
  False, {"eq": True}, risk="high")
R("enableURLFilter", "URL Filter", "Matikan URL filter (lama)",
  "Filter URL versi lama dimatikan.", False, {"eq": True}, risk="high")
R("enableURLContentFilter", "URL Filter", "Matikan content filter",
  "Content filter dimatikan.", False, {"eq": True}, risk="high")
R("whitelistURLFilter", "URL Filter", "Kosongkan whitelist URL",
  "Daftar putih URL dikosongkan.", "", {"nonempty": True}, risk="high", action="clear")
R("blacklistURLFilter", "URL Filter", "Kosongkan blacklist URL",
  "Daftar hitam URL dikosongkan.", "", {"nonempty": True}, risk="high", action="clear")
R("URLFilterRules", "URL Filter", "Kosongkan aturan filter URL",
  "Semua aturan filter dihapus.", None, {"nonempty": True}, risk="high", action="clear_list")

BY_KEY = {r["key"]: r for r in RULES}

PRESETS = {
    "recommended": {
        "nama": "Rekomendasi (bypass penuh, risiko rendah)",
        "keys": [r["key"] for r in RULES if r["risk"] == "low"],
    },
    "lockscreen": {
        "nama": "Hilangkan lock screen saja",
        "keys": [r["key"] for r in RULES if r["cat"] == "Lock Screen & Integritas"],
    },
    "appswitch": {
        "nama": "Buka pindah aplikasi (Cmd/Alt+Tab)",
        "keys": ["allowSwitchToApplications", "enableAppSwitcherCheck", "enableAltTab",
                 "lockdownModePolicy", "enableAltEsc", "enableCtrlEsc", "enableAltF4"],
    },
    "capture": {
        "nama": "Buka screenshot",
        "keys": ["allowWindowCapture", "allowScreenCapture", "enablePrintScreen"],
    },
    "clipboard": {
        "nama": "Buka copy-paste (clipboard)",
        "keys": ["enablePrivateClipboard", "enablePrivateClipboardMacEnforce",
                 "clipboardPolicy"],
    },
    "display": {
        "nama": "Layar ganda & display",
        "keys": ["allowedDisplaysMaxNumber", "allowDisplayMirroring",
                 "allowedDisplayBuiltin", "allowedDisplayBuiltinEnforce",
                 "allowedDisplaysIgnoreFailure"],
    },
    "all": {
        "nama": "SEMUA (termasuk risiko tinggi: lepas URL filter)",
        "keys": [r["key"] for r in RULES],
    },
}


# ============================================================================
# CORE
# ============================================================================
class ConfigError(Exception):
    pass


def load_config(path):
    if not os.path.isfile(path):
        raise ConfigError("File tidak ditemukan: %s" % path)
    with open(path, "rb") as f:
        raw = f.read()
    if not raw:
        raise ConfigError("File kosong.")
    try:
        cfg = plistlib.loads(raw)
    except Exception as e:
        raise ConfigError(
            "Tidak bisa membaca sebagai plist: %s\n"
            "Kemungkinan config terenkripsi / dilindungi password, "
            "atau bukan file .seb yang sah." % type(e).__name__)
    if not isinstance(cfg, dict):
        raise ConfigError("Isi plist bukan dictionary (root=%s)." % type(cfg).__name__)
    return cfg, raw


def is_locked(cfg, rule):
    key, spec = rule["key"], rule["locked"]
    if spec.get("special") == "remote":
        # allowScreenSharing False/absent = deteksi remote AKTIF (memblokir)
        v = cfg.get("allowScreenSharing")
        return v is None or v is False
    if spec.get("special") == "procs":
        pp = cfg.get("prohibitedProcesses") or []
        act = [e for e in pp if isinstance(e, dict) and e.get("active")]
        return len(act) > 0
    if key not in cfg:
        return bool(spec.get("absent", False))
    v = cfg[key]
    if "ne" in spec:
        return v != spec["ne"]
    if "eq" in spec:
        return v == spec["eq"]
    if "in" in spec:
        return v in spec["in"]
    if "nonempty" in spec:
        return len(v) > 0 if isinstance(v, (list, dict, str, bytes)) else bool(v)
    if "lt" in spec:
        return isinstance(v, (int, float)) and v < spec["lt"]
    return False


def current_value(cfg, rule):
    if rule["locked"].get("special") == "remote":
        v = cfg.get("allowScreenSharing")
        return "aktif" if (v is None or v is False) else "nonaktif"
    if rule["locked"].get("special") == "procs":
        pp = cfg.get("prohibitedProcesses") or []
        act = [e for e in pp if isinstance(e, dict) and e.get("active")]
        return "%d aktif / %d total" % (len(act), len(pp))
    k = rule["key"]
    if k not in cfg:
        return "<tidak ada>"
    v = cfg[k]
    if isinstance(v, bytes):
        return "<%d byte>" % len(v)
    s = repr(v)
    return s if len(s) <= 40 else s[:37] + "..."


def apply_rules(cfg, keys, log):
    out = dict(cfg)
    applied = []
    for k in keys:
        rule = BY_KEY.get(k)
        if not rule:
            continue
        act = rule["action"]
        if act == "set_remote_off":
            out["allowScreenSharing"] = True
            out["screenSharingMacEnforceBlocked"] = False
            applied.append((rule["label"], "allowScreenSharing=True"))
        elif act == "deactivate_procs":
            pp = list(out.get("prohibitedProcesses") or [])
            n = 0
            for e in pp:
                if isinstance(e, dict) and e.get("active"):
                    e["active"] = False
                    e["os"] = 0
                    e["strongKill"] = False
                    n += 1
            out["prohibitedProcesses"] = pp
            if n:
                applied.append((rule["label"], "%d entri dinonaktifkan" % n))
        elif act == "clear":
            out[rule["key"]] = rule["value"]
            applied.append((rule["label"], "dikosongkan"))
        elif act == "clear_list":
            out[rule["key"]] = []
            applied.append((rule["label"], "dikosongkan"))
        else:
            out[rule["key"]] = rule["value"]
            applied.append((rule["label"], "= %r" % (rule["value"],)))
    return out, applied


def analyze(cfg):
    """Kembalikan (findings, warnings, info)."""
    findings = [r for r in RULES if is_locked(cfg, r)]
    warnings, info = [], []

    mode = cfg.get("sebMode")
    if mode == 1:
        warnings.append(
            "sebMode = 1 (SEB Server). Config dikendalikan server; perubahan "
            "lokal bisa ditimpa saat ujian dimulai.")
    elif mode == 0:
        info.append("sebMode = 0 (config lokal) - bypass dari sisi klien berlaku.")

    if cfg.get("sebServerURL"):
        warnings.append("sebServerURL terisi: %s" % cfg.get("sebServerURL"))

    if cfg.get("hashedQuitPassword") or cfg.get("hashedAdminPassword"):
        info.append("Config memakai password (quit/admin) - bisa dikosongkan "
                    "lewat opsi di kategori Password & Keluar.")

    if cfg.get("quitURL"):
        info.append("quitURL terisi - SEB hanya bisa ditutup setelah membuka URL itu.")

    try:
        pp = cfg.get("prohibitedProcesses") or []
        act = [e for e in pp if isinstance(e, dict) and e.get("active")]
        if act:
            exts = {os.path.splitext((e.get("executable") or ""))[1].lower() for e in act}
            oside = {e.get("os") for e in act}
            if ".exe" in exts and oside == {1}:
                info.append("Config asal Windows (%d entri terlarang .exe, os=1)."
                            % len(act))
            else:
                warnings.append("%d proses terlarang masih AKTIF - bisa memicu "
                                "lock 'termination failed'." % len(act))
    except Exception:
        pass

    if cfg.get("URLFilterEnable") or cfg.get("enableURLFilter"):
        info.append("URL filter aktif - membuka situs di luar daftar akan diblokir.")

    if "lockdownModePolicy" not in cfg:
        warnings.append(
            "lockdownModePolicy tidak ada. Di macOS 12.1+ itu berarti AAC aktif: "
            "kunci bypass lain (Cmd+Tab/Alt+Tab) DIABAIKAN sampai nilai ini = 1.")
    return findings, warnings, info


def detect_origin(cfg):
    tags = []
    if cfg.get("createNewDesktop") is not None or cfg.get("killExplorerShell") is not None:
        tags.append("Windows")
    if cfg.get("lockdownModePolicy") is not None or cfg.get("allowedDisplayBuiltin") is not None:
        tags.append("macOS")
    ov = cfg.get("originatorVersion")
    if ov:
        tags.append("dibuat oleh %s" % ov)
    return ", ".join(tags) if tags else "tidak diketahui"


# ============================================================================
# CLI
# ============================================================================
def run_cli(args):
    try:
        cfg, raw = load_config(args.input)
    except ConfigError as e:
        print("GAGAL:", e)
        return 2

    findings, warnings, info = analyze(cfg)
    print("=" * 78)
    print("  SEB Config Bypass Studio v%s  (CLI)" % VERSION)
    print("=" * 78)
    print("  File   : %s" % args.input)
    print("  Ukuran : %d byte  sha256 %s" % (len(raw), hashlib.sha256(raw).hexdigest()[:24]))
    print("  Kunci  : %d" % len(cfg))
    print("  Asal   : %s" % detect_origin(cfg))
    print()

    if warnings:
        print("  PERINGATAN:")
        for w in warnings:
            print("    [!] %s" % w)
        print()
    if info:
        print("  INFO:")
        for i in info:
            print("    [i] %s" % i)
        print()

    print("  TERKUNCI (%d dari %d aturan):" % (len(findings), len(RULES)))
    for r in findings:
        print("    [%s] %-42s sekarang=%-18s -> %r" %
              (r["cat"][:4], r["label"], current_value(cfg, r), r["value"]))
    print()

    if args.list and not args.output:
        return 0

    keys = []
    if args.preset:
        keys = list(PRESETS[args.preset]["keys"])
    elif args.keys:
        keys = [k.strip() for k in args.keys.split(",") if k.strip()]
    else:
        keys = [r["key"] for r in findings]

    if not args.output:
        print("  (tidak ada --output; hanya menampilkan deteksi)")
        return 0

    out, applied = apply_rules(cfg, keys, None)
    with open(args.output, "wb") as f:
        f.write(plistlib.dumps(out, fmt=plistlib.FMT_XML, sort_keys=True))

    chk = plistlib.load(open(args.output, "rb"))
    print("  DITERAPKAN (%d):" % len(applied))
    for label, how in applied:
        print("    + %-46s %s" % (label, how))
    with open(args.input, "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == hashlib.sha256(raw).hexdigest()
    print()
    print("  OUTPUT : %s" % args.output)
    print("           %d byte, %d kunci" % (os.path.getsize(args.output), len(chk)))
    print("           sha256 %s" % hashlib.sha256(open(args.output, "rb").read()).hexdigest()[:24])
    print("  Input tidak diubah. OK.")
    return 0


# ============================================================================
# GUI
# ============================================================================
def run_gui(preload=None):
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except ImportError:
        print("tkinter tidak tersedia. Di Linux: sudo apt install python3-tk\n"
              "Atau pakai mode CLI: python3 %s --cli IN.seb OUT.seb --preset recommended"
              % os.path.basename(__file__))
        return 1

    class App(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("SEB Config Bypass Studio v%s" % VERSION)
            self.geometry("1180x780")
            self.minsize(940, 620)
            self.cfg = None
            self.cfg_path = None
            self.raw = None
            self.vars = {}
            self.findings = []

            self.style = ttk.Style(self)
            try:
                self.style.theme_use("clam")
            except Exception:
                pass
            self.style.configure("Head.TLabel", font=("Helvetica", 13, "bold"))
            self.style.configure("Sub.TLabel", foreground="#555")
            self.style.configure("Cat.TLabel", font=("Helvetica", 11, "bold"))
            self.style.configure("Lock.TLabel", foreground="#b00020")
            self.style.configure("Ok.TLabel", foreground="#1b5e20")

            self._build()

        # ---------------------------------------------------------------- UI
        def _build(self):
            top = ttk.Frame(self, padding=10)
            top.pack(fill="x")
            ttk.Label(top, text="SEB Config Bypass Studio",
                      style="Head.TLabel").pack(side="left")
            ttk.Label(top, text="buka config.seb -> deteksi -> pilih bypass -> simpan",
                      style="Sub.TLabel").pack(side="left", padx=12)

            frow = ttk.Frame(self, padding=(10, 0, 10, 6))
            frow.pack(fill="x")
            ttk.Button(frow, text="Buka config.seb...", command=self.open_file).pack(side="left")
            self.lbl_file = ttk.Label(frow, text="(belum ada file)", style="Sub.TLabel")
            self.lbl_file.pack(side="left", padx=10)

            self.lbl_meta = ttk.Label(self, text="", style="Sub.TLabel", padding=(10, 0))
            self.lbl_meta.pack(fill="x")

            self.banner = tk.Text(self, height=4, wrap="word", relief="flat",
                                  background="#fff8e1", foreground="#5d4037",
                                  font=("Helvetica", 10))
            self.banner.pack(fill="x", padx=10, pady=(6, 0))
            self.banner.configure(state="disabled")

            mid = ttk.Panedwindow(self, orient="horizontal")
            mid.pack(fill="both", expand=True, padx=10, pady=8)

            # kiri: opsi
            left = ttk.Frame(mid)
            mid.add(left, weight=3)
            pbar = ttk.Frame(left)
            pbar.pack(fill="x", pady=(0, 4))
            ttk.Label(pbar, text="Pilihan Bypass", style="Head.TLabel").pack(side="left")
            self.lbl_sel = ttk.Label(pbar, text="", style="Sub.TLabel")
            self.lbl_sel.pack(side="right")

            prow = ttk.Frame(left)
            prow.pack(fill="x", pady=(0, 6))
            ttk.Label(prow, text="Preset:", style="Sub.TLabel").pack(side="left")
            self.preset_var = tk.StringVar(value="recommended")
            cb = ttk.Combobox(prow, textvariable=self.preset_var, state="readonly",
                              width=46,
                              values=["%s — %s" % (k, v["nama"]) for k, v in PRESETS.items()])
            cb.set("recommended — %s" % PRESETS["recommended"]["nama"])
            cb.pack(side="left", padx=6)
            cb.bind("<<ComboboxSelected>>", self.on_preset)
            ttk.Button(prow, text="Pilih semua", command=lambda: self.set_all(True)).pack(side="left", padx=2)
            ttk.Button(prow, text="Kosongkan", command=lambda: self.set_all(False)).pack(side="left")

            wrap = ttk.Frame(left)
            wrap.pack(fill="both", expand=True)
            self.canvas = tk.Canvas(wrap, highlightthickness=0)
            vs = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
            self.canvas.configure(yscrollcommand=vs.set)
            vs.pack(side="right", fill="y")
            self.canvas.pack(side="left", fill="both", expand=True)
            self.inner = ttk.Frame(self.canvas)
            self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
            self.inner.bind("<Configure>",
                            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
            self.canvas.bind_all("<MouseWheel>",
                                 lambda e: self.canvas.yview_scroll(int(-e.delta / 60), "units"))

            # kanan: temuan
            right = ttk.Frame(mid)
            mid.add(right, weight=2)
            ttk.Label(right, text="Temuan / Diagnosa", style="Head.TLabel").pack(anchor="w")
            cols = ("cat", "key", "now", "status")
            self.tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
            for c, t, w in (("cat", "Kategori", 130), ("key", "Kunci", 200),
                            ("now", "Sekarang", 110), ("status", "Status", 90)):
                self.tree.heading(c, text=t)
                self.tree.column(c, width=w, anchor="w")
            self.tree.tag_configure("locked", foreground="#b00020")
            self.tree.tag_configure("ok", foreground="#1b5e20")
            self.tree.pack(fill="both", expand=True, pady=(4, 0))

            bot = ttk.Frame(self, padding=10)
            bot.pack(fill="x")
            self.btn_apply = ttk.Button(bot, text="Terapkan & Simpan sebagai...",
                                        command=self.apply, state="disabled")
            self.btn_apply.pack(side="left")
            self.lbl_status = ttk.Label(bot, text="", style="Sub.TLabel")
            self.lbl_status.pack(side="left", padx=12)

        # ------------------------------------------------------------- helpers
        def log(self, msg):
            self.lbl_status.configure(text=msg)
            self.update_idletasks()

        def set_banner(self, warnings, info):
            lines = []
            for w in warnings:
                lines.append("[!] " + w)
            for i in info:
                lines.append("[i] " + i)
            self.banner.configure(state="normal")
            self.banner.delete("1.0", "end")
            self.banner.insert("1.0", "\n".join(lines) if lines else
                               "[i] Tidak ada peringatan.")
            self.banner.configure(state="disabled")

        # ------------------------------------------------------------ actions
        def open_file(self):
            p = filedialog.askopenfilename(
                title="Buka config SEB",
                filetypes=[("SEB config", "*.seb"), ("Semua file", "*.*")])
            if p:
                self.open_path(p)

        def open_path(self, p):
            try:
                cfg, raw = load_config(p)
            except ConfigError as e:
                messagebox.showerror("Gagal membuka", str(e))
                return False
            self.cfg, self.raw, self.cfg_path = cfg, raw, p
            self.lbl_file.configure(text=p)
            findings, warnings, info = analyze(cfg)
            self.findings = findings
            self.lbl_meta.configure(
                text="%d kunci | %d byte | asal: %s | %d aturan terkunci dari %d"
                     % (len(cfg), len(raw), detect_origin(cfg), len(findings), len(RULES)))
            self.set_banner(warnings, info)
            self.build_options(cfg, findings)
            self.build_tree(cfg, findings)
            self.btn_apply.configure(state="normal")
            self.log("Siap. %d opsi terkunci terdeteksi." % len(findings))
            return True

        def build_options(self, cfg, findings):
            for w in self.inner.winfo_children():
                w.destroy()
            self.vars.clear()
            locked_keys = {r["key"] for r in findings}
            for cat in CATEGORIES:
                rules = [r for r in RULES if r["cat"] == cat]
                if not rules:
                    continue
                hdr = ttk.Frame(self.inner)
                hdr.pack(fill="x", pady=(8, 2))
                nlock = sum(1 for r in rules if r["key"] in locked_keys)
                ttk.Label(hdr, text="%s  (%d terkunci / %d)" % (cat, nlock, len(rules)),
                          style="Cat.TLabel").pack(side="left")
                ttk.Button(hdr, text="pilih semua", width=12,
                           command=lambda rs=rules: self._cat(rs, True)).pack(side="right", padx=2)
                ttk.Button(hdr, text="kosongkan", width=10,
                           command=lambda rs=rules: self._cat(rs, False)).pack(side="right")

                for r in rules:
                    locked = r["key"] in locked_keys
                    var = tk.BooleanVar(value=locked and r["risk"] == "low")
                    self.vars[r["key"]] = var
                    row = ttk.Frame(self.inner)
                    row.pack(fill="x", padx=(6, 0))
                    mark = "  " if r["risk"] == "low" else ("* " if r["risk"] == "medium" else "! ")
                    cb = ttk.Checkbutton(row, variable=var,
                                         text="%s%s" % (mark, r["label"]),
                                         command=self.update_count)
                    cb.pack(side="left")
                    note = "-> %r" % (r["value"],) if r["action"] == "set" else "-> dikosongkan"
                    if r["action"] == "deactivate_procs":
                        note = "-> semua active=False"
                    col = "Lock.TLabel" if locked else "Ok.TLabel"
                    ttk.Label(row, text="%s   %s" % (current_value(cfg, r), note),
                              style=col).pack(side="left", padx=8)
                    ttk.Label(row, text=r["key"], style="Sub.TLabel").pack(side="right", padx=6)
            self.update_count()

        def build_tree(self, cfg, findings):
            for i in self.tree.get_children():
                self.tree.delete(i)
            locked_keys = {r["key"] for r in findings}
            for r in RULES:
                locked = r["key"] in locked_keys
                self.tree.insert("", "end", values=(
                    r["cat"], r["key"], current_value(cfg, r),
                    "TERKUNCI" if locked else "ok"),
                    tags=("locked" if locked else "ok",))

        def _cat(self, rules, val):
            for r in rules:
                if r["key"] in self.vars:
                    self.vars[r["key"]].set(val)
            self.update_count()

        def set_all(self, val):
            for v in self.vars.values():
                v.set(val)
            self.update_count()

        def on_preset(self, _evt=None):
            raw = self.preset_var.get()
            key = raw.split(" — ")[0].strip()
            spec = PRESETS.get(key)
            if not spec:
                return
            want = set(spec["keys"])
            for k, v in self.vars.items():
                v.set(k in want)
            self.update_count()

        def update_count(self):
            n = sum(1 for v in self.vars.values() if v.get())
            self.lbl_sel.configure(text="%d dipilih" % n)

        def selected_keys(self):
            return [k for k, v in self.vars.items() if v.get()]

        def apply(self):
            if not self.cfg:
                return
            keys = self.selected_keys()
            if not keys:
                messagebox.showinfo("Tidak ada pilihan",
                                    "Pilih minimal satu opsi bypass.")
                return
            base = os.path.splitext(os.path.basename(self.cfg_path))[0]
            out = filedialog.asksaveasfilename(
                title="Simpan config hasil bypass",
                initialfile="%s.bypass.seb" % base,
                initialdir=os.path.dirname(self.cfg_path) or ".",
                defaultextension=".seb",
                filetypes=[("SEB config", "*.seb")])
            if not out:
                return
            if os.path.abspath(out) == os.path.abspath(self.cfg_path):
                messagebox.showerror("Ditolak", "Output tidak boleh menimpa file input.")
                return
            try:
                newcfg, applied = apply_rules(self.cfg, keys, self.log)
                with open(out, "wb") as f:
                    f.write(plistlib.dumps(newcfg, fmt=plistlib.FMT_XML, sort_keys=True))
                chk = plistlib.load(open(out, "rb"))
                assert len(chk) >= len(self.cfg)
                with open(self.cfg_path, "rb") as f:
                    same = hashlib.sha256(f.read()).hexdigest() == \
                           hashlib.sha256(self.raw).hexdigest()
            except Exception as e:
                messagebox.showerror("Gagal menulis", "%s: %s" % (type(e).__name__, e))
                return

            nf, nw, ni = analyze(chk)
            still = [r for r in nf if r["key"] in set(keys)]
            msg = ("File tersimpan:\n%s\n\n"
                   "%d opsi diterapkan.\n"
                   "Aturan terkunci: %d -> %d\n"
                   "Input tidak diubah: %s\n"
                   % (out, len(applied), len(self.findings), len(nf),
                      "ya" if same else "TIDAK"))
            if still:
                msg += "\nMasih terkunci (tidak dipilih):\n"
                for r in still[:8]:
                    msg += "  - %s\n" % r["key"]
                if len(still) > 8:
                    msg += "  ... dan %d lagi\n" % (len(still) - 8)
            messagebox.showinfo("Selesai", msg)
            self.log("Tersimpan: %s (%d opsi)" % (out, len(applied)))

    app = App()
    preload = os.environ.get("SEB_GUI_OPEN") or preload
    if preload and os.path.isfile(preload):
        try:
            app.after(60, lambda: app.open_path(preload))
        except Exception:
            pass
    if os.environ.get("SEB_GUI_SMOKE"):
        # mode uji: muat file, terapkan preset, simpan, lalu keluar
        src = os.environ["SEB_GUI_SMOKE"]
        out = os.environ.get("SEB_GUI_SMOKE_OUT", "/tmp/gui_smoke_out.seb")
        ok = app.open_path(src)
        app.update()
        app.preset_var.set("recommended — %s" % PRESETS["recommended"]["nama"])
        app.on_preset()
        app.update()
        n = sum(1 for v in app.vars.values() if v.get())
        sel = app.selected_keys()
        newcfg, applied = apply_rules(app.cfg, sel, app.log)
        with open(out, "wb") as f:
            f.write(plistlib.dumps(newcfg, fmt=plistlib.FMT_XML, sort_keys=True))
        chk = plistlib.load(open(out, "rb"))
        nf, nw, ni = analyze(chk)
        orig = hashlib.sha256(open(src, "rb").read()).hexdigest()
        print("SMOKE: loaded=%s file=%s" % (ok, src))
        print("SMOKE: opsi tercantum=%d terpilih=%d" % (len(app.vars), n))
        print("SMOKE: diterapkan=%d" % len(applied))
        print("SMOKE: terkunci sebelum=%d sesudah=%d" % (len(app.findings), len(nf)))
        print("SMOKE: widget kategori=%d" % len(CATEGORIES))
        print("SMOKE: output=%s (%d byte)" % (out, os.path.getsize(out)))
        print("SMOKE: input utuh=%s" %
              (hashlib.sha256(open(src, "rb").read()).hexdigest() == orig))
        app.destroy()
        return 0
    app.mainloop()
    return 0


# ============================================================================
def main():
    ap = argparse.ArgumentParser(
        description="SEB Config Bypass Studio v%s" % VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cli", action="store_true", help="mode tanpa GUI")
    ap.add_argument("--list", action="store_true", help="hanya tampilkan deteksi")
    ap.add_argument("--preset", choices=sorted(PRESETS.keys()), help="preset bypass")
    ap.add_argument("--keys", help="daftar key dipisah koma")
    ap.add_argument("input", nargs="?", help="config.seb masukan")
    ap.add_argument("output", nargs="?", help="config.seb keluaran")
    args = ap.parse_args()

    if args.cli:
        if not args.input:
            ap.error("--cli butuh <input>")
        return run_cli(args)
    return run_gui(args.input)


if __name__ == "__main__":
    sys.exit(main())
