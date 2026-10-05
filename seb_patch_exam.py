#!/usr/bin/env python3
"""SEB unlock-edit v3 (macOS). Reads a .seb plist, applies the strict-kiosk /
clipboard / capture / process-kill edits, writes a NEW file. Input is never modified.

v4 CHANGES vs v3 -- ONE key reverted. Everything else identical.

  1. allowSwitchToApplications: False -> True    (Jack got locked out --- Branch A restored)
  2. THREE clipboard keys added so Cmd+C/Cmd+X/Cmd+V from outside SEB survive.
  3. TARGET FILE CHANGED.  v2 was aimed at the exam config (config (1).seb).
     MEASURED TRUTH: the value in effect at runtime comes from
     ~/Library/Preferences/SebClientSettings.seb -- byte-identical to
     setups/SebClientSettings.seb (a4644dcd...). Precedence, four live data points:

       key                        client-settings   exam-config   runtime   winner
       allowSwitchToApplications  True              False         1         CLIENT
       allowWindowCapture         ABSENT            True          (AAC=0)   exam
       detectAccessibilityApps    ABSENT            False         (freed)   exam
       enablePrivateClipboard     True              True          broken    both

     -> a key present in BOTH files is decided by the CLIENT SETTINGS.
     -> the exam config already says allowSwitchToApplications=False and the
        runtime says 1, so the exam config cannot be the source of the 1.
     This script must therefore be run against BOTH files, so that whichever
     array wins the prohibitedProcesses join carries the fix.

WHY allowSwitchToApplications=False  (SYMPTOM 1 + 3 -- Chrome overlapping SEB)
      SEBController.m:7746   _sessionState.allowSwitchToApplications = [prefs secureBoolForKey:...]
      SEBController.m:7752   BOOL elevate = !(allowSwitchToApplications || _isAACEnabled);   <- THE FORMULA
      SEBController.m:7760   setSecureBool:elevate forKey:@"org_safeexambrowser_elevateWindowLevels"
      SEBController.m:7741-2 the authors' own comment naming this exact link.

      Live log, 12 readouts, every one identical (11:49:36:028 is the last):
        -[SEBController setElevateWindowLevels]: allowSwitchToApplications=1,
          _isAACEnabled=0, _wasAACEnabled=0 -> elevateWindowLevels=0, privateUserDefaults=1
      elevateWindowLevels=1 has NEVER been logged in any session on this machine.

      With elevate=NO the swizzle at NSWindow+SEBWindow.m:44 (if (elevate)) is skipped,
      so SEB never raises its own windows: :45 would give NSNormalWindowLevel -> 29.

      Four independent effects follow from the one flag:
        1. swizzle inert            NSWindow+SEBWindow.m:44 skipped
        2. cap window drops to 0    SEBController.m:7798 [capWindow newSetLevel:NSNormalWindowLevel]
                                    (the else-branch raiser is :7803 -> 26, unreached)
        3. kiosk is the relaxed one SEBController.m:7851-7857 -- NO
                                    NSApplicationPresentationDisableProcessSwitching
        4. panel killer disarmed    SEBController.m:5030 -> else -> :5076
                                    LIVE PROOF: the log is spammed with
                                    "Switching to applications is allowed, don't terminate
                                     application Window Server ((null))"  (3240x per file)
                                    and the same for Cloudflare WARP at level 101.
      Chrome at level 0, or fullscreen, or its helper panels, is then free to order above
      SEB. This is the overlap. It was NEVER a regression: elevate=0 is logged at 08:01:10,
      before any unlocked copy existed (08:52).

      THE TRADE, STATED PLAINLY: with allowSwitchToApplications=False the strict branch
      SEBController.m:7842-7850 adds NSApplicationPresentationDisableProcessSwitching at
      :7848, so Cmd+Tab is blocked by macOS. Cmd+Tab and "SEB stays on top" are mutually
      exclusive in this codebase -- one flag, four effects, one function. There is no
      config-only middle path:
        * SEBController.m:7836-7840 merely round-trips the same flag.
        * forcing elevateWindowLevels=YES separately is impossible: :7760 overwrites it
          every session, and :7839 (set YES) always sits beside :7848 (DisableProcessSwitching).

WHY THE THREE CLIPBOARD KEYS  (SYMPTOM 2 -- CleanShot X screenshot won't paste)
      SEBAbstractWebView.m:97-98   setPrivateClipboardEnabled:(MacEnforce || Clipboard)   <- OR
      SEBSettings.m:491-492        enablePrivateClipboard            default @YES
      SEBSettings.m:494-495        enablePrivateClipboardMacEnforce  default @YES
      SEBSettings.m:413-414        clipboardPolicy                   default SEBOnly (2)
      Constants.h:634-638          Allow=0 / Block=1 / SEBOnly=2

      With private clipboard on, every copy/cut/paste INSIDE the page wipes the system
      pasteboard and writes back SEB's own archive, which never held the screenshot:
      SEBAbstractWebView.m:564  [generalPasteboard clearContents]   (on copy/cut)
      SEBAbstractWebView.m:571  [generalPasteboard clearContents]   (on paste)
      SEBWebView.m:160 / SEBOSXWKWebViewController.swift:406        (after paste)
      SEBController.m:4276      clearPasteboardSavingCurrentString  (session start)
      plus the concealed/transient markers at :576-577 / :586-587 and Spotlight history
      already OFF on this machine (`defaults read com.apple.Spotlight PasteboardHistoryEnabled`
      -> 0).

      BOTH clipboard keys must be False -- :97-98 is an OR, so leaving MacEnforce at its
      @YES default would re-enable it. clipboardPolicy=0 overrides the SEBOnly default.

WHY THE OTHER KEYS -- unchanged from v2

  allowWindowCapture=True
      SEBController.m:7731   _isAACEnabled = NO  (the AAC keystone)
      SEBController.m:6256/:6257  guard + setSharingType:NSWindowSharingNone
      SEBOSXBrowserController.m:175,:462  SEBDockController.m:61  CapWindowController.m:67
      -> six capture-blanking sites skipped. Live-proven: isAACEnabled flipped 1 -> 0 at
         08:47:52 once this key took effect.
  allowScreenCapture=True
      SEBController.m:4881   if (!allowScreenCapture || _isAACEnabled)   -> kills screencapture agent
  allowScreenSharing=True
      SEBController.m:4323/:4327/:4332   False ARMS a quit. Never restore False.
  allowDictionaryLookup=True
      SEBController.m:4890   kills QuickLookUIHelper / LookupViewService on macOS 13+
  lockdownModePolicy=1
      Constants.h:320-322  NSUserDefaults+SEBEncryptedUserDefaults.m:775-777  pins AAC off
  enableAppSwitcherCheck=False
      suicide switch SEBController.m:6026, called only from :1198/:4394, both inside
      if (_isAACEnabled == NO)
  detectAccessibilityApps=False
      SEBController.m:3058 adder, :3099 killer, matcher :3110 containsObject: EXACT,
      TCC-derived set (AccessibilityFeaturesManager.swift:200-245) AND
      ProcessManager.prohibitedApplications. CleanShot X (pl.maketheweb.cleanshotx) has
      ZERO hits anywhere -- it is TCC-matched, so no prohibitedProcesses entry can free
      it. THIS KEY IS THE ONLY CONFIG LEVER.
  autoQuitApplications=False
      SEBController.m:3139 read, :3166 graceful terminate. Does NOT stop the hard kill
      at :3161 for strongKill=YES entries -- that is what PROC_KILL is for.

WHY PROC_KILL (prohibitedProcesses deactivated mirrors)
      NSUserDefaults+SEBEncryptedUserDefaults.m:545-595 joins the loaded array against the
      built-in preset and :595 appends every preset entry with no config counterpart. The
      preset contributes 101 macOS entries, 62 with strongKill=@YES.
      A config entry that reproduces a preset entry with active=False and os=0 causes the
      preset twin to be dropped (:582 remove, :584 nil-check preserves our False, :593
      re-add, :595 skipped). ProcessManager.m:100 then filters `active == YES AND os == 0`.
      This is SEB's OWN documented pattern -- :508 calls such an entry "a deliberately
      deactivated preset process". The inactive-preset cleanup is applied ONLY to
      permittedProcesses (SEBConfigFileManager.m:1170-1174), so it survives here.
      WHY NOT permittedProcesses AS A WHITELIST: SEBController.m:3137 ADDS it to the
      prohibited list. ADDITIVE -- a hazard.

KNOWN LIMITATIONS -- not reachable from config
      SEBController.m:4915 kills WritingToolsViewService on macOS 15.1+; UNGATED.
      SEBController.m:7486 spaceSwitch: kills the most-recently-launched app on every
      Space change; gate at :7499 is runtime state, not a config key.
      com.apple.WebKit.Networking is deliberately NOT in PROC_KILL.

Usage: python3 seb_edit_v3.py IN.seb OUT.seb
"""
import hashlib
import os
import plistlib
import sys

EDITS = [
    ("lockdownModePolicy",               1),
    ("allowVirtualMachine",              True),   # v6: VM detection off
    ("enableAltTab",                     True),   # v7
    ("screenSharingMacEnforceBlocked",   False),  # v7
    ("allowSiri",                        True),   # v7: kalau false SEB keluar
    ("allowDictation",                   True),   # v7
    ("allowSwitchToApplications",        True),    # v4: REVERTED to True (Branch A -- app switching back on)
    ("enableAppSwitcherCheck",           False),
    ("allowWindowCapture",               True),
    ("allowScreenCapture",               True),
    ("allowScreenSharing",               True),
    ("allowDictionaryLookup",            True),
    ("browserWindowAllowAddressBar",     True),
    ("enablePrintScreen",                True),
    ("detectAccessibilityApps",          False),
    ("autoQuitApplications",             False),
    # v3 clipboard group -- BOTH OR-operands plus the policy override
    ("enablePrivateClipboard",           False),
    ("enablePrivateClipboardMacEnforce", False),
    ("clipboardPolicy",                  0),
    # v5 multi-screen group -- see docstring
    ("allowDisplayMirroring",            True),
    ("allowedDisplayBuiltin",            True),
    ("allowedDisplayBuiltinEnforce",     False),
    ("allowedDisplaysMaxNumber",         16),
]

# Deactivated mirrors of preset prohibitedProcesses entries, keyed by the field the
# join predicate compares on. Preset line numbers are SEBPresetSettings.m.
PROC_KILL = [
    # v8: SELURUH 101 entri preset macOS dinonaktifkan.
    # Preset menyumbang entri ke prohibitedApplications lewat join di
    # NSUserDefaults+SEBEncryptedUserDefaults.m:545-595; hanya mirror dengan
    # active=False + os=0 yang membuat entri preset itu dibuang.
    # identifier/executable HARUS disalin apa adanya (termasuk tanda *).
    ("com.adiumX.adiumX",                 "Adium"),
    ("com.runningwithcrayons.Alfred*",    "Alfred*"),
    ("com.philandro.anydesk",             "AnyDesk"),
    ("me.tanmay.AnyGPT",                  "AnyGPT"),
    ("com.trankynam.aText",               "aText"),
    ("com.apple.AutoFillPanelService",    "AutoFill"),
    ("",                                  "Brave Browser Helper"),
    ("com.hegenberg.BetterTouchTool*",    "BetterTouchTool"),
    ("com.techsmith.camtasia*",           "Camtasia*"),
    ("com.geekspiff.chickenofthevnc",     "Chicken"),
    ("net.sourceforge.chicken",           "Chicken"),
    ("com.google.chrome",                 "Chrome"),
    ("com.google.chrome.remote_desktop.native-messaging-host", "Chrome Remote Desktop Host"),
    ("com.google.ChromeRemoteDesktop",    "Chrome Remote Desktop Host"),
    ("",                                  "Chromium Helper"),
    ("com.connectwise.control*",          "ConnectWise Control Client"),
    ("app.cotypist.Cotypist",             "Cotypist"),
    ("com.apple.DataDetectorsViewService", "DataDetectorsViewService"),
    ("com.kapeli.dashdoc",                "Dash"),
    ("com.hnc.Discord*",                  "Discord"),
    ("com.dosdude1.Discord-Lite",         "Discord Lite"),
    ("com.dwservice.dwagent",             "DWAgent"),
    ("im.riot.app",                       "Element (Riot)"),
    ("com.federicoterzi.espanso",         "espanso"),
    ("com.apple.FaceTime",                "FaceTime"),
    ("com.red-sweater.fastscripts3",      "FastScripts"),
    ("org.mozilla.plugincontainer",       "plugin-container"),
    ("",                                  "Google Chrome Helper"),
    ("com.logmein.GoToMeeting",           "GoToMeeting"),
    ("com.electron.guilded",              "Guilded"),
    ("org.hammerspoon.Hammerspoon",       "Hammerspoon"),
    ("com.pais.handy",                    "Handy"),
    ("com.islonline.ISLLight*",           "ISL Light"),
    ("com.googlecode.iterm2",             "iTerm2"),
    ("com.logmein.join.me",               "Join.me"),
    ("com.p5sys.jump.mac.viewer",         "Jump Desktop"),
    ("com.p5sys.jump.mac.connect",        "Jump Desktop Connect"),
    ("org.pqrs.Karabiner*",               "Karabiner-Elements"),
    ("app.keysmith.Keysmith",             "Keysmith"),
    ("com.stairways.keyboardmaestro.editor", "Keyboard Maestro"),
    ("com.stairways.keyboardmaestro.engine", "Keyboard Maestro Engine"),
    ("com.apple.inputmethod.AssistiveControl", "Keyboard Viewer (Assistive Control)"),
    ("com.logmein.LogMeIn*",              "LogMeIn"),
    ("com.loom.desktop",                  "Loom"),
    ("com.apple.iChat",                   "Messages"),
    ("com.apple.MobileSMS",               "Messages"),
    ("com.microsoft.Communicator",        "Microsoft Communicator"),
    ("",                                  "Microsoft Edge Helper"),
    ("com.microsoft.Lync",                "Microsoft Lync"),
    ("com.microsoft.rdc.macos",           "Microsoft Remote Desktop"),
    ("com.moonlight-stream.Moonlight",    "Moonlight"),
    ("com.microsoft.teams2",              "MSTeams"),
    ("com.nomachine.nxplayer",            "NoMachine"),
    ("com.obsproject.obs-studio",         "OBS"),
    ("",                                  "Opera Helper"),
    ("com.parallels.access*",             "Parallels Access"),
    ("com.raycast.macos",                 "Raycast"),
    ("com.parsec.Parsec",                 "Parsec"),
    ("com.brnbw.Poof",                    "Poof"),
    ("com.parsecgaming.parsec",           "Parsec"),
    ("com.tapbots.Pastebot2Mac",          "Pastebot"),
    ("com.bartelsmedia.PhraseExpressOSX", "PhraseExpress"),
    ("com.pilotmoon.popclip",             "PopClip"),
    ("com.remotepc.RemotePCDesktop",      "RemotePC"),
    ("com.remoteutilities.*",             "Remote Utilities*"),
    ("com.carriez.rustdesk",              "RustDesk"),
    ("com.witt-software.Rocket-Typist*",  "Rocket Typist"),
    ("com.apple.WebKit.Networking",       "Safari/WebKit Networking"),
    ("com.apple.ScreenSharing",           "Screen Sharing"),
    ("com.elsitech.screenconnect.client", "Screenconnect"),
    ("com.edovia.screens*",               "Screens*"),
    ("com.skype.skype",                   "Skype"),
    ("com.microsoft.SkypeForBusiness",    "Skype for Business"),
    ("com.tinyspeck.slackmacgap",         "Slack"),
    ("pl.wojciechkulik.Snippety",         "Snippety"),
    ("com.mersive.solstice.client",       "SolsticeClient"),
    ("com.splashtop.*",                   "Splashtop*"),
    ("com.nanosystems.Supremo*",          "Supremo"),
    ("",                                  "sunshine"),
    ("io.cryptoalgo.swiftcord",           "Swiftcord"),
    ("com.microsoft.teams",               "Teams"),
    ("com.apptorium.TeaCode*",            "TeaCode"),
    ("com.teamviewer.TeamViewer",         "TeamViewer"),
    ("com.TeamViewer.TeamViewer",         "TeamViewer"),
    ("ru.keepcoder.Telegram",             "Telegram"),
    ("com.smileonmymac.textexpander",     "TextExpander"),
    ("com.unmarked.textsoap",             "TextSoap"),
    ("com.apple.Terminal",                "Terminal"),
    ("com.youqu.todesk*",                 "ToDesk"),
    ("com.creativeapplicationsnet.textexp", "Typexp"),
    ("com.macility.typinator2",           "Typinator"),
    ("com.typeit4me.TypeIt4MeMenu",       "TypeIt4Me"),
    ("com.apple.universalcontrol",        "Universal Control"),
    ("",                                  "Vivaldi Helper"),
    ("org.videolan.vlc",                  "VLC"),
    ("com.realvnc.vncviewer",             "VNC Viewer"),
    ("",                                  "vncserver"),
    ("lol.peril.voxa",                    "Voxa"),
    ("com.wunderpen.app",                 "WunderType"),
    ("com.cisco.webex.webexmta",          "webexmta"),
    ("us.zoom.xos",                       "zoom.us"),
]

PRESERVE = ("startURL", "examKeySalt", "originatorVersion", "sebConfigPurpose")

# Schema for a prohibitedProcesses entry -- SEBSettings.m:1214-1227.
PROC_SCHEMA = {
    "active": True,
    "allowedExecutables": "",
    "currentUser": False,
    "description": "",
    "executable": "",
    "identifier": "",
    "ignoreInAAC": True,
    "originalName": "",
    "os": 0,
    "strongKill": False,
    "user": "",
    "windowHandlingProcess": "",
}


def make_entry(identifier, executable):
    """A deactivated mirror. active=False and os=0 are BOTH mandatory:
    the match predicate returns NO on a nil `active`
    (NSUserDefaults+SEBEncryptedUserDefaults.m:482) and compares `os` first (:489)."""
    e = dict(PROC_SCHEMA)
    e["identifier"] = identifier
    e["executable"] = executable
    e["originalName"] = executable or identifier
    e["active"] = False
    e["os"] = 0
    e["strongKill"] = False
    e["ignoreInAAC"] = False
    e["description"] = "deactivated mirror (see seb_edit_v3.py docstring)"
    return e


def main():
    if len(sys.argv) != 3:
        print("usage: seb_edit_v3.py IN.seb OUT.seb")
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
    print("%-36s %-22s %-22s" % ("KEY", "BEFORE", "AFTER"))
    print("-" * 84)
    for k, v in EDITS:
        old = repr(d[k]) if k in d else "ABSENT"
        d[k] = v
        print("%-36s %-22s %-22s" % (k, old[:22], repr(v)))
    print("-" * 84)

    # ---- prohibitedProcesses surgery -------------------------------------
    pp = d.get("prohibitedProcesses")
    if pp is None:
        pp = []
        print("%-36s %-22s" % ("prohibitedProcesses", "ABSENT -> created"))
    if not isinstance(pp, list):
        print("REFUSE: prohibitedProcesses is not a list:", type(pp).__name__)
        return 2
    pp = list(pp)
    existing = {
        (e.get("identifier") or "").lower() or (e.get("executable") or "").lower()
        for e in pp
        if isinstance(e, dict)
    }
    added = []
    for ident, exe in PROC_KILL:
        tag = (ident or exe).lower()
        if tag in existing:
            print("SKIP  %-44s (already present)" % (ident or exe))
            continue
        pp.append(make_entry(ident, exe))
        added.append((ident, exe))
        print("ADD   %-44s active=False os=0" % (ident or exe))
    base_len = len(d.get("prohibitedProcesses") or [])
    d["prohibitedProcesses"] = pp
    print("PROHIBITED: %d -> %d entries (+%d)" % (base_len, len(pp), len(added)))
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

    assert len(c["prohibitedProcesses"]) == base_len + len(added), \
        ("ARRAY COUNT FAIL", base_len, len(added), len(c["prohibitedProcesses"]))
    want = {(i or e).lower() for i, e in added}
    seen = set()
    for e in c["prohibitedProcesses"]:
        tag = (e.get("identifier") or "").lower() or (e.get("executable") or "").lower()
        if tag in want and e is not None:
            seen.add(tag)
    assert seen == want, ("ARRAY ENTRIES LOST", sorted(want - seen))
    for e in c["prohibitedProcesses"]:
        if e.get("active") is False:
            assert e.get("os") == 0, ("BAD os", e)
            assert e.get("strongKill") is False, ("BAD strongKill", e)
    was_inactive = {
        (e.get("identifier") or "").lower() or (e.get("executable") or "").lower()
        for e in (before.get("prohibitedProcesses") or [])
        if isinstance(e, dict) and e.get("active") is False
    }
    now_inactive = {
        (e.get("identifier") or "").lower() or (e.get("executable") or "").lower()
        for e in c["prohibitedProcesses"]
        if e.get("active") is False
    }
    assert now_inactive - was_inactive == want, \
        ("UNINTENDED DEACTIVATION", sorted((now_inactive - was_inactive) - want))

    edited = {k for k, _ in EDITS} | {"prohibitedProcesses"}
    assert set(before) - set(c) == set(), ("KEYS LOST", set(before) - set(c))
    for k in set(before) - edited:
        assert c[k] == before[k], ("UNINTENDED CHANGE", k)

    with open(src, "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == src_sha, "INPUT WAS MODIFIED"

    print()
    print("SELFCHECK: OK - %d keys set, %d array entries added, %d keys preserved, "
          "input byte-identical"
          % (len(EDITS), len(added), len(before) - len({k for k, _ in EDITS if k in before})))
    print("  allowSwitchToApplications        %r   <- must be True (Branch A)" % c["allowSwitchToApplications"])
    print("  enablePrivateClipboard           %r" % c["enablePrivateClipboard"])
    print("  enablePrivateClipboardMacEnforce %r" % c["enablePrivateClipboardMacEnforce"])
    print("  clipboardPolicy                  %r" % c["clipboardPolicy"])
    print("  allowedDisplaysMaxNumber         %r   <- must be 16" % c["allowedDisplaysMaxNumber"])
    print("  allowDisplayMirroring            %r" % c["allowDisplayMirroring"])
    print("  allowedDisplayBuiltin            %r" % c["allowedDisplayBuiltin"])
    print("  allowedDisplayBuiltinEnforce     %r" % c["allowedDisplayBuiltinEnforce"])
    for k in PRESERVE:
        if k in c:
            print("  %-32s %r" % (k, c[k]))
    out_sha = hashlib.sha256(open(dst, "rb").read()).hexdigest()
    print("  OUTPUT sha256                    %s" % out_sha)
    return 0


sys.exit(main())
