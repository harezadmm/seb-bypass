#!/bin/bash
# ============================================================
#  SEB Bypass - macOS  (install_mac_one.sh)
#
#  SHIM. Sejak 2026-09-27 skrip ini hanya meneruskan ke
#  install_mac_one_v2.sh, installer resmi yang sekarang.
#
#  KENAPA DIUBAH
#  Versi lama file ini menyimpan salinan sendiri dari logika
#  instalasi, TERMASUK CONFIG_SHA256 yang di-hardcode. Setiap
#  kali payload SebClientSettings.seb diperbarui, hash di sini
#  harus ikut diubah - dan kalau terlupa, skrip ini akan
#  MENOLAK payload baru dan pengguna mendapat config bypass
#  lama tanpa sadar. Itu pernah terjadi.
#
#  Dengan meneruskan ke satu jalur saja, tidak ada lagi hash
#  ganda yang bisa basi: apa pun yang diperbaiki di v2 langsung
#  berlaku di sini.
#
#  Nama file ini dipertahankan supaya tautan dan dokumentasi
#  lama tetap hidup. Untuk pemakaian baru, langsung pakai:
#
#    curl -fsSL https://raw.githubusercontent.com/harezadmm/seb-bypass/main/install_mac_one_v2.sh | bash
# ============================================================
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/harezadmm/seb-bypass/main"
TARGET="${REPO_RAW}/install_mac_one_v2.sh"

echo "=================================================="
echo "  install_mac_one.sh sudah digantikan"
echo "  -> meneruskan ke install_mac_one_v2.sh (terbaru)"
echo "=================================================="
echo

TMP="$(mktemp "${TMPDIR:-/tmp}/seb_one_v2.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

if ! curl -fsSL --retry 3 --connect-timeout 20 "$TARGET" -o "$TMP"; then
    echo "" >&2
    echo "GAGAL mengunduh installer terbaru dari:" >&2
    echo "  $TARGET" >&2
    echo "" >&2
    echo "Kalau repo ini dijadikan privat, URL di atas akan" >&2
    echo "membalas HTTP 404. Pakai file install_mac_one_v2.sh" >&2
    echo "secara lokal, atau jalankan tanpa jaringan." >&2
    exit 1
fi

bash "$TMP" "$@"
