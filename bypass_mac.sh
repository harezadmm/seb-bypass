#!/bin/bash
# ============================================================
#  SEB Bypass — macOS (apply config bypass saja)
#  Prasyarat: SEB 3.7.1 sudah terinstall manual via DMG
#  Repo: github.com/harezadmm/seb-bypass
#  Varian paste-safe: semua baris pendek, aman untuk
#  terminal sempit (tidak akan terpotong saat paste)
# ============================================================
set -u

REPO_RAW="https://raw.githubusercontent.com/harezadmm"
SEB_FILE="SebClientSettings.seb"
SEB_SHA256="27d6485cfc8716c0505099748a8dc80e441b91c23ca6c734af641a4f290bda74"
SEB_URL="${REPO_RAW}/seb-bypass/main/${SEB_FILE}"
SEB_DEST="$HOME/Library/Preferences/${SEB_FILE}"

GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok()  { echo -e "${GREEN}[OK]${NC} $1"; }
err() { echo -e "${RED}[GAGAL]${NC} $1"; }
step() { echo -e "\n${CYAN}==>${NC} ${BOLD}$1${NC}"; }

echo -e "${CYAN}SEB Bypass — macOS${NC}"

# 1. Pastikan SEB terinstall
step "1/3 — Cek SEB terinstall"
SEB_APP="/Applications/Safe Exam Browser.app"
if [ -d "$SEB_APP" ]; then
    ok "SEB ditemukan di /Applications"
else
    err "SEB TIDAK ditemukan di /Applications"
    echo "  Install dulu via DMG, lalu jalankan lagi script ini."
    echo "  DMG: https://github.com/SafeExamBrowser/seb-mac/releases"
    exit 1
fi

# 2. Download + verify + deploy config
step "2/3 — Deploy config bypass"
TMP_SEB="/tmp/SebClientSettings.seb"
if ! curl -fsSL "$SEB_URL" -o "$TMP_SEB"; then
    err "Download gagal — cek koneksi"
    exit 1
fi
DL_SHA="$(shasum -a 256 "$TMP_SEB" | awk '{print $1}')"
if [ "$DL_SHA" != "$SEB_SHA256" ]; then
    err "SHA-256 tidak cocok — file korup/berubah"
    echo "  Diharapkan: $SEB_SHA256"
    echo "  Diterima : $DL_SHA"
    rm -f "$TMP_SEB"
    exit 1
fi
ok "SHA-256 cocok"

mkdir -p "$HOME/Library/Preferences"
if [ -f "$SEB_DEST" ]; then
    cp "$SEB_DEST" "$SEB_DEST.bak.$(date +%Y%m%d%H%M%S)"
    ok "Config lama dibackup"
fi
mv "$TMP_SEB" "$SEB_DEST"
ok "Config terpasang: $SEB_DEST"

# Flush cache preferensi
defaults delete org_safeexambrowser_SEB &>/dev/null
killall cfprefsd &>/dev/null
ok "Cache preferensi di-flush"

# 3. Verifikasi kunci bypass
step "3/3 — Verifikasi kunci bypass"
KEYS_OK=0
check_key() {
    local key="$1" expect="$2"
    local val
    val="$(grep -o "<key>${key}</key><[a-z]*/>" "$SEB_DEST" \
        | grep -o '<[a-z]*/>$' | tr -d '</>')"
    if [ "$val" = "$expect" ]; then
        ok "${key} = ${expect}"
        KEYS_OK=$((KEYS_OK+1))
    else
        err "${key} = ${val} (harusnya ${expect})"
    fi
}
check_key allowVirtualMachine true
check_key allowSwitchToApplications true
check_key enableAppSwitcherCheck false
check_key enableAltTab true

echo ""
if [ "$KEYS_OK" -eq 4 ]; then
    echo -e "${GREEN}${BOLD}SUKSES — BYPASS AKTIF${NC}"
    echo "  Buka SEB → Cmd+Tab → harus bisa pindah aplikasi."
else
    err "Config terpasang tapi kunci tidak sesuai — kirim output ini"
    exit 1
fi
