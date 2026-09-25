#!/bin/bash
# ============================================================
#  SEB Bypass — macOS One-Command Installer
#  Homebrew + Safe Exam Browser 3.7.1 + Bypass Config
#  Repo: github.com/harezadmm/seb-bypass
# ============================================================
set -u

REPO_RAW="https://raw.githubusercontent.com/harezadmm/seb-bypass/main"
CONFIG_NAME="SebClientSettings.seb"
CONFIG_SHA256="a4644dcd571babe83a2bc4ac3c4cdf7578b1c0e278f4ea84b9ce449ea298bde4"
CONFIG_URL="${REPO_RAW}/${CONFIG_NAME}"
CONFIG_DEST="$HOME/Library/Preferences/${CONFIG_NAME}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[GAGAL]${NC} $1"; }
step() { echo -e "\n${CYAN}${BOLD}==>${NC} ${BOLD}$1${NC}"; }

echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   SEB Bypass Installer — macOS (one-command)     ║${NC}"
echo -e "${CYAN}║   SEB 3.7.1 + Config Bypass via Homebrew         ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"

# ------------------------------------------------------------
# 1. Xcode CLT (prasyarat Homebrew)
# ------------------------------------------------------------
step "1/5 — Cek Xcode Command Line Tools"
if xcode-select -p &>/dev/null; then
    ok "Xcode CLT sudah terpasang"
else
    echo "    Memasang Xcode CLT (jika diminta GUI, klik Install)..."
    xcode-select --install &>/dev/null
    # Tunggu sampai CLT tersedia (instalasi via GUI bisa lama)
    for i in $(seq 1 60); do
        xcode-select -p &>/dev/null && break
        sleep 5
    done
    xcode-select -p &>/dev/null && ok "Xcode CLT terpasang" || { err "Xcode CLT tidak terpasang — install manual: xcode-select --install"; exit 1; }
fi

# ------------------------------------------------------------
# 2. Homebrew
# ------------------------------------------------------------
step "2/5 — Cek Homebrew"
BREW=""
if command -v brew &>/dev/null; then
    BREW="$(command -v brew)"
    ok "Homebrew sudah terpasang: ${BREW}"
elif [ -x "/opt/homebrew/bin/brew" ]; then
    BREW="/opt/homebrew/bin/brew"
    ok "Homebrew ditemukan (Apple Silicon): ${BREW}"
elif [ -x "/usr/local/bin/brew" ]; then
    BREW="/usr/local/bin/brew"
    ok "Homebrew ditemukan (Intel): ${BREW}"
else
    echo "    Homebrew belum ada — memasang otomatis..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/null
    if [ -x "/opt/homebrew/bin/brew" ]; then
        BREW="/opt/homebrew/bin/brew"
    elif [ -x "/usr/local/bin/brew" ]; then
        BREW="/usr/local/bin/brew"
    fi
    if [ -n "${BREW}" ]; then
        ok "Homebrew terpasang: ${BREW}"
    else
        err "Homebrew gagal terpasang — cek jaringan / install manual: https://brew.sh"
        exit 1
    fi
fi
BREW_BIN="$(dirname "${BREW}")"
export PATH="${BREW_BIN}:${PATH}"

# ------------------------------------------------------------
# 3. Safe Exam Browser 3.7.1 via cask
# ------------------------------------------------------------
step "3/5 — Install Safe Exam Browser 3.7.1 (Homebrew cask)"
SEB_APP="/Applications/Safe Exam Browser.app"
if [ -d "${SEB_APP}" ]; then
    SEB_VER="$(defaults read "${SEB_APP}/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null || echo '?')"
    if [ "${SEB_VER}" = "3.7.1" ]; then
        ok "SEB 3.7.1 sudah terpasang — skip install"
    else
        warn "SEB versi ${SEB_VER} terdeteksi — upgrade ke 3.7.1 via cask..."
        "${BREW}" install --cask safe-exam-browser || {
            err "Upgrade cask gagal — uninstall dulu dari Finder, lalu re-run script ini"
            exit 1
        }
    fi
else
    "${BREW}" install --cask safe-exam-browser || {
        err "brew install --cask safe-exam-browser gagal — cek jaringan / jalankan: brew update"
        exit 1
    }
fi
# Verifikasi
if [ ! -d "${SEB_APP}" ]; then
    err "SEB app tidak ditemukan di /Applications setelah install — cek brew log"
    exit 1
fi
SEB_VER="$(defaults read "${SEB_APP}/Contents/Info.plist" CFBundleShortVersionString 2>/dev/null || echo '?')"
ok "Safe Exam Browser ${SEB_VER} terpasang di /Applications"

# ------------------------------------------------------------
# 4. Bypass config
# ------------------------------------------------------------
step "4/5 — Deploy config bypass"
echo "    Mengunduh ${CONFIG_NAME} dari repo..."
TMP_SEB="$(mktemp /tmp/sebconfig.XXXXXX)"
if ! curl -fsSL "${CONFIG_URL}" -o "${TMP_SEB}"; then
    err "Download config gagal — cek koneksi ke raw.githubusercontent.com"
    rm -f "${TMP_SEB}"
    exit 1
fi
DL_SHA="$(shasum -a 256 "${TMP_SEB}" | awk '{print $1}')"
if [ "${DL_SHA}" != "${CONFIG_SHA256}" ]; then
    err "SHA-256 TIDAK COCOK — file config berubah/korup, install dibatalkan"
    echo "    Diharapkan: ${CONFIG_SHA256}"
    echo "    Diterima : ${DL_SHA}"
    rm -f "${TMP_SEB}"
    exit 1
fi
ok "SHA-256 cocok (${DL_SHA:0:16}...)"

mkdir -p "$HOME/Library/Preferences"
# Backup config lama jika ada
if [ -f "${CONFIG_DEST}" ]; then
    cp "${CONFIG_DEST}" "${CONFIG_DEST}.bak.$(date +%Y%m%d%H%M%S)"
    ok "Config lama dibackup: ${CONFIG_DEST}.bak.*"
fi
mv "${TMP_SEB}" "${CONFIG_DEST}"
ok "Config terpasang: ${CONFIG_DEST}"

# Bersihkan defaults lama agar SEB baca file config baru
defaults delete org_safeexambrowser_SEB &>/dev/null && ok "defaults lama dihapus" || true
killall cfprefsd &>/dev/null || true
ok "Cache preferensi di-flush"

# ------------------------------------------------------------
# 5. Verifikasi kunci bypass
# ------------------------------------------------------------
step "5/5 — Verifikasi kunci bypass"
KEYS_OK=0
check_key() {
    local key="$1" expect="$2"
    local val
    val="$(grep -o "<key>${key}</key><[a-z]*/>" "${CONFIG_DEST}" | grep -o '<[a-z]*/>$' | tr -d '</>')"
    if [ "${val}" = "${expect}" ]; then
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
check_policy() {
    local val
    val="$(sed -n 's/.*<key>lockdownModePolicy<\/key><integer>\([0-9]*\)<\/integer>.*/\1/p' "${CONFIG_DEST}")"
    if [ "${val}" = "1" ]; then
        ok "lockdownModePolicy = 1 (EnforceClassic: AAC off, kiosk klasik)"
        KEYS_OK=$((KEYS_OK+1))
    else
        err "lockdownModePolicy = ${val} (harusnya 1 — tanpa ini macOS 12.1+ memakai AAC Assessment Mode dan kunci bypass diabaikan)"
    fi
}
check_policy

echo ""
if [ "${KEYS_OK}" -eq 5 ]; then
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║        SUKSES — SEB 3.7.1 + BYPASS AKTIF         ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Terpasang:"
    echo "   • Safe Exam Browser 3.7.1 — /Applications/Safe Exam Browser.app"
    echo "   • Config bypass          — ${CONFIG_DEST}"
    echo ""
    echo "  Fitur bypass aktif:"
    echo "   • Bypass deteksi Virtual Machine"
    echo "   • Alt+Tab / Cmd+Tab unlock"
    echo "   • Allow switch to applications"
    echo "   • Kiosk mode klasik (AAC dimatikan — kunci bypass efektif di macOS 12.1+)"
    echo ""
    echo "  Tes: buka SEB → tekan Cmd+Tab → harus bisa pindah aplikasi."
    echo ""
else
    err "Config terpasang tapi ${KEYS_OK}/5 kunci bypass benar — cek manual file ${CONFIG_DEST}"
    exit 1
fi
