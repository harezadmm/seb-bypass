#!/bin/bash

# ============================================================
#  Safe Exam Browser 3.7.1 (macOS) - Config Bypass Setup
# ============================================================
#  Memasang konfigurasi bypass via preferensi SEB:
#    - allowVirtualMachine        = true
#    - allowSwitchToApplications  = true
#    - enableAppSwitcherCheck     = false
#    - enableAltTab               = true
#  Kompatibel SEB 3.7.1 (macOS).
#
#  Cara pakai:
#    bash install_seb.sh
#  Atau one-liner:
#    curl -fsSL https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_seb.sh | bash
# ============================================================

DEST_DIR="$HOME/Library/Preferences"
FILE_NAME="SebClientSettings.seb"
URL="https://github.com/harezadmm/seb-bypass/raw/main/SebClientSettings.seb"

echo "============================================="
echo "   INSTALL SEB 3.7.1 BYPASS CONFIG FOR macOS"
echo "============================================="
echo ""

# Pastikan direktori tujuan ada
if [ ! -d "$DEST_DIR" ]; then
    mkdir -p "$DEST_DIR"
fi

echo "[1/2] Downloading configuration from GitHub..."
curl -f -sL "$URL" -o "$DEST_DIR/$FILE_NAME"

if [ $? -eq 0 ]; then
    # Bunuh cache preferensi lama supaya SEB baca config baru
    defaults delete org_safeexambrowser_SEB 2>/dev/null
    killall cfprefsd 2>/dev/null

    echo "[2/2] Applying configuration..."
    echo ""
    echo "============================================="
    echo " SUKSES! Konfigurasi SEB 3.7.1 bypass terpasang!"
    echo " Lokasi: $DEST_DIR/$FILE_NAME"
    echo ""
    echo " Fitur bypass:"
    echo "   [+] Bypass deteksi Virtual Machine"
    echo "   [+] Alt+Tab / App Switcher UNLOCK"
    echo "   [+] Switch antar aplikasi diizinkan"
    echo "   [+] Exit keys tetap berfungsi (Esc/CtrlEsc/AltEsc)"
    echo "============================================="
else
    echo ""
    echo "============================================="
    echo " GAGAL! File 'SebClientSettings.seb' tidak ditemukan"
    echo " di repositori GitHub Anda."
    echo "============================================="
    exit 1
fi
