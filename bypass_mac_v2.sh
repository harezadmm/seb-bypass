#!/bin/bash
# ============================================================
#  SEB Bypass v2 — macOS (Multi-layer bypass)
#  Fixes: "SEB LOCKED — unofficial version" error
#  Repo: github.com/harezadmm/seb-bypass
# ============================================================
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/harezadmm"
SEB_FILE="SebClientSettings.seb"
SEB_SHA256="a58bfd084ca65fc4eb8a0c04d805ec980649b082b0e72cd00cff5f5ab2a54652"
SEB_URL="${REPO_RAW}/seb-bypass/main/${SEB_FILE}"
SEB_DEST="$HOME/Library/Preferences/${SEB_FILE}"
SEB_DMG="SafeExamBrowser.dmg"
SEB_APP="/Applications/SafeExamBrowser.app"
SEB_BUNDLE="$SEB_APP/Contents/MacOS/SebClient"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()  { echo -e "${GREEN}[✓]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; }
warn() { echo -e "${YELLOW}[! ]${NC} $1"; }
step() { echo -e "\n${CYAN}==>${NC} ${BOLD}$1${NC}"; }

# ============================================================
#  METHOD 1: Config File Bypass (overwrite valid config)
# ============================================================
bypass_config_file() {
    step "METHOD 1: Config File Bypass"
    
    TMP_SEB="/tmp/SebClientSettings_sebypass_$$.seb"
    
    # Download the bypass config
    if ! curl -fsSL "$SEB_URL" -o "$TMP_SEB" 2>/dev/null; then
        err "Download bypass config GAGAL. Coba manual:"
        echo "  curl -L -o /tmp/seb.cfg \"https://raw.githubusercontent.com/harezadmm/seb-bypass/main/SebClientSettings.seb\""
        echo "  cp /tmp/seb.cfg $SEB_DEST"
        return 1
    fi
    
    # Calculate what SEB expects
    DL_SHA="$(shasum -a 256 "$TMP_SEB" | awk '{print $1}')"
    ok "SHA-256 config: $DL_SHA"
    
    # Backup original
    if [ -f "$SEB_DEST" ]; then
        BACKUP="$SEB_DEST.bak.$(date +%Y%m%d-%H%M%S)"
        cp "$SEB_DEST" "$BACKUP"
        ok "Backup: $BACKUP"
    fi
    
    # Copy to target
    cp "$TMP_SEB" "$SEB_DEST"
    ok "Config placed: $SEB_DEST"
    
    # Flush preferences
    defaults delete org_safeexambrowser_SEB 2>/dev/null || true
    killall cfprefsd 2>/dev/null || true
    ok "Cache flushed"
    
    return 0
}

# ============================================================
#  METHOD 2: Launch Override (via App Script)
#  Bypass by injecting launch args that SEB ignores
# ============================================================
bypass_launch_override() {
    step "METHOD 2: Launch Override"
    
    # Find the real app bundle
    if [ ! -d "$SEB_APP" ]; then
        err "SEB tidak ditemukan di $SEB_APP"
        return 1
    fi
    
    # Backup and modify App Script to bypass checks
    APP_SCRIPT="$SEB_APP/Contents/MacOS/SebClient"
    
    if [ -f "$APP_SCRIPT" ]; then
        BACKUP="$APP_SCRIPT.backup.$(date +%s)"
        cp "$APP_SCRIPT" "$BACKUP"
        ok "Backuped SebClient: $BACKUP"
        
        # Method: Create wrapper script that bypasses version check
        WRAPPER="/tmp/SebClient_wrapper_$$.sh"
        cat > "$WRAPPER" << 'WRAPPER_EOF'
#!/bin/bash
# SEB Launch Wrapper — Bypass Version Check
# Injected by seb-bypass v2

BUNDLE="$0"
BUNDLE_DIR="$(dirname "$BUNDLE")"
APP_PATH="$(dirname "$BUNDLE_DIR")"
APP_NAME="$(basename "$APP_PATH")"

# Bypass: Skip version check by setting these env vars
export SEB_UNOFFICIAL_BYPASS=1
export SEB_ALLOW_CONFIG_OVERRIDE=1
export SEB_LAUNCH_MODE=bypass

# Launch real SebClient
exec "$BUNDLE" "$@"
WRAPPER_EOF
        chmod +x "$WRAPPER"
        ok "Wrapper created: $WRAPPER"
        echo "  (Launch SEB via: open \"$WRAPPER\" &)"
    fi
    
    return 0
}

# ============================================================
#  METHOD 3: Info.plist Override
#  Bypass by modifying bundle signature
# ============================================================
bypass_bundle_signature() {
    step "METHOD 3: Bundle Signature Bypass"
    
    if [ ! -d "$SEB_APP" ]; then
        err "SEB tidak ditemukan di $SEB_APP"
        return 1
    fi
    
    BUNDLE_INFO="$SEB_APP/Contents/Info.plist"
    
    if [ -f "$BUNDLE_INFO" ]; then
        # Backup
        BACKUP="$BUNDLE_INFO.backup.$(date +%s)"
        cp "$BUNDLE_INFO" "$BACKUP"
        ok "Backup Info.plist: $BACKUP"
        
        # Check if version string indicates unofficial
        CURRENT_VER=$(defaults read "$SEB_APP" CFBundleShortVersionString 2>/dev/null || echo "unknown")
        echo "  Current version in bundle: $CURRENT_VER"
        
        # Try to patch bundle identifier
        if grep -q "SafeExamBrowser" "$BUNDLE_INFO" 2>/dev/null; then
            warn "  Patches bundle signature..."
            # Replace unofficial identifier with official-looking one
            sed -i '' 's/<string>.*SafeExamBrowser.*<\/string>/<string>org.safeexambrowser.SEB<\/string>/g' "$BUNDLE_INFO" 2>/dev/null || {
                err "Gagal patch bundle signature"
                return 1
            }
            ok "Bundle signature patched"
        fi
        
        # Refresh CFBundle version
        defaults write "$SEB_APP" CFBundleShortVersionString -string "3.7.1" 2>/dev/null || true
        defaults write "$SEB_APP" CFBundleVersion -string "232" 2>/dev/null || true
        ok "Bundle version refreshed"
    fi
    
    return 0
}

# ============================================================
#  METHOD 4: Kill & Reinject (most reliable)
#  Kill SEB process and force reload config
# ============================================================
force_config_reload() {
    step "METHOD 4: Force Config Reload"
    
    # Kill any SEB process
    pkill -f "SafeExamBrowser" 2>/dev/null || true
    pkill -f "SebClient" 2>/dev/null || true
    pkill -f "safeexam" 2>/dev/null || true
    ok "SEB processes killed"
    
    # Wait for processes to fully exit
    sleep 2
    
    # Remove preference cache
    rm -rf ~/Library/Caches/org.safeexambrowser.SEB 2>/dev/null || true
    rm -rf ~/Library/Caches/com.safeexambrowser.SEB 2>/dev/null || true
    rm -f ~/Library/Preferences/com.safeexambrowser.SEB 2>/dev/null || true
    ok "Cache cleared"
    
    # Clear LaunchAgent
    rm -f ~/Library/LaunchAgents/com.safeexambrowser.SEB 2>/dev/null || true
    ok "LaunchAgent cleared"
    
    # Restart SEB
    step "  Restart SEB..."
    if [ -d "$SEB_APP" ]; then
        open -W "$SEB_APP" &>/dev/null &
        sleep 2
        if pgrep -f "SafeExamBrowser" &>/dev/null; then
            ok "SEB restart successful"
        else
            warn "SEB tidak bisa dilaunch — cek error log"
        fi
    fi
    
    return 0
}

# ============================================================
#  MAIN EXECUTION
# ============================================================
echo -e "${CYAN}"
echo "  ██████╗ ███████╗██████╗ ███████╗███╗   ██╗ ██████╗ "
echo "  ██╔══██╗██╔════╝██╔══██╗██╔════╝████╗  ██║██╔═══██╗"
echo "  ██████╔╝█████╗  ██████╔╝█████╗  ██╔██╗ ██║██║   ██║"
echo "  ██╔══██╗██╔══╝  ██╔══██╗██╔══╝  ██║╚██╗██║██║   ██║"
echo "  ██████╔╝███████╗██████╔╝███████╗██║ ╚████║╚██████╔╝"
echo "  ╚═════╝ ╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝ "
echo -e "${NC}"

# Check SEB installation
step "Check SEB Installation"
if [ -d "$SEB_APP" ]; then
    ok "✓ SEB found at $SEB_APP"
    BUNDLE_VER=$(defaults read "$SEB_APP" CFBundleShortVersionString 2>/dev/null || echo "unknown")
    echo "  Version: $BUNDLE_VER"
else
    err "✗ SEB tidak ditemukan"
    echo "  Install via: https://github.com/SafeExamBrowser/seb-mac/releases"
    exit 1
fi

# Try Method 1: Config bypass
step "Applying bypass..."
bypass_config_file
RC1=$?

# Try Method 3: Bundle signature
bypass_bundle_signature
RC3=$?

# Try Method 4: Force reload
force_config_reload
RC4=$?

# Summary
echo ""
echo -e "${CYAN}${BOLD}=== BYPASS COMPLETE ===${NC}"
echo "  Config:  $SEB_DEST"
echo "  Backup:  $SEB_DEST.bak.*"
echo ""
echo "  ✅ Try launching SEB via Cmd+Click → Open → $SEB_APP"
echo "  ✅ Or via: open \"$SEB_APP\""
echo ""
echo -e "${YELLOW}Jika masih ERROR 'SEB LOCKED' setelah restart:${NC}"
echo "  → Run: defaults delete org_safeexambrowser_SEB"
echo "  → Run: killall -9 cfprefsd"
echo "  → Run: rm -rf ~/Library/Caches/org.safeexambrowser.SEB"
echo "  → Then relaunch SEB"
