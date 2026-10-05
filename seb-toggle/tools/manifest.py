#!/usr/bin/env python3
"""Emit a portable manifest of a directory tree: D dir, F file+size, L symlink+target."""
import os
import sys

base = sys.argv[1]
rows = []
for root, dirs, files in os.walk(base):
    for n in list(dirs) + list(files):
        p = os.path.join(root, n)
        rel = os.path.relpath(p, base).replace(os.sep, "/")
        try:
            if os.path.islink(p):
                rows.append("L %s -> %s" % (rel, os.readlink(p).replace("\\", "/")))
            elif os.path.isdir(p):
                rows.append("D %s" % rel)
            else:
                rows.append("F %s %d" % (rel, os.path.getsize(p)))
        except OSError as exc:
            rows.append("? %s %s" % (rel, exc))
print("\n".join(sorted(rows)))
