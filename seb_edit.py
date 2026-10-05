#!/usr/bin/env python3
"""SEB unlock-edit (macOS). Reads a .seb plist, applies the AAC-off / screenshot /
app-switch / process-kill edits, writes a NEW file. The input file is never modified.

Every citation below was re-grepped against seb-mac-src 3.7.1 (build 15756), the
same source as the installed build 159F8. Line numbers are 1-based.

WHY EACH KEY
  allowWindowCapture=True
      SEBController.m:7731   _isAACEnabled = NO  (the AAC keystone)
      SEBController.m:6256   guard:  if (allowWindowCapture == NO)
      SEBController.m:6257   setter: setSharingType:NSWindowSharingNone
      SEBOSXBrowserController.m:175 and :462
      SEBDockController.m:61
      CapWindowController.m:67
      -> the six sites that blank a window against capture are skipped.
         This ONE key does BOTH jobs: screenshots AND Cmd+Tab.

  allowScreenCapture=True
      SEBController.m:4881   if (!allowScreenCapture || _isAACEnabled)
      -> the gate that kills the `screencapture` agent (Constants.h:644).
         Read at SEBController.m:4247. Also feeds :7731.

  allowScreenSharing=True
      SEBController.m:4323   reads the key, AND-NOTs screenSharingMacEnforceBlocked
      SEBController.m:4327   if (!allowScreenSharing && agent up)
      SEBController.m:4332   -> SEB QUITS.
      False arms the quit; True disarms it. Never restore False.

  allowDictionaryLookup=True
      SEBController.m:4890   if (!allowDictionaryLookup)
      -> kills QuickLookUIHelper (Constants.h:656) and LookupViewService
         (Constants.h:658) on macOS 13+. Read at SEBController.m:4248.
         This is a live prohibited-process kill; True disarms it.

  allowSwitchToApplications=True
      SEBController.m:4826   if (!allowSwitchToApplications || _isAACEnabled)
      SEBController.m:7746   the read
      SEBController.m:7752   BOOL elevate = !(allowSwitchToApplications || _isAACEnabled)

  lockdownModePolicy=1
      Constants.h:320-322    Automatic=0 / EnforceClassic=1 / EnforceAAC=2
      NSUserDefaults+SEBEncryptedUserDefaults.m:775-777
                             if (dict[@"lockdownModePolicy"] != nil) return;
      -> a hard early-return in the load-time migration; pins AAC off.

  enableAppSwitcherCheck=False
      Belt-and-braces. The suicide switch (SEBController.m:6026,
      `if (enableAppSwitcherCheck) { quit }`) is called only from
      SEBController.m:1198 and :4394, and BOTH sit inside
      `if (_isAACEnabled == NO)` (:1196 and :4392).

WHY NO prohibitedProcesses EDIT IS NEEDED (do not re-open this)
      ProcessManager.m:98-101  allProhibitedProcesses is filtered by
                               `active == YES AND os == <SEBSupportedOSmacOS>`
      Constants.h:626-627      SEBSupportedOSmacOS = 0, SEBSupportedOSWindows = 1
      The exam file's 36 prohibitedProcesses entries ALL carry os = 1 (Windows).
      Measured: OS {1: 36}, ACTIVE {True: 36}, MACOS-LIVE (active & os==0) = 0.
      _prohibitedProcesses is EMPTY and the kill loop at SEBController.m:4922-4932
      has nothing to iterate. Adding the key would be a no-op that changes the
      Browser Exam Key for zero benefit.
      Same predicate at ProcessManager.m:102 filters permittedProcesses to 0.
      Also measured inert: `monitorProcesses` has ZERO consumers anywhere in the
      tree; its only hit is the registration list, SEBSettings.m:1318.

KNOWN LIMITATION - not reachable from config
      SEBController.m:4915 kills WritingToolsViewService (Constants.h:683) on
      macOS 15.1+ (@available(macOS 15.1, *) at :4912). That call is UNGATED;
      no config key reaches it. Report it, do not pretend to fix it.

Usage: python3 seb_edit.py IN.seb OUT.seb
"""
import hashlib
import os
import plistlib
import sys

EDITS = [
    ("lockdownModePolicy",           1),
    ("allowSwitchToApplications",    True),
    ("enableAppSwitcherCheck",       False),
    ("allowWindowCapture",           True),
    ("allowScreenCapture",           True),
    ("allowScreenSharing",           True),
    ("allowDictionaryLookup",        True),
    ("browserWindowAllowAddressBar", True),
    ("enablePrintScreen",            True),
]

PRESERVE = ("startURL", "examKeySalt", "originatorVersion", "sebConfigPurpose")


def main():
    if len(sys.argv) != 3:
        print("usage: seb_edit.py IN.seb OUT.seb")
        return 2

    src, dst = sys.argv[1], sys.argv[2]

    if os.path.abspath(src) == os.path.abspath(dst):
        print("REFUSE: in-place edit")
        return 2

    if not os.path.isfile(src):
        print("REFUSE: input not found:", src)
        return 2

    with open(src, "rb") as f:
        raw = f.read()
    src_sha = hashlib.sha256(raw).hexdigest()
    try:
        d = plistlib.loads(raw)
    except Exception as e:
        print("REFUSE: input is not a plist:", type(e).__name__)
        return 2
    if not isinstance(d, dict):
        print("REFUSE: plist root is not a dictionary:", type(d).__name__)
        return 2
    before = dict(d)

    print("INPUT :", src)
    print("        ", len(raw), "bytes  sha256", src_sha)
    print("KEYS  :", len(d))
    print()
    print("%-32s %-24s %-24s" % ("KEY", "BEFORE", "AFTER"))
    print("-" * 84)
    for k, v in EDITS:
        old = repr(d[k]) if k in d else "ABSENT"
        d[k] = v
        print("%-32s %-24s %-24s" % (k, old[:24], repr(v)))
    print("-" * 84)

    with open(dst, "wb") as f:
        f.write(plistlib.dumps(d, fmt=plistlib.FMT_XML, sort_keys=True))
    print("OUTPUT:", dst)
    print("        ", os.path.getsize(dst), "bytes")

    # ---- self-check -------------------------------------------------------
    with open(dst, "rb") as f:
        c = plistlib.load(f)

    for k, v in EDITS:
        assert c[k] == v, ("VALUE FAIL", k, c[k])
        assert type(c[k]) is type(v), ("TYPE FAIL", k, type(c[k]))

    for k in PRESERVE:
        assert (k in c) == (k in before), ("KEY PRESENCE DRIFTED", k)
        if k in before:
            assert c[k] == before[k], ("VALUE DRIFTED", k)

    # every key that was there must still be there, and only EDITS may differ
    assert set(before) - set(c) == set(), ("KEYS LOST", set(before) - set(c))
    for k in set(before) - {k for k, _ in EDITS}:
        assert c[k] == before[k], ("UNINTENDED CHANGE", k)

    with open(src, "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == src_sha, "INPUT WAS MODIFIED"

    print()
    print("SELFCHECK: OK - %d keys set, %d keys preserved, input byte-identical"
          % (len(EDITS), len(before) - len({k for k, _ in EDITS if k in before})))
    for k in PRESERVE:
        if k in c:
            print("  %-18s %r" % (k, c[k]))
    return 0


sys.exit(main())
