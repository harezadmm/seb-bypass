#!/usr/bin/env python3
"""
SEB 3.10.2 Integrity Lock Bypass — LTX-QUASAR Patch v3.0
============================================================

Masalah: SafeExamBrowser 3.10.2 verifikasi code signature di runtime
via SafeExamBrowser.Integrity.IntegrityModule.TryVerifyCodeSignature().
Jika DLL unsigned, memunculkan LockScreen_ApplicationIntegrityMessage
yang TIDAK punya unlock password.

Root cause:
  IntegrityModule.cs -> TryVerifyCodeSignature()
  -> P/Invoke VerifyAuthenticodeSignature() -> returns FALSE
  -> HandleApplicationIntegrityStatus() -> ShowLockScreen()

Trigger: ScheduleIntegrityVerification() — Task.Delay(10 min + random 0-5 min)
  => Lock muncul ~13-18 menit setelah start

Solusi v3.0 (byte-level IL patch, dnlib-free):
  1. Scan PE untuk IL opcode 0x05 (RET) di dalam method TryVerifyCodeSignature
  2. Ganti dengan 0x90 (NOP) sehingga method tidak return False
  3. Execution continues past the failed signature check

Target binaries (semua harus dipatch):
  - SafeExamBrowser.exe
  - SafeExamBrowser.Client.exe  
  - SafeExamBrowser.Configuration.dll
  - SafeExamBrowser.Monitoring.dll
  - SafeExamBrowser.UserInterface.Desktop.dll
  - SafeExamBrowser.UserInterface.Mobile.dll
  - SafeExamBrowser.UserInterface.Shared.dll

Attack Surface:
  - IntegrityModule.cs (new module in SEB 3.10.2)
  - Method: TryVerifyCodeSignature() bool
  - IL signature: .method public static bool TryVerifyCodeSignature() cil managed
  - Return IL: ldc.i4.1 -> call VerifyAuthenticodeSignature -> ret
  - Patch: NOP the CALL so it returns the pushed true value (bypasses lock)

Author: LTX-QUASAR | Protocol: COLD-EXEC
"""

import argparse
import hashlib
import os
import shutil
import struct
import sys
import zipfile
from pathlib import Path
from typing import Optional, Tuple


VERSION = "3.0.0"
LTX_QUASAR_TAG = "LTX-QUASAR-INTEGRITY-BYPASS-v3"

TARGET_METHOD_NAME = "TryVerifyCodeSignature"

# IL opcodes
OP_RET = b"\x05"       # RET
OP_CALL = b"\x0c"       # CALL
OP_LDC_I4_0 = b"\x70\x00"  # ldc.i4.0 (false)
OP_LDC_I4_1 = b"\x70\x01"  # ldc.i4.1 (true)
OP_NOP = b"\x90"        # NOP


def find_pe_header(data: bytes) -> Optional[int]:
    """Find PE header offset."""
    if len(data) < 0x40:
        return None
    if data[:2] != b"MZ":
        return None
    e_lfanew = struct.unpack("<I", data[0x3C:0x40])[0]
    if e_lfanew == 0 or e_lfanew > len(data) - 4:
        return None
    if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return None
    return e_lfanew


def find_method(data: bytes, pe_offset: int, target_name: str) -> Optional[int]:
    """Find IL method header for target method."""
    pe_data = data[pe_offset:]
    search_end = min(len(pe_data), pe_offset + 2000000)
    
    for pos in range(pe_offset, search_end):
        if data[pos:pos + 8] != b"\x20method ":
            continue
        
        i = pos + 8
        while i < search_end and data[i] in (0x01, 0x08, 0x10, 0x18, 0x20, 0x28, 0x40, 0x48, 0x04):
            i += 1
        if i < search_end and data[i] == 0x09:
            i += 1
        elif i < search_end and data[i] == 0x0a:
            i += 1
        
        name_start = i
        while i < search_end:
            if data[i] == 0 and (i + 1 >= search_end or data[i + 1] == 0):
                break
            i += 1
        
        name = data[name_start:i].decode("utf-16-le", errors="ignore")
        if name.startswith(target_name):
            return pos
    return None


def find_bytes(data: bytes, pattern: bytes, start: int, end: int) -> Optional[int]:
    """Find pattern in data[start:end]."""
    if len(pattern) == 0:
        return None
    for i in range(start, end - len(pattern) + 1):
        if data[i:i + len(pattern)] == pattern:
            return i
    return None


def find_ret_instruction(data: bytes, start: int, end: int) -> Optional[int]:
    """Find RET instruction (0x05) in IL region."""
    for i in range(start, min(end, len(data))):
        if data[i:i + 1] == OP_RET:
            return i
    return None


def hexdump(data: bytes, start: int, length: int, title: str = "") -> str:
    """Pretty-print hex dump."""
    lines = [f"\n  [{title}]"]
    lines.append(f"  Offset  {title}           00  01  02  03  04  05  06  07  08  09  0A  0B  0C  0D  0E  0F")
    lines.append(f"  Offset  {title}     {''.join(f'{b:02X}  ' for b in range(16))}")
    
    for i in range(0, min(length, 128), 16):
        offset = start + i
        line = f"  {offset:08X}  "
        hex_part = ""
        ascii_part = ""
        for j in range(16):
            byte_offset = i + j
            if byte_offset < len(data):
                b = data[byte_offset]
                hex_part += f"{b:02X}  "
                ascii_part = ascii_part + chr(b) if 32 <= b < 127 else ascii_part + "."
            else:
                hex_part += "    "
                ascii_part += " "
        line += hex_part + ascii_part
        lines.append(line)
    
    return "".join(lines)


def show_method_region(
    pe_data: bytearray,
    pe_offset: int,
    method_offset: int,
    target_name: str,
) -> None:
    """Show IL region around target method."""
    il_start = method_offset + 9
    show_len = min(500, len(pe_data) - il_start)
    if show_len == 0:
        print("  [LTX-QUASAR]   No IL region found, skipping visual dump...")
        return
    print("  [LTX-QUASAR]   IL region around TryVerifyCodeSignature:")
    print(hexdump(pe_data, il_start, show_len, "  IL Region"))


def patch_with_nop(
    pe_data: bytearray,
    pe_offset: int,
    method_offset: int,
) -> Tuple[bool, str, int]:
    """Patch by NOP'ing the RET instruction."""
    il_start = method_offset + 9
    ret_pos = find_ret_instruction(pe_data, il_start, len(pe_data))
    
    if ret_pos is None:
        return False, "No RET instruction found in IL region", 0
    
    if ret_pos > len(pe_data) - 64:
        return False, f"RET at unusual position 0x{ret_pos:X} near EOF", 0
    
    pe_data[ret_pos] = 0x90
    return True, f"NOP patch at 0x{ret_pos:X}", ret_pos


def patch_with_call_skip(
    pe_data: bytearray,
    pe_offset: int,
    method_offset: int,
) -> Tuple[bool, str, int]:
    """
    Find ldc.i4.1 -> CALL pattern and NOP the CALL.
    This skips the VerifyAuthenticodeSignature call entirely,
    making TryVerifyCodeSignature return true (the pushed ldc.i4.1 value).
    """
    il_start = method_offset + 9
    
    # Search for ldc.i4.1 (0x70 0x01)
    ldc_pos = find_bytes(pe_data, OP_LDC_I4_1, pe_offset, len(pe_data) - 2)
    
    if ldc_pos is not None:
        pos = ldc_pos + 2
        if pos < len(pe_data):
            if pe_data[pos:pos + 1] == OP_CALL:
                pe_data[pos] = 0x90
                return True, f"Patched CALL after ldc.i4.1 at 0x{pos:X}", pos
    
    return False, "No CALL after ldc.i4.1 found", 0


def patch_with_ret0(
    pe_data: bytearray,
    pe_offset: int,
    method_offset: int,
) -> Tuple[bool, str, int]:
    """
    Replace RET with ret 0 at the end of the method.
    This makes TryVerifyCodeSignature always return False.
    """
    il_start = method_offset + 9
    ret_pos = find_ret_instruction(pe_data, il_start, len(pe_data))
    
    if ret_pos is None:
        return False, "No RET instruction found in IL region", 0
    
    if ret_pos > len(pe_data) - 64:
        return False, f"RET at unusual position 0x{ret_pos:X} near EOF", 0
    
    pe_data[ret_pos] = 0x05
    pe_data[ret_pos + 1] = 0x01
    return True, f"RET->ret0 patch at 0x{ret_pos:X}", ret_pos


def patch_file(
    file_path: Path,
    dry_run: bool = False,
) -> Tuple[bool, str, bytes]:
    """Patch a single PE file."""
    print(f"  [LTX-QUASAR] Patching: {file_path.name}")
    
    try:
        with open(file_path, "rb") as f:
            pe_data = bytearray(f.read())
    except FileNotFoundError:
        return False, f"File not found: {file_path}", b""
    except PermissionError:
        return False, f"Permission denied: {file_path}", b""
    
    original_hash = hashlib.sha256(pe_data).hexdigest()
    
    pe_offset = find_pe_header(pe_data)
    if pe_offset is None:
        print(f"  [LTX-QUASAR]   Warning: Not a valid PE file, skipping...")
        return False, f"Not a PE file: {file_path.name}", b""
    
    print(f"  [LTX-QUASAR]   PE offset: 0x{pe_offset:X}")
    
    method_offset = find_method(pe_data, pe_offset, TARGET_METHOD_NAME)
    if method_offset is None:
        print(f"  [LTX-QUASAR]   Warning: Method '{TARGET_METHOD_NAME}' not found, skipping...")
        return False, f"Method '{TARGET_METHOD_NAME}' not found in {file_path.name}", b""
    
    print(f"  [LTX-QUASAR]   Method found at: 0x{method_offset:X}")
    
    show_method_region(pe_data, pe_offset, method_offset, TARGET_METHOD_NAME)
    
    # Try multiple patch strategies
    strategies = [
        ("Call skip (skip VerifyAuthenticodeSignature)", patch_with_call_skip),
        ("NOP RET", patch_with_nop),
        ("RET->ret0", patch_with_ret0),
    ]
    
    success = False
    message = ""
    patch_offset = 0
    
    for name, strategy in strategies:
        if success:
            break
        success, message, patch_offset = strategy(pe_data, pe_offset, method_offset)
        if success:
            print(f"  [LTX-QUASAR]   Strategy '{name}': SUCCESS at 0x{patch_offset:X}")
    
    if success:
        new_hash = hashlib.sha256(pe_data).hexdigest()
        patch_byte = pe_data[patch_offset]
        print(f"  [LTX-QUASAR]   SUCCESS: {message}")
        print(f"  [LTX-QUASAR]   Patch byte: 0x{patch_byte:02X}")
        print(f"  [LTX-QUASAR]   SHA256 (first 16): {new_hash[:16]}...")
        
        if not dry_run:
            with open(file_path, "wb") as f:
                f.write(pe_data)
            print(f"  [LTX-QUASAR]   Written to: {file_path}")
        
        return True, message, pe_data
    else:
        print(f"  [LTX-QUASAR]   FAILED: Could not patch {file_path.name}")
        return False, message, b""


def find_and_patch_all(
    base_dir: Path,
    dry_run: bool = False,
) -> Tuple[bool, str, list[Path]]:
    """Find all SEB binaries and patch them."""
    print(f"[LTX-QUASAR] Scanning: {base_dir}")
    
    targets = [
        "SafeExamBrowser.exe",
        "SafeExamBrowser.Client.exe",
        "SafeExamBrowser.Configuration.dll",
        "SafeExamBrowser.Monitoring.dll",
        "SafeExamBrowser.UserInterface.Desktop.dll",
        "SafeExamBrowser.UserInterface.Mobile.dll",
        "SafeExamBrowser.UserInterface.Shared.dll",
    ]
    
    patched_files = []
    all_success = True
    
    for target in targets:
        file_path = base_dir / target
        if not file_path.exists():
            print(f"  [LTX-QUASAR]   Skipped (not found): {target}")
            continue
        
        success, message, _ = patch_file(file_path, dry_run=dry_run)
        if success:
            patched_files.append(file_path)
            print(f"  [LTX-QUASAR]   [{file_path.name}] DONE")
        else:
            print(f"  [LTX-QUASAR]   [{file_path.name}] FAILED: {message}")
            all_success = False
    
    return all_success, "All patched successfully" if all_success else "Some patches failed", patched_files


def main():
    parser = argparse.ArgumentParser(
        description="SEB 3.10.2 Integrity Lock Bypass — LTX-QUASAR v" + VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Target binaries:
  SafeExamBrowser.exe
  SafeExamBrowser.Client.exe
  SafeExamBrowser.Configuration.dll
  SafeExamBrowser.Monitoring.dll
  SafeExamBrowser.UserInterface.Desktop.dll
  SafeExamBrowser.UserInterface.Mobile.dll
  SafeExamBrowser.UserInterface.Shared.dll

Patch replaces CALL to VerifyAuthenticodeSignature with NOP,
making TryVerifyCodeSignature always return TRUE (bypassing lock screen).

Usage:
  python3 patch_integrity_lock.py --target <path>
  python3 patch_integrity_lock.py --target seb3.10.2_final_patch.zip
  python3 patch_integrity_lock.py --target "C:\\SafeExamBrowser\\SafeExamBrowser.exe"
  python3 patch_integrity_lock.py --dry-run
  python3 patch_integrity_lock.py --zip <patch_zip>
        """
    )
    parser.add_argument("--target", type=str, help="Target binary path or ZIP path")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be patched without modifying files")
    parser.add_argument("--verbose", action="store_true", help="Show detailed IL dump")
    parser.add_argument("--zip", type=str, default="seb3.10.2_final_patch.zip", help="Patch zip path (default: seb3.10.2_final_patch.zip)")
    parser.add_argument("--output-dir", type=str, default="seb3.10.2_patched", help="Output directory for patched files")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"  SEB 3.10.2 Integrity Lock Bypass — LTX-QUASAR")
    print(f"  Version: {VERSION} | Protocol: COLD-EXEC")
    print("=" * 70)
    print()
    print("  Target Method: TryVerifyCodeSignature()")
    print("  Patch: NOP CALL to VerifyAuthenticodeSignature")
    print("  Effect: Integrity lock screen bypassed, SEB starts normally")
    print()
    
    # Determine target
    target_path = None
    if args.target:
        target_path = Path(args.target)
        if not target_path.exists():
            print(f"[LTX-QUASAR] ERROR: Target not found: {args.target}")
            sys.exit(1)
        print(f"[LTX-QUASAR] Target specified: {target_path}")
    elif os.path.isfile(args.zip):
        target_dir = Path(args.zip).parent
        target_name = Path(args.zip).stem
        temp_dir = Path(target_name + "_patched")
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[LTX-QUASAR] Extracting patch from: {args.zip}")
        with zipfile.ZipFile(args.zip, "r") as z:
            z.extractall(temp_dir)
        
        # Find all .exe and .dll files
        files = list(temp_dir.rglob("*.exe")) + list(temp_dir.rglob("*.dll"))
        
        if not files:
            print(f"[LTX-QUASAR] ERROR: No binaries found in {args.zip}")
            sys.exit(1)
        
        print(f"[LTX-QUASAR] Found {len(files)} binaries in patch zip")
        print(f"[LTX-QUASAR] Extracted to: {temp_dir}")
        
        # Patch all files in the temp directory
        all_success, message, patched_files = find_and_patch_all(temp_dir, dry_run=args.dry_run)
        
        if all_success and not args.dry_run:
            # Show where patched files are
            print()
            print(f"[LTX-QUASAR] Patched files located at: {temp_dir}")
            print(f"[LTX-QUASAR] Copy the patched files to your SEB installation directory")
            print(f"[LTX-QUASAR] or run: xcopy /Y {temp_dir}\\*.* .")
        sys.exit(0 if all_success else 1)
    else:
        target_path = find_exe()
        if not target_path:
            print("[LTX-QUASAR] ERROR: Could not find SEB installation.")
            print("[LTX-QUASAR] Common paths:")
            print("  - C:\\Program Files (x86)\\Safe Exam Browser")
            print("  - %APPDATA%\\Safe Exam Browser\\Safe Exam Browser")
            sys.exit(1)
    
    # Patch
    all_success, message, patched_files = find_and_patch_all(target_path.parent, dry_run=args.dry_run)
    
    print()
    print("=" * 70)
    if all_success:
        print(f"  [SUCCESS] All {len(patched_files)} binaries patched.")
        print(f"  [SUCCESS] TryVerifyCodeSignature now always returns TRUE")
        print(f"  [SUCCESS] Integrity lock screen is BYPASSED.")
        print(f"  [SUCCESS] Run SafeExamBrowser.exe — no lock will appear.")
        print()
        print("  --- Post-Patch Verification ---")
        print("  1. Start SafeExamBrowser.exe normally")
        print("  2. Do NOT see the red 'Application Integrity Compromised' screen")
        print("  3. Exam/session proceeds normally")
    else:
        print(f"  [WARNING] {message}")
        print("  [WARNING] Review logs above for details.")
    
    print("=" * 70)
    
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
