#!/usr/bin/env bash
# Build SEB Config Bypass Studio untuk macOS (.app + .dmg)
# Hasil: build/dist/SEB Config Bypass Studio.app  dan  build/SEB Config Bypass Studio.dmg
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$HERE"

echo "==> SEB Config Bypass Studio - build macOS"
echo "    root : $ROOT"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "ERROR: python3 tidak ditemukan."; exit 1
fi

# 1) venv + pyinstaller
if [ ! -d "$HERE/.venv" ]; then
    echo "==> membuat venv..."
    "$PY" -m venv "$HERE/.venv"
fi
VENV_PY="$HERE/.venv/bin/python"
"$VENV_PY" -m pip install -q --upgrade pip
echo "==> memasang pyinstaller + pillow..."
"$VENV_PY" -m pip install -q pyinstaller pillow

# 2) ikon
if [ ! -f "$HERE/assets/sebstudio.icns" ]; then
    echo "==> membuat ikon..."
    "$VENV_PY" "$HERE/make_icon.py"
fi

# 3) build
echo "==> pyinstaller..."
rm -rf "$HERE/dist" "$HERE/build"
"$VENV_PY" -m PyInstaller --clean --noconfirm "$HERE/seb_bypass_gui.spec"

APP="$HERE/dist/SEB Config Bypass Studio.app"
if [ ! -d "$APP" ]; then
    echo "ERROR: .app tidak terbentuk."; exit 1
fi
echo "==> OK: $APP"

# 4) tanda tangan ad-hoc supaya macOS mau menjalankannya
echo "==> codesign ad-hoc..."
codesign --force --deep --sign - --timestamp=none "$APP" 2>/dev/null || true
codesign --verify --verbose=1 "$APP" 2>&1 | tail -2 || true

# 5) DMG
DMG="$HERE/SEB Config Bypass Studio.dmg"
echo "==> membuat DMG..."
rm -f "$DMG"
hdiutil create -volname "SEB Config Bypass Studio" \
    -srcfolder "$APP" -ov -format UDZO "$DMG" >/dev/null
echo "==> OK: $DMG ($(du -h "$DMG" | cut -f1))"

echo
echo "=================================================="
echo " SELESAI"
echo "   .app : $APP"
echo "   .dmg : $DMG"
echo "=================================================="
echo
echo "Catatan: aplikasi ditandatangani ad-hoc (bukan Developer ID)."
echo "Saat pertama dibuka, macOS bisa menolak. Cara buka:"
echo "  - Klik kanan app -> Open -> Open"
echo "  - atau: xattr -dr com.apple.quarantine \"$APP\""
