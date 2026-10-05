#!/usr/bin/env python3
"""Inspect .seb files on a machine: format, key count, and the keys that matter."""
import glob
import os
import plistlib

MAGIC = {b"plnd": "plain container", b"pswd": "password", b"pwcc": "password(cc)",
         b"pkhs": "public-key", b"phsk": "public-key+sym"}
WATCH = ["originatorVersion", "clipboardPolicy", "enablePrivateClipboard",
         "enablePrivateClipboardMacEnforce", "allowSwitchToApplications",
         "allowOpenAndSavePanel", "allowShareSheet", "enableMacOSAAC",
         "lockdownModePolicy", "sebConfigPurpose", "sebMode", "browserViewMode",
         "createNewDesktop", "allowVirtualMachine", "allowScreenSharing",
         "enablePrintScreen", "enableAltTab", "useAsymmetricOnlyEncryption"]

roots = [os.path.expanduser(p) for p in os.sys.argv[1:]] or [os.path.expanduser("~")]
seen = []
for root in roots:
    for p in glob.glob(os.path.join(root, "**", "*.seb"), recursive=True):
        seen.append(p)

for p in sorted(set(seen)):
    try:
        with open(p, "rb") as fh:
            head = fh.read(4)
            fh.seek(0)
            if head in MAGIC:
                print("\n%s\n   FORMAT: %s (not a plist)" % (p, MAGIC[head]))
                continue
            d = plistlib.load(fh)
        print("\n%s\n   plist, %d keys, %d bytes" % (p, len(d), os.path.getsize(p)))
        for k in WATCH:
            if k in d:
                print("      %-32s %r" % (k, d[k]))
    except Exception as exc:
        print("\n%s\n   UNREADABLE: %s: %s" % (p, type(exc).__name__, exc))
