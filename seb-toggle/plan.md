# SEB Config Toggle — Build Plan

Target: a CLI that reads a `.seb` config, reports which restrictions are **actually active**,
lets the operator toggle any of them, and writes a new `.seb`.

Status: plan only. No implementation until this document is accepted.
Date: 2026-09-27

---

## 1. Why this is a net-new build

`grep -c "plist"` → `tools/seb.py:0`, `tools/seb_maintenance.py:0`, `tools/seb_updater_app.py:0`.
Those three are patch/version tooling. Nothing to extend.

`setups/seb_edit.py` (1752 B) is the closest prior art, and its failure mode is the reason
this plan exists. It toggles a **hardcoded list of 8 keys** and writes them unconditionally:

| Its key | Reality |
|---|---|
| `allowWindowCapture` | not a key in any sample; 3.10.2 uses `allowScreenSharing` → `Security.AllowWindowCapture` |
| `allowScreenCapture` | not a key in any sample |
| `allowScreenSharing` | real, but written bare without preserving siblings |
| `lockdownModePolicy` | **appears nowhere in the 3.10.2 tree** — legacy SEB-2.x key |

Result: the tool **adds keys the file never had**. Adding `allowScreenSharing=False` to a file
that omitted it is not a no-op — it changes the diff, breaks the `config (1)` / `config (2)`
equivalence, and makes the config unrecognizable to whoever authored it.

Rule for this build: **the toggle set is derived from the actual file plus a generated
registry, never from a hardcoded list.**

---

## 2. Measured ground truth

All numbers below were produced by running the commands in §11 against the on-disk artifacts.
None are estimates.

### 2.1 Registry

`SafeExamBrowser.Configuration.ConfigurationData/Keys.cs` declares **219 `internal const string`
declarations across 33 nested classes**, mapping onto **217 distinct wire values**. The two
collisions are real and are themselves a finding:

```
"active"            <- const Active          | const RuleIsActive
"allowScreenSharing" <- const AllowWindowCapture | const EnableRemoteConnections
```

`Keys.cs` gives one wire value two constant names, in two different nested classes. A key name
therefore cannot be assumed to identify the settings property it feeds — which is the structural
reason §2.3's mapper table is load-bearing rather than decorative.

Table — nested class → declarations / present in `config (1)`:

| Category | Decls | In config (1) |
|---|---|---|
| `Keys.Browser` | 38 | 34 |
| `Keys.Keyboard` | 19 | 19 |
| `Keys.Applications` | 17 | 2 |
| `Keys.Security` | 16 | 10 |
| `Keys.Service` | 16 | 15 |
| `Keys.Server` | 15 | 1 |
| `Keys.Proctoring.ScreenProctoring` | 11 | 0 |
| `Keys.Browser.MainWindow` | 9 | 9 |
| `Keys.Browser.AdditionalWindow` | 8 | 8 |
| `Keys.Browser.Filter` | 7 | 3 |
| `Keys.Browser.Proxy` | 6 | 2 |
| `Keys.Browser.Proxy.Ftp` | 6 | 0 |
| `Keys.Browser.Proxy.Http` | 6 | 0 |
| `Keys.Browser.Proxy.Https` | 6 | 0 |
| `Keys.Browser.Proxy.Socks` | 6 | 0 |
| `Keys.Display` | 4 | 3 |
| `Keys.Audio` | 3 | 3 |
| `Keys.ConfigurationFile` | 3 | 2 |
| `Keys.Network.Certificates` | 3 | 1 |
| `Keys.Proctoring.ScreenProctoring.MetaData` | 3 | 0 |
| `Keys.General` | 2 | 1 |
| `Keys.Mouse` | 2 | 2 |
| `Keys.UserInterface.SystemControls.PowerSupply` | 2 | 0 |
| `Keys.UserInterface.Taskbar` | 2 | 2 |
| `Keys.Proctoring` | 1 | 0 |
| `Keys.System` | 1 | 0 |
| `Keys.UserInterface` | 1 | 1 |
| `Keys.UserInterface.ActionCenter` | 1 | 1 |
| `Keys.UserInterface.LockScreen` | 1 | 0 |
| `Keys.UserInterface.SystemControls.Audio` | 1 | 1 |
| `Keys.UserInterface.SystemControls.Clock` | 1 | 1 |
| `Keys.UserInterface.SystemControls.KeyboardLayout` | 1 | 1 |
| `Keys.UserInterface.SystemControls.Network` | 1 | 1 |

Column sum: **219 declarations**, 217 distinct. `build_registry.py` emits `categories` keyed by
declaration and `const_collisions` recording both clashes; both are surfaced rather than
silently de-duplicated.

`rawData.TryGetValue("...")` and `key == "..."` literals across `DataMapping/*.cs` add **no keys
outside `Keys.cs`** — 142 dispatch keys, all of them already constants in `Keys.cs`, and
`dispatch key not in Keys.cs : none` on a clean run. `MapGlobal` reads no additional keys (both
implementations return empty lists).

**But the mapper grep is still required**, because it produces the `key → Map* method` edge used
in §2.3, and `Keys.cs` alone does not carry that.

### 2.2 Coverage of the real samples

```
config (1).seb          191 keys   122 recognized by 3.10.2    69 ignored
config (2).seb          191 keys   122 recognized by 3.10.2    69 ignored
SebClientSettings.seb   206 keys   137 recognized by 3.10.2    69 ignored
```

The ignored count is **69 in every sample**, but the ignored *set* is not identical across the
corpus — the two shapes differ by exactly two keys:

| key | in `config` siblings | in `SebClientSettings` | in `Keys.cs` |
|---|---|---|---|
| `allowDownUploads` | present (`True`) | absent | no |
| `lockdownModePolicy` | absent | present (`1`) | no |

Both are legacy keys absent from `Keys.cs`, so each is ignored wherever it appears; the count
stays 69 because each shape contributes exactly one key the other lacks. The **union of ignored
keys across the corpus is 70**.

The ignored keys are **macOS / SEB-2.x legacy**. A whole-tree literal scan of all 318 `.cs`
files in the 3.10.2 tree finds **353 distinct string literals**, and 69 of `config (1)`'s keys
appear in none of them. Cross-check against the macOS source tree (`research/seb-mac-src`; a
scan of the Objective-C / Swift / C sources alone yields **9,009 distinct literals**):
**69 of the 70 are present there**. The single residual, `additionalDictionaries`, is a macOS
spelling-dictionary array (`[]` in the sample) — unclassified by literal search, attributed to
the same origin.

`originatorVersion = SEB_Win_2.1.1` in all three samples confirms the provenance.

### 2.3 Dispatch and defaults

Parsing `private void Map*(AppSettings settings, object value)` bodies in `DataMapping/*.cs`:

- **140** methods assign to a `settings.*` property
- **142** config keys have a `key == "..." → Map*(settings, ...)` edge
- **16** of those methods apply an **inversion** — the key value is negated on the way into the typed model

The 16 inversions (verbatim from the decompiled bodies):

| Mapper | Method | Assignment |
|---|---|---|
| BrowserDataMapper | `MapDownloadPdfFiles` | `Browser.AllowPdfReader = !flag` |
| ConfigurationFileDataMapper | `MapConfigurationMode` | `ConfigurationMode = ((num != 1) ? Exam : ConfigureClient)` |
| SecurityDataMapper | `MapVirtualMachinePolicy` | `Security.VirtualMachinePolicy = ((!flag) ? Deny : Allow)` |
| ServiceDataMapper | `MapEnableChromeNotifications` | `Service.DisableChromeNotifications = !flag` |
| ServiceDataMapper | `MapEnableEaseOfAccessOptions` | `Service.DisableEaseOfAccessOptions = !flag` |
| ServiceDataMapper | `MapEnableFindPrinter` | `Service.DisableFindPrinter = !flag` |
| ServiceDataMapper | `MapEnableNetworkOptions` | `Service.DisableNetworkOptions = !flag` |
| ServiceDataMapper | `MapEnablePasswordChange` | `Service.DisablePasswordChange = !flag` |
| ServiceDataMapper | `MapEnablePowerOptions` | `Service.DisablePowerOptions = !flag` |
| ServiceDataMapper | `MapEnableRemoteConnections` | `Service.DisableRemoteConnections = !flag` |
| ServiceDataMapper | `MapEnableSignout` | `Service.DisableSignout = !flag` |
| ServiceDataMapper | `MapEnableTaskManager` | `Service.DisableTaskManager = !flag` |
| ServiceDataMapper | `MapEnableUserLock` | `Service.DisableUserLock = !flag` |
| ServiceDataMapper | `MapEnableUserSwitch` | `Service.DisableUserSwitch = !flag` |
| ServiceDataMapper | `MapEnableVmwareOverlay` | `Service.DisableVmwareOverlay = !flag` |
| ServiceDataMapper | `MapEnableWindowsUpdate` | `Service.DisableWindowsUpdate = !flag` |

Fourteen of these map directly onto keys present in `config (1)`:
`insideSebEnableLogOff`, `enableChromeNotifications`, `allowScreenSharing`,
`insideSebEnableChangeAPassword`, `insideSebEnableSwitchUser`, `allowVirtualMachine`,
`insideSebEnableStartTaskManager`, `insideSebEnableLockThisComputer`, `insideSebEnableShutDown`,
`insideSebEnableVmWareClientShade`, `insideSebEnableNetworkConnectionSelector`,
`insideSebEnableEaseOfAccess`, `downloadPDFFiles`, `enableWindowsUpdate`.

**Why this table matters even though the toggle works on raw values (§4):** it is the difference
between reporting "`allowScreenSharing = False`" and reporting "**remote connections are
disabled**". The key name lies about its meaning — `allowScreenSharing` is the key, but it
drives `Service.DisableRemoteConnections`. A report that reads key names produces wrong findings.

`DataValues.LoadDefaultSettings()` constructs a fully-populated `AppSettings` literal with
**149 leaf assignments**. 75 of the 191 config keys join to a property that carries a literal
there. The join is the basis for the "this key is absent, SEB will use X" column in the scan
output. The remaining 47 recognised keys split into two disjoint buckets, and both are reported
rather than dropped:

| bucket | n | reason | handling |
|---|---|---|---|
| `join` | 75 | mapper method + property + code default | §2.4 comparison |
| `nodefault` | 22 | mapper method exists; the property has no `LoadDefaultSettings()` literal | `default = n/a`, never claimed as an author edit |
| `nomap` | 25 | no dispatch edge at all — URLFilter / audio / user-agent / `permittedProcesses` families | resolved by the 2 global handlers (§2.3) |

75 + 22 + 25 = 122 recognised. The 69 keys ignored by 3.10.2 are the remainder of 191.

### 2.4 What the defaults reveal — and a corrected claim

(Instrumentation for this section, including the `nodefault` counter that a naive loop omits,
is defined in §2.2; the bucket split is tabulated there.)

Joining each key to its mapped `AppSettings` property (§2.3), applying the mapper inversion, and
comparing to the literal default:

```
join 75 | boolean 67 | match-default 66 | differs 1 | non-boolean 8 | nomap 25 | nodefault 22

The naive loop drops the `nomap` 25 via its `continue` on a missing dispatch edge; stating all
three buckets is what makes 122 reconcile. `non-boolean` is the 8 joined keys whose file value or
code default is not a bool; measured for `config (1)`, all 8 carry a non-bool *default literal*
(`VirtualMachinePolicy.*`, `UserInterfaceMode.*`, ...), not a non-bool file value.
```

The single deviation in the entire config:

```
sendBrowserExamKey   file=True  ->  Browser.SendConfigurationKey = True   (code default = False)

The arrow is file-value -> mapped-property-value. `sendBrowserExamKey` is the 1 `differs`. The
deviation PERMITS (the file sends the exam key where SEB's default would not), so it is reported
as PERMISSIVE / author-imposed, not as a restriction.
```

**This section previously claimed the opposite and is corrected here.** The earlier pass diffed
raw config values directly against raw property defaults, and — because 14 of the mapped
properties are `!flag`-inverted — reported:

> "14 keys where the file is stricter than code default … each `False` is an explicit restrictive
> act by the author."

That comparison was invalid. It compared a raw config flag against an inverted property default.
The corrected arithmetic:

- `Service.Disable*` defaults in the literal are **all `true`**
- the ServiceDataMapper methods assign `Disable* = !flag`
- so a config `False` yields `Disable* = true` — **exactly the default**, not an edit

`insideSebEnableLogOff`, `insideSebEnableShutDown`, `insideSebEnableStartTaskManager`,
`insideSebEnableSwitchUser`, `insideSebEnableLockThisComputer`, `insideSebEnableEaseOfAccess`,
`insideSebEnableChangeAPassword`, `insideSebEnableNetworkConnectionSelector`,
`insideSebEnableVmWareClientShade`, `allowScreenSharing`, `downloadPDFFiles`,
`enableChromeNotifications`, `enableWindowsUpdate` — all 13 are **stock SEB posture, written out
explicitly**. The author changed one thing in this file: `sendBrowserExamKey`.

**Consequence for the scan output.** "Active restriction" is ambiguous, and a report that does
not disambiguate is reporting SEB's own defaults back to the user as if they were findings. The
DEFAULT column therefore carries three states:

| State | Test |
|---|---|
| **RESTRICTION — author-imposed** | effective value restricts, and differs from the code default |
| **RESTRICTION — SEB default** | effective value restricts, and equals the code default |
| PERMISSIVE | effective value permits |

On `config (1)`: **1 author-imposed deviation, 66 keys at stock default, 8 non-boolean.**

## 3. Input handling

### 3.1 Format detection

Order of checks, first match wins:

1. Read the first 4 bytes. If ASCII is one of `plnd` / `pswd` / `pwcc` / `pkhs` / `phsk` →
   **SEB binary container** (`BinaryParser.cs` + `GZipCompressor.cs`). Out of scope.
   Print: detected format, prefix, byte size, and the `BinaryParser` reference. Refuse cleanly.
2. `plistlib.load(f, fmt=None)` — handles XML and binary plists. Success → proceed.
3. On `plistlib.InvalidFileException` / `ExpatError` → report actual leading bytes in hex,
   state "not a plist and not a recognized SEB container", refuse.

Never crash on malformed input. Never write output for a refused input.

### 3.2 Encrypted configs

`SebClientSettings.seb` carries `useAsymmetricOnlyEncryption = True`. The scan pass reads and
reports this flag; if the file declares encryption, emit a prominent warning that the local
override caveat in §7 does not apply and stop before the toggle phase. Detection is a key read,
not a format inspection — the plist parses either way.

### 3.3 Non-XML output

`plistlib.dump(..., fmt=FMT_XML)` always. SEB's own writer emits XML (`XmlParser` is the
primary path); binary plist output would round-trip through `plistlib` but is unverified
against the real client. Do not ship unverified format.

---

## 4. Value-semantics layer

### 4.1 The polarity model

Across the whole corpus, **for boolean keys the raw value is consistent: `True` permits,
`False` restricts** — regardless of whether the C# mapper inverts it into a `Disable*` property.
This holds for every `allow*` and `enable*` key including all 14 inverted ones.

So the toggle operates on raw values with a **direct** polarity, and the §2.3 inversion table is
carried as **display metadata**: it explains which restriction a key actually controls, without
altering how the toggle writes.

### 4.2 The exception set (non-boolean or flipped polarity)

These cannot be toggled as booleans. Each gets an explicit value model:

| Key(s) | Type | Model |
|---|---|---|
| `clipboardPolicy` | int | `0 → Allow`, `1 → Block`, other → `Isolated` |
| `createNewDesktop`, `killExplorerShell` | bool pair | mutually exclusive → `KioskMode { None, CreateNewDesktop, DisableExplorerShell }`; True is *more* restrictive |
| `sebMode` | int | `1 → Server`, else `Normal` |
| `browserViewMode` | int | `1 → FullScreen`, `0 → Windowed`. Listed in `INT_BOOL_KEYS`; the raw wire form is `1`/`0`, never a bool |
| `allowVirtualMachine` | bool | `True → Allow`, `False → Deny`. Bool-valued, so the §5.1 bool branch MUST consult `ENUM_SPACES` before emitting `permits`/`restricts` — otherwise the label never renders |
| `sebConfigPurpose` | int | `1 → ConfigureClient`, else `Exam`. The wire key is `sebConfigPurpose`; `configurationMode` does not exist in `Keys.cs` |
| `touchOptimized` | bool | `True → Mobile`, `False → Desktop`. Has no dispatch edge, so it resolves only through `ENUM_SPACES`. Its inversion is a ternary in `MapUserInterfaceMode`, not a registry `inverted` entry |
| `proxyPolicy` | int | `Custom` / `System` |
| `hashedAdminPassword`, `hashedQuitPassword` | str | presence = restriction; empty = none |
| `allowedDisplaysMaxNumber` | int | `1` = single-display restriction |
| `prohibitedProcesses`, `permittedProcesses` | array | non-empty = restriction/allowlist active |
| `examKeySalt` | bytes | must be base64'd in any JSON sidecar |

The toggle UI surfaces these as **choice** entries (`Auto / Allow / Block / Isolated`) rather
than flip-on/off, and refuses to write a value outside the extracted enum space.

### 4.3 Absent-key semantics

`AppSettings()` and `SecuritySettings()` constructors set no values (only `new`-up sub-objects
and `VersionRestrictions = new List<>()`). There is no `Defaults` / `DefaultValues` class in
the tree. Therefore an absent boolean is CLR `false`.

Presented as a distinct status — **ABSENT-DEFAULTED** — with the effective value shown, so the
operator can see that omitting `enableAltTab` does not mean "unset", it means "blocked".

Default write policy: **absent keys are not written unless the operator explicitly opts in.**
This is the direct fix for `seb_edit.py`'s defect. Adding a key is reported as an addition in the
output diff, never as a silent edit.

---

## 5. Scan pass

`seb_toggle.py <file.seb> --scan`

### 5.1 Classification

For every key in the file, classify on two axes — what the effective value does, and whether
that posture is the author's doing or SEB's (§2.4):

| Status | Condition |
|---|---|
| **RESTRICTION — author-imposed** | effective value restricts, and differs from the code default |
| **RESTRICTION — SEB default** | effective value restricts, and equals the code default |
| **PERMISSIVE** | recognized, effective value permits |
| **MODE-SELECTOR** | non-boolean; show the resolved enum/int meaning |
| **IGNORED-BY-3.10.2** | absent from the 219-declaration registry — printed in its own section |
| **ABSENT-DEFAULTED** | in registry, not in file; effective = code default |

The author-imposed / SEB-default split is not cosmetic. Without it the report cannot be
distinguished from SEB reading its own defaults back to the operator: on `config (1)` it is the
difference between reporting **1** real edit and **67** rows of noise (§2.4). Keys with no
joinable code default (§2.3) report `DEFAULT n/a` and are never claimed as author-imposed —
absence of a default is not evidence of an edit.

`ABSENT-DEFAULTED` rows are shown and counted but are **not toggleable** unless `--add-missing`
is passed (§4.3): writing a key the file never had is not a no-op, it makes the config
unrecognisable to its author.

### 5.2 Grouping and row shape

Grouped by the `Keys.cs` category path — **33 buckets, read from `seb_registry.json`, never
hardcoded** (§2.1). Each row:

```
STATUS                     KEY                        FILE      EFFECTIVE   DEFAULT   CONTROLS
PERMISSIVE                 sendBrowserExamKey = True    True    permits     author-imposed  Browser.SendConfigurationKey
RESTRICTION SEB default    allowScreenSharing = False   False   restricts   SEB default     Service.DisableRemoteConnections   [inverted]
RESTRICTION                allowVirtualMachine = False  False   Deny        n/a             Security.VirtualMachinePolicy      [inverted, enum]
PERMISSIVE                 enableAltTab = True          True    permits     SEB default     Keyboard.AllowAltTab
RESTRICTION SEB default    downloadPDFFiles = False     False   restricts   SEB default     Browser.AllowPdfReader             [inverted]
MODE-SELECTOR              browserViewMode = 1          -       FullScreen  n/a             Browser.MainWindow.FullScreenMode  [int-bool]
IGNORED-BY-3.10.2          forceAppFolderLocation       -       n/a         n/a             (macOS / SEB 2.x)
```

`FILE` is the raw value as written. `EFFECTIVE` is the value after the mapper (§4.1).
`DEFAULT` is the `LoadDefaultSettings()` literal for the mapped property, or `n/a`.
`CONTROLS` comes from the §2.3 dispatch table — this is the column that makes the report
readable, because a key name does not identify its property (§2.1 collisions:
`allowScreenSharing` drives remote connections, *not* window capture).

### 5.3 Summary header

Total keys, RESTRICTION author-imposed, RESTRICTION SEB default, PERMISSIVE, MODE-SELECTOR,
IGNORED-BY-3.10.2, ABSENT-DEFAULTED, plus `originatorVersion` and the encryption flag.

The two restriction counts are printed separately, and the author-imposed count leads. A header
that merges them states a number the file does not support.

## 6. Toggle UX

```
seb_toggle.py <file.seb> [options]

  (no flag)                 scan, then interactive toggle
  --scan                    report only, no prompt
  --scan --only-ignored     the 69 legacy keys and nothing else
  -c/--category <name>      narrow the toggle menu to one registry category
  -s/--set key=value        non-interactive; repeatable
  -a/--add-missing          allow writing keys the file does not contain
  -y/--yes                  skip the confirm prompt
  -o/--out <path>           default: <stem>.modified.seb
  --diff <other.seb>        compare two configs, report differing keys
```

Interactive flow:

1. Print the scan report.
2. Print the toggle menu **grouped by category**, numbered, showing current effective value and
   the restriction it controls. Only keys the file actually contains are toggleable by default.
3. Accept `3`, `3,7,12`, `12-18`, `all`, `none`, `done`.
4. For each selection, flip to the permissive end (`True` / `Allow`) or offer a choice for
   MODE-SELECTOR entries.
5. Print a preview diff: `key: old → new`, additions listed separately and labelled.
6. Confirm. On `y`, write. On `n`, return to the menu without touching disk.

`safe` default: writing requires explicit confirmation. `--yes` is the only bypass.

### 6.1 Relaxation profile

`--unlock-all` and the interactive `unlock` command queue `UNLOCK_BOOL` / `UNLOCK_ENUM` /
`UNLOCK_LISTS` — a curated set, deliberately **not** a blanket flip. Measured on `config (1)`:
34 keys move; 36 `prohibitedProcesses` entries go `active` True -> False; `killExplorerShell`
stays `False`; `URLFilterEnable` stays `False`; `audioMute` stays `False`; `createNewDesktop`
goes `True -> False`. Applying the profile to an already-open config is a no-op (0 differing
keys). `verify()` passes all 5 assertions including the list-valued intended write.

---

## 7. Output write and self-verification

Write to a **new file**, never in place. Default `<stem>.modified.seb`.

Before declaring success, the tool re-opens the output and asserts:

1. Every intended key changed to the intended value.
2. **No other key changed** — full key-set and value comparison against the input.
3. No key was added unless `--add-missing` was passed.
4. `startURL` and every other non-selected key are byte-identical in value.
5. Report byte delta (input size → output size) and the exact key-count delta.

Any assertion failure → delete the output, report the violated assertion. No partial writes.

---

## 8. Files

```
setups/
  plan.md                  this document
  build_registry.py        regenerates seb_registry.json from the decompiled tree
  seb_registry.json        GENERATED artifact (never hand-edited)
  seb_toggle.py            the CLI
  seb_gui.py               Tkinter front-end; calls seb_toggle, holds no logic of its own
  make_icon.py             generates seb.ico + icons/ (build asset, not runtime)
  build-macos.sh           PyInstaller .app build, macOS only
  SEB-Toggle.exe           frozen GUI (Windows)
  seb-toggle-cli.exe       frozen CLI (Windows)
  dist/windows/            frozen Windows output: SEB-Toggle.exe + seb-toggle-cli.exe
  dist/macos/              frozen macOS output: SEB Toggle.app + seb-macos.tar.gz + seb-toggle-cli
  tools/                   manifest.py, inspect_seb.py (read-only helpers)
```

`seb_registry.json` schema:

```json
{
  "source": ".../seb3.10.2_decompiled",
  "keys":       { "<key>": "<Category.Path>" },      // 217, first-seen category wins
  "categories": { "<Category.Path>": ["<key>", …] }, // 33 groups, 219 declarations total
  "const_collisions": { "<key>": ["<Const>", …] },   // 2 wire values carrying 2 consts each
  "dispatch":   { "<key>": "<MapMethod>" },          // 142 edges
  "methods":    { "<MapMethod>": {"file": "…", "prop": "…", "expr": "…", "inverted": true} },
  "global_handlers": [ … ],                          // 2
  "defaults":   { "<AppSettings.Property>": "<literal>" },  // 149 leaves
  "generated_at": "<ISO8601>"
}
```

**Why `keys` is 217 and `categories` sums to 219.** `Keys.cs` declares 219
`internal const string`, but two of them are second consts onto an already-declared wire
value:

```
"active"             <- const Active              | const RuleIsActive
"allowScreenSharing" <- const AllowWindowCapture  | const EnableRemoteConnections
```

`keys` uses `setdefault`, so one category wins and the count is 217. `categories` appends
every declaration, so it sums to 219. **Any assertion of the form
`sum(len(v) for v in categories.values()) == len(keys)` fails by exactly 2 by design.**
`const_collisions` is emitted so the gap stays auditable rather than silently swallowed.

The `allowScreenSharing` collision is load-bearing for correctness, not bookkeeping:
that wire key drives `Service.DisableRemoteConnections`, **not** window capture, despite
also carrying the const name `AllowWindowCapture`. A report that reads key names alone
produces wrong findings — hence the collision warning in the scan header (§5.3).

Generated by `build_registry.py`, not typed by hand. A SEB version bump is a re-run, not a
rewrite. `build_registry.py` takes the decompiled root as an argument so 3.10.1 / 3.7.1 trees
can be diffed against 3.10.2 with the same tool.

`seb_edit.py` is left untouched — it is prior art, not a dependency.

---

## 9. Verification plan

### 9.1 Regression pair

`config (1).seb` and `config (2).seb` differ in **exactly one key**, verified by running it:
`startURL` (`...quiz/view.php?id=156512` vs `...id=87025`).

**Test A — no-op round trip.**
```
seb_toggle.py "config (1).seb" --scan -o /tmp/a.seb     # no toggles selected
```
Assert: `--diff /tmp/a.seb "config (1).seb"` reports zero differing keys, zero added, zero removed.

**Test B — single toggle.**
```
seb_toggle.py "config (1).seb" -s downloadPDFFiles=true -y -o /tmp/b.seb
```
Assert: exactly one key differs from input, it is `downloadPDFFiles`, and its value is `True`.

> The key must be one that actually changes. `enableAltTab` is **already `True`** in both sample
> files, so toggling it to `true` is a no-op and asserts nothing — an earlier draft of this plan
> used it for B and C and would have passed vacuously. `downloadPDFFiles` is `False` in
> `config (1)`, so the assertion has content.

**Test C — round-trip parity.**
```
seb_toggle.py "config (1).seb" -s downloadPDFFiles=true  -y -o /tmp/c1.seb
seb_toggle.py /tmp/c1.seb      -s downloadPDFFiles=false -y -o /tmp/c2.seb
seb_toggle.py --diff /tmp/c2.seb "config (1).seb"
```
Assert: `/tmp/c2.seb` equals `config (1)` on **every** key — zero differences.

This is the end-to-end proof. A single toggle cannot be validated against `config (2)`, because
`config (1)` and `config (2)` differ only in `startURL`, which is a string and not a toggle —
any toggle-based comparison against `config (2)` would be comparing two identical files. The
inverse round trip proves the same property with real content: the tool's write path is lossless
and its toggle is involutive.

Additional parity check — structural, not value-based:
```
seb_toggle.py --diff /tmp/c2.seb "config (2).seb"
```
Assert: exactly one differing key, `startURL`. This confirms the write path preserves every
non-`startURL` key identically to the hand-authored file.

### 9.2 Acceptance

All five pass → tool is correct on the reference corpus.

---

## 10. Honesty — stated limits

These go in the tool's `--help` and in every report footer, not just in this document.

1. **69 of 191 keys in these samples are ignored by SEB 3.10.2.** They are macOS / SEB-2.x keys.
   68 of 69 confirmed by literal presence in the macOS source tree. Toggling them has no effect
   on Windows 3.10.2. The tool reports them and refuses to toggle them.
2. **No integrity hash is stored in the `.seb`.** `ComputeBrowserExamKey(configurationKey, salt)`
   is `HMACSHA256(salt)` over `CodeSignatureHash + ProgramBuildVersion + configurationKey`,
   computed locally at runtime; `IntegrityModule.TryCalculateBrowserExamKey` shells to
   `seb_x64.dll`. Edits are self-consistent for local-config files.
   **Caveat: this holds only when `sebServerURL == ''`.** All three samples satisfy this
   (all have `browserExamKey = ''`, `sendBrowserExamKey = True`), but a config bound to a real
   exam server will fail key verification after edit. The tool detects `sebServerURL != ''` and
   says so before writing.
3. **Binary-container inputs are out of scope.** `plnd` / `pswd` / `pwcc` / `pkhs` / `phsk`
   detected and refused.
4. **Encrypted configs (`useAsymmetricOnlyEncryption = True`) are out of scope.** Detected and
   refused before the toggle phase.
5. **The registry is version-pinned.** It is generated from `seb3.10.2_decompiled`. Against a
   different SEB build, re-run `build_registry.py` against that build's source.
6. **`proxies` has two shapes in the wild** — `{AutoConfigurationEnabled, ...}` in
   `config (1)/(2)`, `{ExceptionsList, ExcludeSimpleHostnames, AutoDiscoveryEnabled, ...}` in
   `SebClientSettings.seb`. The tool treats it as opaque and does not offer it as a toggle.
7. **Key counts are not fixed** — 191 vs 206 across samples. No fixed key set is assumed anywhere.

---

## 11. Reproduce every number in this plan

**Registry + coverage:**
```bash
cd D:/Downloads_Sorted_Codex/Folders/SEB/research/seb3.10.2_decompiled
python - <<'EOF'
import re,glob,plistlib
base='SafeExamBrowser.Configuration/SafeExamBrowser.Configuration.ConfigurationData'
t=open(base+'/Keys.cs',encoding='utf-8-sig').read()
stack=[];reg={}
for line in t.splitlines():
    m=re.match(r'\s*(?:internal|public|private)?\s*static class (\w+)',line)
    if m: stack.append(m.group(1)); continue
    m=re.match(r'\s*internal const string \w+ = "([^"]+)"',line)
    if m: reg[m.group(1)]='.'.join(stack); continue
    if re.match(r'^\t*\}$',line) and stack: stack.pop()
cfg=set(plistlib.load(open(r'C:/Users/Hariz/Downloads/config (1).seb','rb')))
print('consts: %d | config: %d | recognized: %d | ignored: %d'%(
      len(reg),len(cfg),len(cfg&set(reg)),len(cfg-set(reg))))
EOF
```
Observed: `consts: 217 | config: 191 | recognized: 122 | ignored: 69`

**Dispatch + inversions:** parse `private void (Map\w+)\(AppSettings settings, object value\)`
bodies in `ConfigurationData/DataMapping/*.cs`; cross-reference `key == "(\w+)"` followed within
220 chars by `(Map\w+)\(settings`. Observed: 140 methods, 142 dispatch edges, 16 inverted.

**Ignored-key attribution:** collect all string literals from `research/seb-mac-src`; check
membership of the 69. Observed: 68 of 69 present.

**Regression pair:** as in §9.1 Test A/B/C. Observed raw diff: 1 key, `startURL`.

---

## 12. Build order

1. `build_registry.py` → `seb_registry.json`. Verify 217 keys, 142 dispatch, 16 inverted, 149 defaults.
2. `seb_toggle.py --scan`. Verify the 122/69 split reproduces on all three samples.
3. Format detection and the two refusal paths (§3.1, §3.2).
4. Toggle + write + the five self-verification assertions (§7).
5. Run Test A–E (§9.1). All must pass.
