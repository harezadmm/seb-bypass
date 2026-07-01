#!/bin/bash

# Tempat penyimpanan preferences SEB di macOS
DEST_DIR="$HOME/Library/Preferences"
FILE_NAME="SebClientSettings.seb"
URL="https://github.com/harezadmm/seb-bypass/raw/main/SebClientSettings.seb"

echo "============================================="
echo "   INSTALL SEB CONFIGURATION FOR macOS"
echo "============================================="
echo ""

# Pastikan direktori tujuan ada
if [ ! -d "$DEST_DIR" ]; then
    mkdir -p "$DEST_DIR"
fi

echo "[1/2] Downloading configuration from GitHub..."
curl -f -sL "$URL" -o "$DEST_DIR/$FILE_NAME"

if [ $? -eq 0 ]; then
    echo "[2/2] Applying configuration..."
    echo ""
    echo "============================================="
    echo " SUKSES! Konfigurasi SEB macOS berhasil terpasang!"
    echo " Lokasi: $DEST_DIR/$FILE_NAME"
    echo "============================================="
else
    echo ""
    echo "============================================="
    echo " GAGAL! File 'SebClientSettings.seb' tidak ditemukan"
    echo " di repositori GitHub Anda."
    echo "============================================="
    exit 1
fi
