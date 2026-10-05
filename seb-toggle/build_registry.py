#!/usr/bin/env python3
"""Generate seb_registry.json from a decompiled SafeExamBrowser tree.

Registry = Keys.cs constants (nested-class aware) + DataMapping/*.cs key->method
dispatch + method bodies (property/expression/inversion) + DataValues.LoadDefaultSettings.

Usage:
    build_registry.py <decompiled-root> [-o seb_registry.json]

<decompiled-root> is the directory containing
    SafeExamBrowser.Configuration/SafeExamBrowser.Configuration.ConfigurationData/
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

CFG_REL = "SafeExamBrowser.Configuration/SafeExamBrowser.Configuration.ConfigurationData"


def resolve_mapping_dir(cfg):
    """Locate the DataMapping directory.

    On disk (decompiled layout) it is a SIBLING of the ConfigurationData directory,
    named `...ConfigurationData.DataMapping`, not a child. Accept either.
    """
    child = cfg / "DataMapping"
    if child.is_dir():
        return child
    parent = cfg.parent
    for cand in sorted(parent.glob("*.DataMapping")):
        if cand.is_dir() and any(cand.glob("*.cs")):
            return cand
    raise SystemExit(f"DataMapping directory not found under {parent}")


def parse_keys_cs(path):
    """Return ({key: category}, {category: [keys]}, collisions).

    Class names are attached to the brace that actually opens the body (char-scanned, with
    string literals masked), so `class X { ... }` on one line, multi-line declarations, and
    several braces per line all nest correctly.

    collisions: {wire_value: [const_name, ...]} for wire values declared more than once.
    Keys.cs declares two values twice under differing constant names, which is exactly why
    a key name cannot be assumed to identify the settings property it feeds.
    """
    text = path.read_text(encoding="utf-8-sig")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)

    stack, pending = [], []
    keys, cats, decls = {}, {}, []
    depth = 0
    for line in text.split("\n"):
        skel = re.sub(r'"[^"]*"', '""', line)  # mask literals so their braces cannot count
        m = re.search(r"\bclass\s+(\w+)", skel)
        if m:
            pending.append(m.group(1))
        for ch in skel:
            if ch == "{":
                depth += 1
                if pending:
                    stack.append((depth, pending.pop(0)))
            elif ch == "}":
                if stack and stack[-1][0] == depth:
                    stack.pop()
                depth -= 1
        m = re.search(r'internal const string (\w+) = "([^"]+)"', line)
        if m:
            const, wire = m.group(1), m.group(2)
            cat = ".".join(name for _, name in stack)
            keys.setdefault(wire, cat)
            cats.setdefault(cat, []).append(wire)
            decls.append((const, wire))

    seen = {}
    for const, wire in decls:
        seen.setdefault(wire, []).append(const)
    collisions = {w: cs for w, cs in seen.items() if len(cs) > 1}
    return keys, cats, collisions


def parse_methods(mapping_dir):
    """Return (methods, dispatch).

    methods:  {MapMethod: {file, prop, expr, inverted}}
    dispatch: {key: MapMethod}  -- from `key == "x"` followed within 220 chars by `Map*(settings`
    """
    methods, dispatch = {}, {}
    for f in sorted(mapping_dir.glob("*.cs")):
        src = f.read_text(encoding="utf-8-sig", errors="replace")
        for m in re.finditer(
            r"private void (Map\w+)\(AppSettings settings, object value\)\s*\{(.*?)\n\t\}",
            src, re.S,
        ):
            name, body = m.group(1), m.group(2)
            a = re.search(r"settings\.([A-Za-z0-9_.]+)\s*=\s*([^;]{1,90});", body)
            if not a:
                continue
            expr = a.group(2).strip()
            methods[name] = {
                "file": f.stem,
                "prop": a.group(1),
                "expr": expr[:70],
                "inverted": "!" in expr,
            }
        for km in re.finditer(r'key == "([A-Za-z0-9_]+)"', src):
            tail = src[km.end():km.end() + 220]
            c = re.search(r"(Map\w+)\(settings", tail)
            if c:
                dispatch[km.group(1)] = c.group(1)
    return methods, dispatch


def parse_globals(mapping_dir):
    """Return {MapperClass: [keys read via TryGetValue in MapGlobal]}."""
    out = {}
    for f in sorted(mapping_dir.glob("*.cs")):
        src = f.read_text(encoding="utf-8-sig", errors="replace")
        for m in re.finditer(
            r"internal override void MapGlobal\(IDictionary<string, object> rawData, AppSettings settings\)\s*\{(.*?)\n\t\}",
            src, re.S,
        ):
            out[f.stem] = re.findall(r'TryGetValue\("([^"]+)"', m.group(1))
    return out


def parse_defaults(data_values_cs):
    """Return {AppSettings.Property: literal} from DataValues.LoadDefaultSettings()."""
    text = data_values_cs.read_text(encoding="utf-8-sig")
    start = text.index("return new AppSettings", text.index("LoadDefaultSettings"))
    j = text.index("{", start)
    depth, k = 0, j
    while True:
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    body = text[j + 1:k]

    stack, defaults = [], {}
    for line in body.split("\n"):
        t = line.strip()
        if not t:
            continue
        # nested object: `Foo =` or `Foo = {`
        if re.fullmatch(r"[A-Za-z0-9_]+\s*=\s*\{?", t):
            stack.append(t.split("=")[0].strip())
            continue
        m = re.fullmatch(r"([A-Za-z0-9_]+)\s*=\s*(.+?),?;?", t)
        if m:
            name, val = m.group(1), m.group(2).rstrip(",;")
            if val.startswith("new "):
                continue
            defaults.setdefault(".".join(stack + [name]), val)
            continue
        if re.fullmatch(r"\},?\s*;?", t) and stack:
            stack.pop()
    return defaults


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="decompiled SEB root")
    ap.add_argument("-o", "--out", default="seb_registry.json")
    args = ap.parse_args()

    root = Path(args.root)
    cfg = root / CFG_REL
    if not cfg.is_dir():
        sys.exit(f"not a decompiled SEB tree: {cfg} missing")

    keys, cats, collisions = parse_keys_cs(cfg / "Keys.cs")
    mapping = resolve_mapping_dir(cfg)
    methods, dispatch = parse_methods(mapping)
    globals_ = parse_globals(mapping)
    defaults = parse_defaults(cfg / "DataValues.cs")

    reg = {
        "source": str(root),
        "keys": keys,
        "categories": cats,
        "const_collisions": collisions,
        "dispatch": dispatch,
        "methods": methods,
        "global_handlers": globals_,
        "defaults": defaults,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    Path(args.out).write_text(json.dumps(reg, indent=1), encoding="utf-8")

    inverted = [k for k, v in methods.items() if v["inverted"]]
    outside = sorted(set(dispatch) - set(keys))
    print(f"keys.cs constants : {len(keys)} across {len(cats)} categories")
    print(f"mapper methods    : {len(methods)}")
    print(f"dispatch edges    : {len(dispatch)}")
    print(f"inverted methods  : {len(inverted)}")
    print(f"defaults leaves   : {len(defaults)}")
    print(f"dispatch key not in Keys.cs : {outside if outside else 'none'}")
    print(f"global handlers   : { {k: len(v) for k, v in globals_.items()} }")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
