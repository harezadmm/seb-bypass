#!/usr/bin/env python3
"""seb_gui.py - desktop UI for the SEB config toggle.

The engine is seb_toggle.py. This file adds no scanning, toggling or writing logic of
its own; it calls the same functions the CLI calls, so the two can never drift.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    sys.stderr.write(
        "Tkinter tidak tersedia di Python ini.\n"
        "  Debian/Ubuntu : sudo apt install python3-tk\n"
        "  Fedora        : sudo dnf install python3-tkinter\n"
        "  macOS/Windows : pakai Python resmi dari python.org\n"
        "Sementara itu CLI tetap jalan: python seb_toggle.py --help\n")
    raise SystemExit(2)

import seb_toggle as engine

VOID = ("", "", "", "", "", "")


class Model:
    """All state and behaviour, no widgets. Testable without a display."""

    def __init__(self):
        self.reg = engine.Registry(engine.REGISTRY_PATH)
        self.path = None
        self.data = {}
        self.size = 0
        self.rows = []
        self.absent = []
        self.encrypted = False
        self.intended = {}
        self.entries = []

    def load(self, path):
        data, size = engine.detect_and_load(path)
        self.path = str(path)
        self.data = data
        self.size = size
        self.rows, self.absent = engine.scan(data, self.reg)
        self.encrypted = engine.check_encryption(data)
        self.intended = {}
        self.entries = [r for r in self.rows
                        if r["known"] and isinstance(r["raw"], bool)]
        return self

    def counts(self):
        return engine.counts(self.rows, self.absent)

    def restricting(self):
        return [r for r in self.entries if r["raw"] is False]

    def new_value(self, key):
        return self.intended.get(key, "")

    def toggle(self, key):
        for r in self.entries:
            if r["key"] == key:
                if key in self.intended:
                    del self.intended[key]
                else:
                    self.intended[key] = not r["raw"]
                return True
        return False

    def select_restricting(self):
        n = 0
        for r in self.restricting():
            self.intended[r["key"]] = True
            n += 1
        return n

    def clear(self):
        n = len(self.intended)
        self.intended = {}
        return n

    def unlock_all(self):
        self.intended.update(engine.build_unlock(self.data))
        return len(self.intended)

    def default_out(self):
        p = Path(self.path)
        return str(p.with_name(p.stem + ".modified.seb"))

    def write(self, out_path, add_missing=False):
        src = dict(self.data)
        out, _added = engine.write_output(self.data, self.intended, self.path,
                                          out_path, add_missing, self.reg)
        ok, errors, stats = engine.verify(src, self.path, out, self.intended, add_missing)
        if not ok:
            try:
                Path(out).unlink()
            except OSError:
                pass
        return ok, errors, stats


def _theme(root):
    st = ttk.Style(root)
    for name in ("vista", "winnative", "clam", "default"):
        if name in st.theme_names():
            st.theme_use(name)
            break
    st.configure("Head.TLabel", font=("Segoe UI", 13, "bold"))
    st.configure("Sub.TLabel", foreground="#555")
    st.configure("Chip.TLabel", padding=(8, 3))
    st.configure("Go.TButton", font=("Segoe UI", 10, "bold"))
    return st


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SEB Config Toggle")
        self.geometry("1080x760")
        self.minsize(900, 620)
        self.model = Model()
        self.out_path = tk.StringVar()
        self.query = tk.StringVar()
        self.only_blocking = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Pilih file .seb untuk mulai.")
        self._build()
        self.refresh_tree()

    # ---------------------------------------------------------------- layout
    def _build(self):
        _theme(self)
        pad = dict(padx=10, pady=6)

        head = ttk.Frame(self)
        head.pack(fill="x", **pad)
        ttk.Label(head, text="SEB Config Toggle", style="Head.TLabel").pack(anchor="w")
        ttk.Label(head, text="Buka batasan Safe Exam Browser, lalu tulis ke file baru. "
                             "Input tidak pernah diubah.",
                  style="Sub.TLabel").pack(anchor="w")

        pick = ttk.Frame(self)
        pick.pack(fill="x", **pad)
        ttk.Label(pick, text="File").pack(side="left")
        self.file_var = tk.StringVar()
        ttk.Entry(pick, textvariable=self.file_var).pack(side="left", fill="x",
                                                         expand=True, padx=6)
        ttk.Button(pick, text="Pilih…", command=self.on_pick).pack(side="left")
        ttk.Button(pick, text="Muat", command=self.on_load).pack(side="left", padx=(6, 0))

        self.info = ttk.Frame(self)
        self.info.pack(fill="x", **pad)
        self.lbl_meta = ttk.Label(self.info, style="Sub.TLabel")
        self.lbl_meta.pack(anchor="w")
        self.chips = ttk.Frame(self.info)
        self.chips.pack(anchor="w", pady=(4, 0))

        bar = ttk.Frame(self)
        bar.pack(fill="x", **pad)
        self.btn_unlock = ttk.Button(bar, text="Buka Semua Batasan",
                                     style="Go.TButton", command=self.on_unlock)
        self.btn_unlock.pack(side="left")
        ttk.Button(bar, text="Pilih yang memblokir",
                   command=self.on_select_blocking).pack(side="left", padx=6)
        ttk.Button(bar, text="Kosongkan", command=self.on_clear).pack(side="left")
        ttk.Checkbutton(bar, text="Hanya yang memblokir", variable=self.only_blocking,
                        command=self.refresh_tree).pack(side="left", padx=(18, 0))
        ttk.Label(bar, text="Cari").pack(side="left", padx=(18, 4))
        e = ttk.Entry(bar, textvariable=self.query, width=22)
        e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self.refresh_tree())

        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, **pad)
        cols = ("pick", "status", "key", "now", "after", "prop")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", selectmode="browse")
        for c, t, w in (("pick", "", 34), ("status", "STATUS", 190), ("key", "KEY", 260),
                        ("now", "NILAI SEKARANG", 110), ("after", "JADI", 90),
                        ("prop", "PROPERTY", 300)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, stretch=(c in ("key", "prop")))
        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="left", fill="y")
        self.tree.tag_configure("cat", background="#eef2f7", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("blocking", foreground="#b00020")
        self.tree.tag_configure("open", foreground="#1b5e20")
        self.tree.tag_configure("picked", background="#fff4d6")
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<Double-1>", self.on_double)
        self.tree.bind("<space>", self.on_space)

        prev = ttk.LabelFrame(self, text="Perubahan yang akan ditulis")
        prev.pack(fill="both", expand=False, **pad)
        self.preview = tk.Text(prev, height=8, wrap="none", font=("Consolas", 9))
        self.preview.configure(state="disabled", background="#fbfbfb")
        self.preview.pack(fill="both", expand=True, padx=6, pady=6)

        foot = ttk.Frame(self)
        foot.pack(fill="x", **pad)
        ttk.Label(foot, text="Output").pack(side="left")
        self.out_var = tk.StringVar()
        ttk.Entry(foot, textvariable=self.out_var).pack(side="left", fill="x",
                                                        expand=True, padx=6)
        ttk.Button(foot, text="Pilih…", command=self.on_pick_out).pack(side="left")
        self.btn_write = ttk.Button(foot, text="TULIS FILE", style="Go.TButton",
                                    command=self.on_write)
        self.btn_write.pack(side="left", padx=(6, 0))

        ttk.Separator(self).pack(fill="x")
        ttk.Label(self, textvariable=self.status, style="Sub.TLabel").pack(
            anchor="w", padx=10, pady=5)

    # ---------------------------------------------------------------- helpers
    def _set_status(self, text):
        self.status.set(text)

    def _warn(self, text):
        messagebox.showwarning("SEB Config Toggle", text)

    def _err(self, text):
        messagebox.showerror("SEB Config Toggle", text)

    def _set_preview(self, lines):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", "\n".join(lines) if lines else "(belum ada perubahan)")
        self.preview.configure(state="disabled")

    def _chips(self):
        for w in self.chips.winfo_children():
            w.destroy()
        c = self.model.counts()
        blocking = (c["RESTRICTION"] + c["RESTRICTION SEB default"]
                    + c["RESTRICTION author-imposed"])
        items = [("memblokir", blocking, "#b00020"),
                 ("mengizinkan", c["PERMISSIVE"], "#1b5e20"),
                 ("mode", c["MODE-SELECTOR"], "#0d47a1"),
                 ("diabaikan", c["IGNORED-BY-3.10.2"], "#616161"),
                 ("absen", c["ABSENT-DEFAULTED"], "#616161")]
        for label, n, colour in items:
            lb = tk.Label(self.chips, text="%s %d" % (label, n), bg=colour, fg="white",
                          padx=8, pady=2, font=("Segoe UI", 9))
            lb.pack(side="left", padx=(0, 6))

    # ---------------------------------------------------------------- actions
    def on_pick(self):
        p = filedialog.askopenfilename(title="Pilih config .seb",
                                       filetypes=[("SEB config", "*.seb"), ("Semua file", "*.*")])
        if p:
            self.file_var.set(p)
            self.on_load()

    def on_load(self):
        p = self.file_var.get().strip().strip('"')
        if not p:
            self._warn("Pilih file .seb dulu.")
            return
        try:
            self.model.load(p)
        except engine.Refused as exc:
            self._err("Ditolak: %s" % exc)
            self._set_status("Ditolak: %s" % exc)
            return
        except FileNotFoundError:
            self._err("File tidak ditemukan:\n%s" % p)
            return
        except Exception as exc:
            self._err("%s: %s" % (type(exc).__name__, exc))
            return

        m = self.model
        self.out_var.set(m.default_out())
        meta = "originatorVersion %s   ·   %s   ·   %d key   ·   %d kategori registry" % (
            m.data.get("originatorVersion", "(absen)"), _bytes(m.size), len(m.rows),
            len(m.reg.categories))
        self.lbl_meta.configure(text=meta)
        self._chips()
        self.refresh_tree()
        self._set_preview([])
        if m.encrypted:
            self.btn_write.state(["disabled"])
            self._warn("Config ini mendeklarasikan enkripsi (%s = True).\n\n"
                       "Menulis file baru tidak akan berpengaruh di klien SEB, jadi tombol "
                       "TULIS dimatikan." % engine.ENCRYPTION_KEY)
            self._set_status("Config terenkripsi — penulisan dimatikan.")
        else:
            self.btn_write.state(["!disabled"])
            self._set_status("%d key dimuat. %d di antaranya bisa di-toggle."
                             % (len(m.rows), len(m.entries)))

    def on_unlock(self):
        if not self.model.rows:
            self._warn("Muat file dulu.")
            return
        n = self.model.unlock_all()
        self.refresh_tree()
        self._set_status("Profil relaksasi: %d key akan diubah." % n
                         if n else "Tidak ada yang perlu dibuka — config sudah terbuka.")

    def on_select_blocking(self):
        if not self.model.rows:
            self._warn("Muat file dulu.")
            return
        n = self.model.select_restricting()
        self.refresh_tree()
        self._set_status("%d key yang memblokir dipilih." % n)

    def on_clear(self):
        n = self.model.clear()
        self.refresh_tree()
        self._set_status("%d pilihan dibatalkan." % n)

    def on_pick_out(self):
        p = filedialog.asksaveasfilename(title="Simpan config baru", defaultextension=".seb",
                                         initialfile=Path(self.model.default_out()).name,
                                         filetypes=[("SEB config", "*.seb")])
        if p:
            self.out_var.set(p)

    def on_write(self):
        if not self.model.rows:
            self._warn("Muat file dulu.")
            return
        if self.model.encrypted:
            self._warn("Config terenkripsi — penulisan dimatikan.")
            return
        if not self.model.intended:
            if not messagebox.askyesno("SEB Config Toggle",
                                       "Belum ada perubahan dipilih.\n\n"
                                       "Tulis salinan identik (uji tulis)?"):
                return
        out = self.out_var.get().strip().strip('"') or self.model.default_out()
        if Path(out).resolve() == Path(self.model.path).resolve():
            self._err("Menolak menulis ke file input. Pilih nama lain.")
            return
        if Path(out).exists() and not messagebox.askyesno(
                "SEB Config Toggle", "File tujuan sudah ada:\n%s\n\nTimpa?" % out):
            return
        try:
            ok, errors, stats = self.model.write(out)
        except Exception as exc:
            self._err("%s: %s" % (type(exc).__name__, exc))
            return
        if ok:
            self._set_status("Tersimpan: %s  ·  %d -> %d key  ·  %d -> %d byte"
                             % (out, stats["src_keys"], stats["out_keys"],
                                stats["src_bytes"], stats["out_bytes"]))
            messagebox.showinfo("SEB Config Toggle",
                                "Berhasil ditulis dan diverifikasi.\n\n%s\n\n"
                                "key %d -> %d\nbyte %d -> %d\n\n5 assertion lulus."
                                % (out, stats["src_keys"], stats["out_keys"],
                                   stats["src_bytes"], stats["out_bytes"]))
        else:
            self._err("Verifikasi gagal — file output dihapus.\n\n" + "\n".join(errors))
            self._set_status("Verifikasi gagal, output dihapus.")

    # ---------------------------------------------------------------- tree
    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.model.rows:
            self.update_preview()
            return
        q = self.query.get().strip().lower()
        only = self.only_blocking.get()
        by_cat = {}
        for r in self.model.rows:
            if not (r["known"] and isinstance(r["raw"], bool)):
                continue
            if only and r["raw"] is not False:
                continue
            if q and q not in r["key"].lower() and q not in (r["prop"] or "").lower():
                continue
            by_cat.setdefault(r["category"], []).append(r)
        for cat in sorted(by_cat):
            self.tree.insert("", "end", text=cat, values=VOID, tags=("cat",), open=True)
            for r in by_cat[cat]:
                self.tree.insert("", "end", iid=r["key"], values=self._row_values(r),
                                 tags=self._row_tags(r))
        self.update_preview()

    def _row_values(self, r):
        after = self.model.intended.get(r["key"], "")
        return ("✓" if r["key"] in self.model.intended else "",
                r["status"], r["key"], engine.fmt_raw(r["raw"]),
                str(after) if after != "" else "", r["prop"] or "(unmapped)")

    def _row_tags(self, r):
        tags = ["blocking" if r["raw"] is False else "open"]
        if r["key"] in self.model.intended:
            tags.append("picked")
        return tuple(tags)

    def _refresh_row(self, key):
        for r in self.model.entries:
            if r["key"] == key:
                self.tree.item(key, values=self._row_values(r), tags=self._row_tags(r))
                return

    def on_click(self, ev):
        row = self.tree.identify_row(ev.y)
        if not row or row not in self.tree.get_children(""):
            return
        col = self.tree.identify_column(ev.x)
        if col == "#1":
            self._toggle(row)

    def on_double(self, ev):
        row = self.tree.identify_row(ev.y)
        if row:
            self._toggle(row)

    def on_space(self, _ev):
        sel = self.tree.selection()
        if sel:
            self._toggle(sel[0])

    def _toggle(self, key):
        if not self.model.toggle(key):
            return
        self._refresh_row(key)
        self.update_preview()
        n = len(self.model.intended)
        self._set_status("%d key akan diubah." % n if n else "Tidak ada perubahan dipilih.")

    def update_preview(self):
        lines = []
        for k, v in sorted(self.model.intended.items()):
            if k in self.model.data:
                lines.append("%-38s %s -> %s" % (k, engine.fmt_raw(self.model.data[k]),
                                                 engine.fmt_raw(v)))
            else:
                lines.append("%-38s (absen) -> %s        [ADDITION]"
                             % (k, engine.fmt_raw(v)))
        self._set_preview(lines)


def _bytes(n):
    if n < 1024:
        return "%d B" % n
    if n < 1048576:
        return "%.1f KB" % (n / 1024.0)
    return "%.1f MB" % (n / 1048576.0)


def _selftest(cfg, report):
    """Drive the real widgets headlessly-ish so a frozen build can be verified."""
    import tempfile, traceback

    def _no_dialog(name):
        def _raise(*_a, **_k):
            raise RuntimeError("modal dialog attempted during selftest: %s" % name)
        return _raise

    for _fn in ("showwarning", "showerror", "showinfo", "askyesno"):
        setattr(messagebox, _fn, _no_dialog(_fn))
    try:
        app = App()
        app.file_var.set(cfg)
        app.on_load()
        app.update()
        rows = len([r for r in app.tree.get_children("") if not app.tree.item(r, "text")])
        app.on_unlock()
        app.update()
        ticked = len([r for r in app.tree.get_children("") if app.tree.set(r, "pick") == "\u2713"])
        out = Path(tempfile.mkdtemp()) / "selftest.seb"
        ok, errors, _stats = app.model.write(str(out))
        written = out.exists() and ok
        app.destroy()
        lines = ["rows=%d" % rows, "ticked=%d" % ticked, "written=%s" % written,
                 "errors=%s" % ("; ".join(errors) if errors else "none")]
        code = 0 if (rows == 85 and written) else 1
    except Exception:
        lines = ["FAILED", traceback.format_exc()]
        code = 1
    text = "\n".join(lines)
    if report:
        Path(report).write_text(text, encoding="utf-8")
    else:
        sys.stderr.write(text + "\n")
    return code


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        return _selftest(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    app = App()
    if len(sys.argv) > 1:
        app.file_var.set(sys.argv[1])
        app.on_load()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
