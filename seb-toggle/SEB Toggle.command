#!/usr/bin/env bash
# Double-click this in Finder to open the GUI. Works without any build step,
# as long as Python 3 with tkinter is installed (python.org builds include it).
#
# If macOS refuses to open it: right-click > Open, then Open again.
# Or run once:  chmod +x "SEB Toggle.command"
cd "$(dirname "$0")" || exit 1

PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import tkinter" >/dev/null 2>&1; then
        PY="$c"; break
    fi
done

if [ -z "$PY" ]; then
    osascript -e 'display dialog "Python 3 with tkinter tidak ditemukan.\n\nPasang dari python.org (tkinter sudah termasuk), lalu coba lagi.\n\nSementara itu CLI tetap bisa dipakai lewat Terminal: python3 seb_toggle.py --help" with title "SEB Toggle" buttons {"OK"} default button 1 with icon caution' >/dev/null 2>&1
    echo "Python 3 + tkinter not found."
    echo "Install from https://www.python.org/downloads/ (tkinter is bundled)."
    read -r -p "Press Return to close." _
    exit 1
fi

exec "$PY" seb_gui.py "$@"
