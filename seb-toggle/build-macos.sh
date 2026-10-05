#!/usr/bin/env bash
# Build a double-clickable "SEB Toggle.app" for macOS.
#
# MUST run on macOS. PyInstaller cannot cross-compile a .app from Windows or Linux.
#
#   chmod +x build-macos.sh
#   ./build-macos.sh
#
# Result: dist/SEB Toggle.app   and   dist/seb-toggle-cli
#
# The script picks its own interpreter on purpose. Apple's /usr/bin/python3 ships
# Tk 8.5, which is deprecated and produces a broken bundle on current macOS. Only a
# Python whose Tk is 8.6 or newer is accepted.
set -euo pipefail
cd "$(dirname "$0")"

need() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- interpreter
probe() {
    # echoes "<path> <version> <tk>" when the interpreter is usable, else nothing
    "$1" - <<'PY' 2>/dev/null || return 1
import sys, tkinter
if sys.version_info < (3, 9):
    raise SystemExit(1)
if tkinter.TkVersion < 8.6:
    raise SystemExit(1)
print("%d.%d %s" % (sys.version_info[0], sys.version_info[1], tkinter.TkVersion))
PY
}

CANDIDATES=()
[ -n "${PYTHON:-}" ] && CANDIDATES+=("$PYTHON")
for v in 3.14 3.13 3.12 3.11 3.10; do
    [ -x "/opt/homebrew/bin/python$v" ] && CANDIDATES+=("/opt/homebrew/bin/python$v")
done
for d in /Library/Frameworks/Python.framework/Versions/*/bin/python3; do
    [ -x "$d" ] && CANDIDATES+=("$d")
done
[ -x /opt/homebrew/bin/python3 ] && CANDIDATES+=("/opt/homebrew/bin/python3")
[ -x /usr/local/bin/python3 ] && CANDIDATES+=("/usr/local/bin/python3")
if need python3; then CANDIDATES+=("$(command -v python3)"); fi

PICKED=""
REJECTED=""
for c in "${CANDIDATES[@]}"; do
    if info=$(probe "$c"); then
        PICKED="$c"
        echo "== interpreter =="
        echo "   $c   (python $info)   - Tk 8.6+ confirmed"
        break
    else
        ver=$("$c" --version 2>&1 | tr -d '\n' || echo "?")
        tk=$("$c" -c "import tkinter;print(tkinter.TkVersion)" 2>/dev/null | tail -1 || echo "no tkinter")
        REJECTED="$REJECTED
   $c  ($ver, Tk $tk)"
    fi
done

if [ -z "$PICKED" ]; then
    cat <<EOF
No usable Python found. Checked:${REJECTED}

Needs Python >= 3.9 with Tk >= 8.6. Fix with either:

  brew install python@3.13 python-tk@3.13
  # or install from https://www.python.org/downloads/ (tkinter bundled)

Then re-run this script. Override manually with:
  PYTHON=/path/to/python3 ./build-macos.sh
EOF
    exit 1
fi

# ---------------------------------------------------------------- venv
VENV=".venv-build"
if [ ! -x "$VENV/bin/python" ]; then
    echo "== venv =="
    "$PICKED" -m venv "$VENV"
fi
VENV_PY="$PWD/$VENV/bin/python"
"$VENV_PY" -m pip install --quiet --upgrade pip
if ! "$VENV_PY" -m PyInstaller --version >/dev/null 2>&1; then
    echo "   installing pyinstaller"
    "$VENV_PY" -m pip install --quiet pyinstaller
fi
if ! "$VENV_PY" -c "import PIL" >/dev/null 2>&1; then
    echo "   installing pillow"
    "$VENV_PY" -m pip install --quiet pillow
fi
echo "   python $("$VENV_PY" --version | awk '{print $2}')  |  pyinstaller $("$VENV_PY" -m PyInstaller --version)"

# ---------------------------------------------------------------- icon
echo "== icon =="
if [ ! -f seb.ico ] || [ ! -d icons ]; then
    "$VENV_PY" make_icon.py
fi
if [ ! -f seb.icns ]; then
    if need iconutil; then
        rm -rf seb.iconset && mkdir seb.iconset
        cp icons/icon_16x16.png      seb.iconset/icon_16x16.png
        cp icons/icon_32x32.png      seb.iconset/icon_16x16@2x.png
        cp icons/icon_32x32.png      seb.iconset/icon_32x32.png
        cp icons/icon_64x64.png      seb.iconset/icon_32x32@2x.png
        cp icons/icon_128x128.png    seb.iconset/icon_128x128.png
        cp icons/icon_256x256.png    seb.iconset/icon_128x128@2x.png
        cp icons/icon_256x256.png    seb.iconset/icon_256x256.png
        cp icons/icon_512x512.png    seb.iconset/icon_256x256@2x.png
        cp icons/icon_512x512.png    seb.iconset/icon_512x512.png
        cp icons/icon_1024x1024.png  seb.iconset/icon_512x512@2x.png
        iconutil -c icns seb.iconset -o seb.icns
        rm -rf seb.iconset
        echo "   seb.icns written"
    else
        echo "   iconutil not found - building without an icon"
    fi
fi

# ---------------------------------------------------------------- build
echo "== build =="
ICON_ARG=()
[ -f seb.icns ] && ICON_ARG=(--icon seb.icns)

# Output lands in dist/macos/, beside the shipped artifacts. Only that folder is
# cleared - dist/windows/ must survive a macOS rebuild.
rm -rf build dist/macos
mkdir -p dist/macos
"$VENV_PY" -m PyInstaller --windowed --noconfirm --distpath dist/macos --workpath build \
    ${ICON_ARG[@]+"${ICON_ARG[@]}"} \
    --name "SEB Toggle" --osx-bundle-identifier com.hariz.sebtoggle \
    --add-data "seb_registry.json:." seb_gui.py
"$VENV_PY" -m PyInstaller --onefile --noconfirm --distpath dist/macos --workpath build \
    --name "seb-toggle-cli" --add-data "seb_registry.json:." seb_toggle.py

# ---------------------------------------------------------------- verify
echo "== verify =="
APP="dist/macos/SEB Toggle.app"
[ -d "$APP" ] || { echo "   FAIL: $APP not produced"; exit 1; }
info() { /usr/libexec/PlistBuddy -c "Print :$1" "$APP/Contents/Info.plist" 2>/dev/null || echo "?"; }
echo "   bundle id : $(info CFBundleIdentifier)"
echo "   name      : $(info CFBundleName)"
echo "   icon      : $(info CFBundleIconFile)"
echo "   arch      : $(file -b "$APP/Contents/MacOS/SEB Toggle" | cut -d, -f1)"
echo "   size      : $(du -sh "$APP" | cut -f1)"

read -r -d '' HINT <<'EOF' || true
First launch of an unsigned .app: right-click > Open, then Open again.
Or: xattr -dr com.apple.quarantine "dist/macos/SEB Toggle.app"
EOF
echo
echo "done:"
echo "   $APP        drag to /Applications, double-click to open"
echo "   dist/macos/seb-toggle-cli        terminal CLI"
echo
echo "$HINT"
