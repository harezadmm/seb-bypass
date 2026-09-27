#!/bin/bash
# ============================================================
#  SEB Bypass — macOS One-Command Installer  (v2)
#  Safe Exam Browser 3.7.1 + Bypass Config
#  Fitur: VM bypass, Cmd+Tab (ganti aplikasi), kiosk klasik
#  Repo: github.com/harezadmm/seb-bypass
#
#  v2 beda dari v1:
#   - Jalur utama TIDAK butuh Xcode CLT / Homebrew.
#     DMG resmi (ETH Zurich) diunduh + diverifikasi SHA-256.
#   - Verifikasi kunci pakai plutil (bukan grep) + auto-repair.
#   - Cmd+Tab = enableAltTab (nama kunci di macOS), dicek eksplisit.
#   - Idempotent, bisa diulang kapan saja.
# ============================================================
set -u

# ------------------------------------------------------------
# Konstanta
# ------------------------------------------------------------
REPO_RAW="https://raw.githubusercontent.com/harezadmm/seb-bypass/main"

CONFIG_NAME="SebClientSettings.seb"
CONFIG_SHA256="a58bfd084ca65fc4eb8a0c04d805ec980649b082b0e72cd00cff5f5ab2a54652"
CONFIG_URL="${REPO_RAW}/${CONFIG_NAME}"
CONFIG_DEST="$HOME/Library/Preferences/${CONFIG_NAME}"

APP_NAME="Safe Exam Browser.app"
SEB_APP="/Applications/${APP_NAME}"
SEB_BIN="${SEB_APP}/Contents/MacOS/Safe Exam Browser"
SEB_VERSION="3.7.1"

DMG_NAME="SafeExamBrowser-3.7.1.dmg"
DMG_SHA256="d9a11b2f5f35f5681b0f0f204a217bdcb90413481748f34cbff2ae86044e6086"  # terukur 2026-09-27
DMG_BYTES="11456688"
DMG_URL_OFFICIAL="https://github.com/SafeExamBrowser/seb-mac/releases/download/3.7.1/${DMG_NAME}"

BREW_CASK="safe-exam-browser"
DOMAIN="org_safeexambrowser_SEB"

# SEB membaca config SISTEM (/Library/Preferences/) DULU, baru config
# user (~/Library/Preferences/). Kalau file sistem ada tapi salah,
# bypass di level user DIABAIKAN tanpa pesan error apa pun.
SYSTEM_PREF_DIR="/Library/Preferences"
SYSTEM_PREF="${SYSTEM_PREF_DIR}/${CONFIG_NAME}"

# ------------------------------------------------------------
# Argumen
# ------------------------------------------------------------
MODE_DMG=1          # 1 = DMG resmi (default), 0 = paksa brew cask
MODE_SYSTEM=0       # 1 = pasang juga di /Library/Preferences (sudo)
ALLOW_REPAIR=1      # 1 = perbaiki kunci yang salah otomatis
VERIFY_ONLY=0       # 1 = lewati install, cuma verifikasi status
ARG_DMG=""
ARG_CONFIG=""

usage() {
    cat <<'USAGE'
Pemakaian:
  bash install_mac_one_v2.sh [opsi]

Opsi:
  --dmg <path>      Pakai file DMG lokal (skip unduh)
  --config <path>   Pakai file .seb lokal (skip unduh)
  --brew            Paksa jalur Homebrew cask (butuh Xcode CLT)
  --system          Pasang juga di /Library/Preferences/ (butuh sudo).
                    Dipakai kalau SEB tetap terkunci padahal config
                    user sudah benar - config sistem menimpanya.
  --no-repair       Jangan perbaiki kunci yang salah, cuma laporkan
  --verify-only     Lewati install SEB, cuma verifikasi status
  -h, --help        Tampilkan bantuan ini

Contoh:
  bash install_mac_one_v2.sh
  bash install_mac_one_v2.sh --dmg ~/Downloads/SafeExamBrowser-3.7.1.dmg
  bash install_mac_one_v2.sh --verify-only
USAGE
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dmg)        ARG_DMG="${2:-}"; shift 2 ;;
        --config)     ARG_CONFIG="${2:-}"; shift 2 ;;
        --brew)       MODE_DMG=0; shift ;;
        --system)     MODE_SYSTEM=1; shift ;;
        --no-repair)  ALLOW_REPAIR=0; shift ;;
        --verify-only) VERIFY_ONLY=1; shift ;;
        -h|--help)    usage; exit 0 ;;
        *) echo "Opsi tidak dikenal: $1"; usage; exit 2 ;;
    esac
done

# ------------------------------------------------------------
# Helper output
# ------------------------------------------------------------
if [ -t 1 ]; then
    GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
    CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
else
    GREEN=''; YELLOW=''; RED=''; CYAN=''; BOLD=''; NC=''
fi

ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[GAGAL]${NC} $1"; }
info() { echo -e "      $1"; }
step() { echo ""; echo -e "${CYAN}${BOLD}==>${NC} ${BOLD}$1${NC}"; }
die()  { err "$1"; exit 1; }

banner() {
    echo -e "${CYAN}==================================================${NC}"
    echo -e "${CYAN}  SEB Bypass Installer - macOS (one-command)  v2${NC}"
    echo -e "${CYAN}  SEB ${SEB_VERSION} + VM/AltTab bypass + Cmd+Tab${NC}"
    echo -e "${CYAN}==================================================${NC}"
}

sha256_of() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        openssl sha256 "$1" | awk '{print $NF}'
    fi
}

bytes_of() {
    if stat -f %z "$1" >/dev/null 2>&1; then
        stat -f %z "$1"
    else
        wc -c < "$1" | tr -d ' '
    fi
}

banner

# ------------------------------------------------------------
# 1/5 - Cek sistem
# ------------------------------------------------------------
step "1/5 - Cek sistem"

if [ "$(uname -s)" != "Darwin" ]; then
    die "Script ini untuk macOS. Di Linux/Windows pakai installer Windows."
fi

ARCH="$(uname -m)"
OSVER="$(sw_vers -productVersion 2>/dev/null || echo '?')"
OSMAJ="${OSVER%%.*}"

ok "macOS ${OSVER} (${ARCH})"

case "$ARCH" in
    arm64)  ok "Apple Silicon - DMG 3.7.1 universal, jalan native" ;;
    x86_64) ok "Intel - DMG 3.7.1 universal, jalan native" ;;
    *)      warn "Arsitektur ${ARCH} belum teruji - lanjut dengan risiko" ;;
esac

# lockdownModePolicy wajib di macOS 12.1+: SEB memakai AAC
# Assessment Mode yang MENGABAIKAN allowSwitchToApplications
# dan enableAltTab. Tanpa kunci itu, Cmd+Tab tidak berefek.
if [ "${OSMAJ:-0}" -ge 12 ] 2>/dev/null; then
    info "macOS ${OSMAJ} terdeteksi: kunci lockdownModePolicy"
    info "wajib = 1 (EnforceClassic). Kalau tidak, Cmd+Tab diam."
fi

# ------------------------------------------------------------
# 2/5 - Install aplikasi SEB
# ------------------------------------------------------------
step "2/5 - Install Safe Exam Browser ${SEB_VERSION}"

install_from_dmg() {
    local dmg="$1" mnt rc=0

    mnt="$(mktemp -d "${TMPDIR:-/tmp}/sebdmg.XXXXXX")" || return 1

    if ! hdiutil attach -nobrowse -quiet -mountpoint "$mnt" "$dmg" \
            >/dev/null 2>&1; then
        rmdir "$mnt" 2>/dev/null
        # Fallback: biarkan hdiutil pilih mount point sendiri
        local out
        out="$(hdiutil attach -nobrowse "$dmg" 2>/dev/null | tail -1)"
        mnt="$(printf '%s' "$out" | awk -F'\t' '{print $NF}')"
        [ -d "$mnt" ] || return 1
    fi

    local src=""
    [ -d "${mnt}/${APP_NAME}" ] && src="${mnt}/${APP_NAME}"
    if [ -z "$src" ]; then
        src="$(find "$mnt" -maxdepth 2 -name "$APP_NAME" \
                -type d 2>/dev/null | head -1)"
    fi

    if [ -z "$src" ]; then
        err "  ${APP_NAME} tidak ada di dalam DMG"
        hdiutil detach -quiet "$mnt" >/dev/null 2>&1 || true
        return 1
    fi

    if pgrep -f "Safe Exam Browser" >/dev/null 2>&1; then
        warn "  SEB sedang berjalan - menutupnya dulu"
        osascript -e 'quit app "Safe Exam Browser"' >/dev/null 2>&1
        sleep 2
    fi

    if [ -w /Applications ]; then
        rm -rf "$SEB_APP" 2>/dev/null
        ditto "$src" "$SEB_APP" || rc=1
    else
        info "  /Applications butuh izin - memakai sudo"
        sudo rm -rf "$SEB_APP" 2>/dev/null
        sudo ditto "$src" "$SEB_APP" || rc=1
    fi

    hdiutil detach -quiet "$mnt" >/dev/null 2>&1 || true
    rmdir "$mnt" 2>/dev/null || true
    return $rc
}

APP_SRC=""

if [ -n "$ARG_DMG" ]; then
    [ -f "$ARG_DMG" ] || die "File DMG tidak ditemukan: $ARG_DMG"
    info "Pakai DMG lokal: $ARG_DMG"
    if [ "$(sha256_of "$ARG_DMG")" != "$DMG_SHA256" ]; then
        warn "  SHA-256 DMG lokal tidak cocok dengan rilis resmi"
        info "  (lokakarya/custom build - tetap dipakai atas permintaan)"
    else
        ok "  SHA-256 DMG lokal cocok"
    fi
    APP_SRC="$ARG_DMG"
elif [ "$MODE_DMG" -eq 1 ]; then
    if [ -f "./${DMG_NAME}" ]; then
        info "Menemukan ${DMG_NAME} di folder ini"
        if [ "$(sha256_of "./${DMG_NAME}")" = "$DMG_SHA256" ]; then
            ok "  SHA-256 cocok - pakai file lokal"
            APP_SRC="./${DMG_NAME}"
        else
            warn "  SHA-256 lokal beda - akan unduh ulang dari resmi"
        fi
    fi

    if [ -z "$APP_SRC" ]; then
        TMP_DMG="${TMPDIR:-/tmp}/${DMG_NAME}"
        info "Mengunduh DMG resmi (ETH Zurich / GitHub releases)"
        info "  ${DMG_URL_OFFICIAL}"
        if curl -fL --retry 3 --connect-timeout 20 --progress-bar \
                "$DMG_URL_OFFICIAL" -o "$TMP_DMG"; then
            GOT="$(sha256_of "$TMP_DMG")"
            SZ="$(bytes_of "$TMP_DMG")"
            if [ "$GOT" != "$DMG_SHA256" ]; then
                err "  SHA-256 DMG tidak cocok"
                info "  Harusnya : ${DMG_SHA256}"
                info "  Diterima : ${GOT}"
                rm -f "$TMP_DMG"
                die "Unduhan DMG korup - coba lagi atau pakai --brew"
            fi
            ok "  SHA-256 cocok (${SZ} byte)"
            APP_SRC="$TMP_DMG"
        else
            warn "  Unduhan DMG resmi gagal"
            if [ "$ALLOW_REPAIR" -eq 1 ]; then
                info "  Beralih ke jalur Homebrew cask"
                MODE_DMG=0
            else
                die "Gagal unduh DMG dan fallback dimatikan"
            fi
        fi
    fi
fi

if [ "$VERIFY_ONLY" -eq 1 ]; then
    ok "Mode --verify-only: tahap install SEB dilewati."
    info "Tidak ada perubahan pada sistem. Lanjut ke verifikasi."
elif [ "$MODE_DMG" -eq 0 ]; then
    step "2b/5 - Jalur Homebrew cask"
    BREW=""
    if command -v brew >/dev/null 2>&1; then
        BREW="$(command -v brew)"
    elif [ -x /opt/homebrew/bin/brew ]; then
        BREW="/opt/homebrew/bin/brew"
    elif [ -x /usr/local/bin/brew ]; then
        BREW="/usr/local/bin/brew"
    fi

    if [ -z "$BREW" ]; then
        if ! xcode-select -p >/dev/null 2>&1; then
            info "  Memasang Xcode Command Line Tools (prasyarat Homebrew)"
            info "  Kalau muncul dialog GUI, klik Install."
            xcode-select --install >/dev/null 2>&1
            for _ in $(seq 1 60); do
                xcode-select -p >/dev/null 2>&1 && break
                sleep 5
            done
            xcode-select -p >/dev/null 2>&1 \
                || die "Xcode CLT tidak terpasang"
        fi
        ok "  Xcode CLT siap"
        info "  Memasang Homebrew..."
        /bin/bash -c "$(curl -fsSL \
          https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
          </dev/null
        if [ -x /opt/homebrew/bin/brew ]; then
            BREW="/opt/homebrew/bin/brew"
        elif [ -x /usr/local/bin/brew ]; then
            BREW="/usr/local/bin/brew"
        else
            die "Homebrew gagal terpasang"
        fi
    fi
    ok "Homebrew: ${BREW}"
    export PATH="$(dirname "$BREW"):${PATH}"

    if [ -d "$SEB_APP" ]; then
        CUR="$(defaults read "${SEB_APP}/Contents/Info.plist" \
                CFBundleShortVersionString 2>/dev/null || echo '?')"
        if [ "$CUR" = "$SEB_VERSION" ]; then
            ok "  SEB ${CUR} sudah terpasang - skip"
        else
            warn "  SEB ${CUR} terdeteksi - upgrade ke ${SEB_VERSION}"
            "$BREW" install --cask "$BREW_CASK" || {
                "$BREW" reinstall --cask "$BREW_CASK" \
                  || die "Upgrade cask gagal"
            }
        fi
    else
        "$BREW" install --cask "$BREW_CASK" \
          || die "brew install --cask ${BREW_CASK} gagal"
    fi
elif [ -n "$APP_SRC" ]; then
    info "Memasang dari DMG..."
    install_from_dmg "$APP_SRC" || die "Pemasangan dari DMG gagal"
    rm -f "$APP_SRC" 2>/dev/null || true
fi

if [ ! -d "$SEB_APP" ]; then
    if [ "$VERIFY_ONLY" -eq 1 ]; then
        warn "SEB app tidak ada di /Applications"
    else
        die "SEB app tidak ada di /Applications"
    fi
fi

INSTALLED_VER="$(defaults read "${SEB_APP}/Contents/Info.plist" \
                  CFBundleShortVersionString 2>/dev/null || echo '?')"
ok "SEB ${INSTALLED_VER} terpasang di /Applications"

if [ "$INSTALLED_VER" != "$SEB_VERSION" ]; then
    warn "Versi terpasang ${INSTALLED_VER} != ${SEB_VERSION} yang diuji"
fi

# Buang atribut quarantine supaya Gatekeeper tidak menghalangi
if command -v xattr >/dev/null 2>&1; then
    xattr -dr com.apple.quarantine "$SEB_APP" >/dev/null 2>&1 || true
fi

# ------------------------------------------------------------
# 3/5 - Ambil config bypass
# ------------------------------------------------------------
step "3/5 - Ambil config bypass"

SRC_CONFIG=""
TMP_CFG=""

if [ -n "$ARG_CONFIG" ]; then
    [ -f "$ARG_CONFIG" ] || die "Config tidak ditemukan: $ARG_CONFIG"
    SRC_CONFIG="$ARG_CONFIG"
    info "Pakai config lokal: $SRC_CONFIG"
elif [ -f "./${CONFIG_NAME}" ]; then
    if [ "$(sha256_of "./${CONFIG_NAME}")" = "$CONFIG_SHA256" ]; then
        SRC_CONFIG="./${CONFIG_NAME}"
        ok "Config lokal di folder ini - SHA-256 cocok"
    else
        warn "Config lokal SHA-256 beda - akan unduh dari repo"
    fi
fi

if [ -z "$SRC_CONFIG" ]; then
    TMP_CFG="$(mktemp "${TMPDIR:-/tmp}/sebconfig.XXXXXX")" || die "mktemp gagal"
    info "Mengunduh ${CONFIG_NAME} dari repo"
    if curl -fsSL --retry 3 --connect-timeout 20 \
            "$CONFIG_URL" -o "$TMP_CFG"; then
        SRC_CONFIG="$TMP_CFG"
    else
        warn "  Gagal dari raw.githubusercontent.com"
        if curl -fsSL --retry 2 --connect-timeout 20 \
                "https://github.com/harezadmm/seb-bypass/raw/main/${CONFIG_NAME}" \
                -o "$TMP_CFG"; then
            ok "  Berhasil lewat jalur github.com"
            SRC_CONFIG="$TMP_CFG"
        else
            rm -f "$TMP_CFG"
            die "Unduh config gagal - cek koneksi internet"
        fi
    fi
fi

CFG_SHA="$(sha256_of "$SRC_CONFIG")"
if [ "$CFG_SHA" != "$CONFIG_SHA256" ]; then
    err "SHA-256 config TIDAK COCOK - instalasi dibatalkan"
    info "Harusnya : ${CONFIG_SHA256}"
    info "Diterima : ${CFG_SHA}"
    [ -n "$TMP_CFG" ] && rm -f "$TMP_CFG"
    die "Config bukan rilis yang benar"
fi
ok "SHA-256 config cocok (${CFG_SHA%${CFG_SHA#????????????????}}...)"

# Config harus plist XML yang bisa dibaca plutil
if command -v plutil >/dev/null 2>&1; then
    plutil -lint "$SRC_CONFIG" >/dev/null 2>&1 \
      || die "Config bukan plist yang valid"
    ok "Struktur plist valid"
fi

# ------------------------------------------------------------
# 4/5 - Deploy config
# ------------------------------------------------------------
step "4/5 - Deploy config ke ~/Library/Preferences"

# SEB membaca /Library/Preferences/ DULU. Kalau file sistem ada,
# file user DIABAIKAN sepenuhnya. Cek dulu supaya tidak salah kira.
if [ -f "$SYSTEM_PREF" ]; then
    SYS_SHA="$(sha256_of "$SYSTEM_PREF")"
    if [ "$SYS_SHA" = "$CONFIG_SHA256" ]; then
        ok "Config sistem ada dan BENAR - dipakai SEB"
        info "  ${SYSTEM_PREF}"
    else
        warn "Config sistem ada TAPI BERBEDA - SEB pakai file ini,"
        info "  bukan config user. Bypass bisa tidak aktif."
        info "  ${SYSTEM_PREF}"
        info "  sha256: ${SYS_SHA}"
        if [ "$MODE_SYSTEM" -eq 0 ]; then
            info "  Perbaiki dengan: bash \"\$0\" --system"
            case "$0" in
                bash|sh|-bash|/bin/bash|/bin/sh)
                    info "  Catatan: dijalankan via 'curl ... | bash', jadi \$0 bukan nama file."
                    info "  Simpan skrip ke file dulu, baru jalankan dengan --system." ;;
            esac
        fi
    fi
fi

if [ "$VERIFY_ONLY" -eq 1 ]; then
    info "Mode --verify-only: tidak mengubah apa pun"
    [ -n "$TMP_CFG" ] && rm -f "$TMP_CFG"
else
    if pgrep -f "Safe Exam Browser" >/dev/null 2>&1; then
        warn "SEB sedang berjalan"
        info "Config dibaca HANYA saat SEB start."
        info "Perubahan berlaku setelah SEB di-restart."
    fi

    mkdir -p "$HOME/Library/Preferences"

    if [ -f "$CONFIG_DEST" ]; then
        BAK="${CONFIG_DEST}.bak.$(date +%Y%m%d%H%M%S)"
        cp "$CONFIG_DEST" "$BAK" && ok "Config lama dibackup: $(basename "$BAK")"
    fi

    # Salin atomik: tulis ke .tmp lalu pindahkan
    TMP_DEST="${CONFIG_DEST}.tmp.$$"
    cp "$SRC_CONFIG" "$TMP_DEST" || die "Gagal menulis config"
    mv -f "$TMP_DEST" "$CONFIG_DEST" || die "Gagal memasang config"
    ok "Config terpasang: ${CONFIG_DEST}"
    [ -n "$TMP_CFG" ] && rm -f "$TMP_CFG"

    # Bersihkan cache defaults lama supaya SEB baca file baru
    defaults delete "$DOMAIN" >/dev/null 2>&1 \
      && ok "defaults lama (${DOMAIN}) dihapus" \
      || info "Tidak ada defaults lama untuk dihapus"
    killall cfprefsd >/dev/null 2>&1 || true
    ok "Cache preferensi (cfprefsd) di-flush"

    if [ "$MODE_SYSTEM" -eq 1 ]; then
        echo ""
        info "Memasang config sistem di ${SYSTEM_PREF_DIR}"
        info "  (butuh sudo - akan muncul prompt password)"
        if sudo mkdir -p "$SYSTEM_PREF_DIR" && \
           sudo cp "$CONFIG_DEST" "${SYSTEM_PREF}.tmp.$$" && \
           sudo mv -f "${SYSTEM_PREF}.tmp.$$" "$SYSTEM_PREF" && \
           sudo chmod 644 "$SYSTEM_PREF"; then
            ok "Config sistem terpasang"
            sudo killall cfprefsd >/dev/null 2>&1 || true
        else
            warn "Config sistem gagal dipasang - lanjut dengan config user"
        fi
    fi
fi

# ------------------------------------------------------------
# 5/5 - Verifikasi + perbaikan kunci (Cmd+Tab)
# ------------------------------------------------------------
step "5/5 - Verifikasi kunci bypass"

# Tentukan file config EFEKTIF: SEB memprioritaskan /Library/Preferences/.
# Verifikasi harus menguji file yang benar-benar dipakai SEB, bukan
# file user yang mungkin diabaikan.
EFFECTIVE="$CONFIG_DEST"
PLSET_SUDO=""
if [ -f "$SYSTEM_PREF" ] && \
   [ "$(sha256_of "$SYSTEM_PREF")" = "$CONFIG_SHA256" ]; then
    EFFECTIVE="$SYSTEM_PREF"
    PLSET_SUDO="sudo"
    info "SEB memakai config SISTEM: ${SYSTEM_PREF}"
    info "Config user diabaikan selama file sistem ada."
fi

[ -f "$EFFECTIVE" ] || die "Config belum ada di ${EFFECTIVE}"

# Baca nilai kunci dari plist. plutil dulu, PlistBuddy cadangan.
plist_get() {
    local f="$1" k="$2" v=""
    if command -v plutil >/dev/null 2>&1; then
        v="$(plutil -extract "$k" raw -o - "$f" 2>/dev/null)"
    fi
    if [ -z "$v" ] && [ -x /usr/libexec/PlistBuddy ]; then
        v="$(/usr/libexec/PlistBuddy -c "Print :${k}" "$f" 2>/dev/null)"
    fi
    printf '%s' "$v"
}

# Set bool. Coba -replace dulu; kalau kunci BELUM ADA di plist,
# plutil -replace GAGAL, jadi jatuh ke -insert / PlistBuddy Add.
plist_set_bool() {
    local f="$1" k="$2" val="$3" b
    if [ "$val" = "true" ]; then b=YES; else b=NO; fi
    if command -v plutil >/dev/null 2>&1; then
        $PLSET_SUDO plutil -replace "$k" -bool "$b" "$f" >/dev/null 2>&1 \
            && return 0
        $PLSET_SUDO plutil -insert "$k" -bool "$b" "$f" >/dev/null 2>&1 \
            && return 0
    fi
    if [ -x /usr/libexec/PlistBuddy ]; then
        $PLSET_SUDO /usr/libexec/PlistBuddy -c "Set :${k} ${val}" "$f" \
            >/dev/null 2>&1 && return 0
        $PLSET_SUDO /usr/libexec/PlistBuddy -c "Add :${k} bool ${val}" "$f" \
            >/dev/null 2>&1 && return 0
    fi
    return 1
}

# Set integer. Sama: -replace dulu, -insert kalau kunci belum ada.
plist_set_int() {
    local f="$1" k="$2" val="$3"
    if command -v plutil >/dev/null 2>&1; then
        $PLSET_SUDO plutil -replace "$k" -integer "$val" "$f" \
            >/dev/null 2>&1 && return 0
        $PLSET_SUDO plutil -insert "$k" -integer "$val" "$f" \
            >/dev/null 2>&1 && return 0
    fi
    if [ -x /usr/libexec/PlistBuddy ]; then
        $PLSET_SUDO /usr/libexec/PlistBuddy -c "Set :${k} ${val}" "$f" \
            >/dev/null 2>&1 && return 0
        $PLSET_SUDO /usr/libexec/PlistBuddy -c "Add :${k} integer ${val}" "$f" \
            >/dev/null 2>&1 && return 0
    fi
    return 1
}

KEYS_TOTAL=20
KEYS_OK=0
KEYS_FIXED=0

verify_bool() {
    local key="$1" expect="$2" label="$3" got
    got="$(plist_get "$EFFECTIVE" "$key")"
    if [ "$got" = "$expect" ]; then
        ok "${key} = ${expect}    (${label})"
        KEYS_OK=$((KEYS_OK+1))
        return 0
    fi
    warn "${key} = ${got:-<kosong>} (harusnya ${expect})"
    if [ "$ALLOW_REPAIR" -eq 1 ] && [ "$VERIFY_ONLY" -eq 0 ]; then
        if plist_set_bool "$EFFECTIVE" "$key" "$expect"; then
            got="$(plist_get "$EFFECTIVE" "$key")"
            if [ "$got" = "$expect" ]; then
                ok "${key} diperbaiki = ${expect}    (${label})"
                KEYS_FIXED=$((KEYS_FIXED+1))
                KEYS_OK=$((KEYS_OK+1))
                return 0
            fi
        fi
    fi
    err "${key} tetap salah - ${label} TIDAK aktif"
    return 1
}

verify_int() {
    local key="$1" expect="$2" label="$3" got
    got="$(plist_get "$EFFECTIVE" "$key")"
    if [ "$got" = "$expect" ]; then
        ok "${key} = ${expect}    (${label})"
        KEYS_OK=$((KEYS_OK+1))
        return 0
    fi
    warn "${key} = ${got:-<kosong>} (harusnya ${expect})"
    if [ "$ALLOW_REPAIR" -eq 1 ] && [ "$VERIFY_ONLY" -eq 0 ]; then
        if plist_set_int "$EFFECTIVE" "$key" "$expect"; then
            got="$(plist_get "$EFFECTIVE" "$key")"
            if [ "$got" = "$expect" ]; then
                ok "${key} diperbaiki = ${expect}    (${label})"
                KEYS_FIXED=$((KEYS_FIXED+1))
                KEYS_OK=$((KEYS_OK+1))
                return 0
            fi
        fi
    fi
    err "${key} tetap salah - ${label} TIDAK aktif"
    return 1
}

# --- KUNCI INERT: enableAltTab terdaftar di SEBSettings.m:530-531 dan punya
#     checkbox di PreferencesSecurity.xib:1979, TETAPI tidak ada satu pun
#     berkas .m yang membacanya. Di macOS kunci ini TIDAK BERPENGARUH -- sisa
#     dari basis kode Windows. Diset true hanya demi kompatibilitas.
#     Yang benar-benar menentukan Cmd+Tab adalah allowSwitchToApplications:
#     saat true, SEB memakai cabang kiosk longgar SEBController.m:7851-7857
#     yang TIDAK memasang NSApplicationPresentationDisableProcessSwitching.
verify_bool enableAltTab true              "kompatibilitas (INERT di macOS)"
verify_bool allowSwitchToApplications true "boleh pindah aplikasi (Cmd+Tab)"
verify_bool enableAppSwitcherCheck false   "cek app-switcher dimatikan"
verify_bool allowVirtualMachine true       "bypass deteksi VM"

# --- BYPASS DETEKSI MULTI-SCREEN
#     Penegak: SEBController.m:5345 conditionallyTerminateDisplayMirroring.
#     Default kunci ada di SEBSettings.m:202-217.
#
#     allowedDisplaysMaxNumber (default 1) -- SEBController.m:5504-5515:
#         NSUInteger displaysCounter = (mainScreen != nil);   // = 1
#         if (displaysCounter < maxAllowedDisplays) { aktif } else { inactive }
#       Dengan nilai 1, layar kedua dan seterusnya ditandai INACTIVE.
#       WAJIB diverifikasi lewat log SEB, bukan diasumsikan berhasil:
#         - baris "Current Settings: Maximum allowed displays: N"
#         - TIDAK boleh ada baris "Flagged screen ... as inactive"
#
#     allowDisplayMirroring (default @NO) -- SEBController.m:5400-5424:
#       SEB MEMBONGKAR mirroring secara paksa via CGConfigureDisplayMirrorOfDisplay
#       begitu mirroring terdeteksi.
#
#     allowedDisplayBuiltin (default @YES) -- SEBController.m:5450: memaksa
#       display built-in sebagai layar utama.
#     allowedDisplayBuiltinEnforce (default @YES) -- SEBController.m:5464:
#       bila built-in tidak ada -> noRequiredBuiltInScreenAvailable = YES (:5469)
#       -> notifikasi detectedRequiredBuiltinDisplayMissing (:5524) -> kunci layar.
#
#     CATATAN: allowedDisplaysIgnoreFailure terdaftar di SEBSettings.m:214 dan
#     punya checkbox di XIB, tetapi TIDAK PERNAH DIBACA oleh kode mana pun.
#     Inert -- jangan diandalkan sebagai jaring pengaman.
verify_int  allowedDisplaysMaxNumber 16         "izinkan banyak layar (default 1 = layar ke-2 dimatikan)"
verify_bool allowDisplayMirroring true          "izinkan display mirroring"
verify_bool allowedDisplayBuiltin false         "display built-in tidak diwajibkan"
verify_bool allowedDisplayBuiltinEnforce false  "penegakan display built-in dimatikan"

# --- BYPASS PEMICU KELUAR OTOMATIS
#     SEBController.m punya beberapa jalur yang membuat SEB KELUAR SENDIRI.
#     Semuanya hanya membaca config - tidak ada yang perlu di-patch di macOS.
#       :4323-4324  allowScreenSharing = allowScreenSharing && !screenSharingMacEnforceBlocked
#       :4327       if (!allowScreenSharing && (ScreensharingAgent || AppleVNCServer))
#                       -> "Screen Sharing Detected!" + SEB keluar
#       :4319       allowDictation dibaca
#       :4340       if (!allowSiri && SiriService && Siri aktif)
#                       -> "Siri Detected!" + SEB keluar
#     KEDUA kunci screen sharing harus benar: :4323 adalah AND, :4324 adalah NOT.
verify_bool allowScreenSharing true              "izinkan screen sharing (false = SEB keluar)"
verify_bool screenSharingMacEnforceBlocked false "jangan paksa blokir screen sharing"
verify_bool allowSiri true                       "izinkan Siri (false = SEB keluar)"
verify_bool allowDictation true                  "izinkan dictation"

# --- KUNCI AAC + CAPTURE
#     allowWindowCapture=true adalah kunci AAC: SEBController.m:7731 menghitung
#     _isAACEnabled = !screenCapture && !windowCapture && !screenSharing && ...
#     Dengan capture diizinkan, AAC mati, dan blok penegakan window (:4972) dilewati -
#     itu yang membebaskan screenshot dan CleanShot X.
verify_bool allowWindowCapture true              "kunci AAC - screenshot & CleanShot X"
verify_bool allowScreenCapture true              "izinkan screen capture"
verify_bool detectAccessibilityApps false        "jangan bunuh app accessibility (CleanShot X)"
verify_bool autoQuitApplications false           "jangan auto-quit aplikasi lain"
verify_bool allowDictionaryLookup true           "izinkan dictionary lookup"
verify_bool enablePrintScreen true               "izinkan PrintScreen"
verify_bool browserWindowAllowAddressBar true    "tampilkan address bar"

# --- lockdownModePolicy = 1 (EnforceClassic).
#     macOS 12.1+ default AAC Assessment Mode -> kunci di atas
#     diabaikan. Nilai 1 memaksa kiosk klasik.
POLICY="$(plist_get "$EFFECTIVE" lockdownModePolicy)"
if [ "$POLICY" = "1" ]; then
    ok "lockdownModePolicy = 1    (EnforceClassic, AAC off)"
    KEYS_OK=$((KEYS_OK+1))
else
    warn "lockdownModePolicy = ${POLICY:-<kosong>} (harusnya 1)"
    if [ "$ALLOW_REPAIR" -eq 1 ] && [ "$VERIFY_ONLY" -eq 0 ]; then
        if plist_set_int "$EFFECTIVE" lockdownModePolicy 1; then
            POLICY="$(plist_get "$EFFECTIVE" lockdownModePolicy)"
            if [ "$POLICY" = "1" ]; then
                ok "lockdownModePolicy diperbaiki = 1"
                KEYS_FIXED=$((KEYS_FIXED+1))
                KEYS_OK=$((KEYS_OK+1))
            fi
        fi
    fi
    [ "$POLICY" = "1" ] || err "lockdownModePolicy tetap salah"
fi

# --- Kunci tambahan (informasi, tidak menggagalkan instalasi)
echo ""
echo "  Status kunci lain (informasi):"
for k in enableEsc enableCtrlEsc enableAltEsc allowQuit \
         allowPreferencesWindow browserWindowAllowReload; do
    v="$(plist_get "$EFFECTIVE" "$k")"
    printf '    %-30s %s\n' "$k" "${v:-<tidak ada>}"
done

# ------------------------------------------------------------
# Hasil
# ------------------------------------------------------------
echo ""
if [ "$KEYS_OK" -eq "$KEYS_TOTAL" ]; then
    echo -e "${GREEN}${BOLD}==================================================${NC}"
    echo -e "${GREEN}${BOLD}     SUKSES - SEB ${SEB_VERSION} + BYPASS AKTIF${NC}"
    echo -e "${GREEN}${BOLD}==================================================${NC}"
    echo ""
    echo "  Terpasang:"
    echo "   - Safe Exam Browser ${INSTALLED_VER} -> ${SEB_APP}"
    echo "   - Config bypass   -> ${EFFECTIVE}"
    [ "$EFFECTIVE" != "$CONFIG_DEST" ] && \
        echo "     (config SISTEM menang atas config user)"
    [ "$KEYS_FIXED" -gt 0 ] && \
        echo "   - ${KEYS_FIXED} kunci diperbaiki otomatis"
    echo ""
    echo "  Fitur aktif:"
    echo "   - Cmd+Tab  : ganti aplikasi (app switcher macOS)"
    echo "                allowSwitchToApplications=true   <- INI penentunya"
    echo "                + enableAppSwitcherCheck=false"
    echo "                (enableAltTab INERT di macOS: terdaftar + ada"
    echo "                 checkbox, tapi nol pembaca di kode. Diset demi"
    echo "                 kompatibilitas saja.)"
    echo "   - Multi-layar: allowedDisplaysMaxNumber=16"
    echo "                  allowDisplayMirroring=true"
    echo "                  allowedDisplayBuiltin=false"
    echo "                  allowedDisplayBuiltinEnforce=false"
    echo "   - Anti-keluar: allowScreenSharing=true"
    echo "                  screenSharingMacEnforceBlocked=false"
    echo "                  allowSiri=true / allowDictation=true"
    echo "                  (tanpa ini SEB keluar sendiri saat deteksi"
    echo "                   screen sharing / Siri)"
    echo "   - Screenshot : allowWindowCapture=true (kunci AAC)"
    echo "                  allowScreenCapture=true"
    echo "                  detectAccessibilityApps=false"
    echo "                  (CleanShot X dibebaskan)"
    echo "   - Cmd+Q    : keluar aplikasi (allowQuit)"
    echo "   - VM bypass: allowVirtualMachine=true"
    echo "   - Kiosk klasik: lockdownModePolicy=1 (AAC dimatikan)"
    echo ""
    echo "  Cara tes:"
    echo "   1. Tutup SEB kalau sedang jalan (config dibaca saat start)"
    echo "   2. Buka SEB, masuk ke halaman ujian"
    echo "   3. Tekan Cmd+Tab -> harus muncul app switcher macOS"
    echo "   4. Colok monitor kedua / aktifkan Sidecar"
    echo "      -> SEB TIDAK boleh menampilkan kunci layar"
    echo "      -> cek log: maksimal display harus 16, dan tidak ada"
    echo "         baris 'Flagged screen ... as inactive'"
    echo ""
    echo "  Kalau Cmd+Tab masih terkunci:"
    echo "   - Pastikan macOS >= 12.1 dan lockdownModePolicy = 1"
    echo "   - Tutup SEB sepenuhnya, lalu buka ulang"
    echo ""
    echo -e "${YELLOW}  Catatan:${NC} macOS SEB itu app bertanda tangan +"
    echo "  hardened runtime, jadi bypass lewat CONFIG, bukan patch"
    echo "  biner. Kalau server ujian mengirim konfigurasi sendiri,"
    echo "  config lokal bisa ditimpa saat ujian mulai."
    echo ""
else
    err "${KEYS_OK}/${KEYS_TOTAL} kunci benar - TIDAK semua fitur aktif"
    echo ""
    echo "  Perbaiki manual:"
    echo "    plutil -replace lockdownModePolicy -integer 1 \"${EFFECTIVE}\""
    echo "    plutil -replace allowedDisplaysMaxNumber -integer 16 \"${EFFECTIVE}\""
    echo "    plutil -replace allowDisplayMirroring -bool YES \"${EFFECTIVE}\""
    echo "    plutil -replace allowedDisplayBuiltin -bool NO \"${EFFECTIVE}\""
    echo "    plutil -replace allowedDisplayBuiltinEnforce -bool NO \"${EFFECTIVE}\""
    echo "    killall cfprefsd"
    echo ""
    exit 1
fi

# ------------------------------------------------------------
# Troubleshooting
# ------------------------------------------------------------
echo "  Troubleshooting:"
echo "   - 'bad CPU type'          : DMG 3.7.1 universal (x86_64+arm64)"
echo "   - Cmd+Tab tetap terkunci  : lockdownModePolicy harus 1;"
echo "                               tutup SEB dulu sebelum re-run"
echo "   - Layar ke-2 tetap mati   : allowedDisplaysMaxNumber harus >= 16."
echo "                               Kalau file CONFIG UJIAN juga memuat"
echo "                               kunci ini (default 1), config ujian"
echo "                               MENANG atas config ini - patch juga"
echo "                               file .seb ujiannya."
echo "   - Config user diabaikan   : cek /Library/Preferences/"
echo "                               SebClientSettings.seb - kalau ada,"
echo "                               itu yang dipakai SEB. Perbaiki:"
echo "                               bash $0 --system"
echo "   - Config tidak terbaca    : killall cfprefsd lalu buka SEB lagi"
echo "   - 'Config SHA tidak cocok': file config di repo berubah;"
echo "                               jangan lanjut, ambil config resmi"
echo "   - SEB tidak bisa dibuka   : System Settings -> Privacy &"
echo "                               Security -> Open Anyway"
echo "   - Mau jalur Homebrew      : bash $0 --brew"
echo "   - Mau pakai DMG lokal     : bash $0 --dmg <path>"
echo ""
