"""
ORSPEX PDF Compressor
Compresses PDF files using Ghostscript.
"""

import os
import sys
import subprocess
import threading
import configparser
import tkinter as tk
from tkinter import filedialog, ttk, messagebox

# NEW: optional image support for logo (Pillow)
try:
    from PIL import Image, ImageTk
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

APP_NAME     = "ORSPEX PDF Compressor"
APP_VERSION  = "1.1.0"
APP_AUTHOR   = "ORSPEX"

# NEW: paths to icon + logo (change if your files live elsewhere)
APP_DIR  = os.path.dirname(os.path.abspath(__file__))

def _asset(name):
    """Find asset next to script, in assets/, or in a PyInstaller bundle."""
    candidates = [
        os.path.join(APP_DIR, name),
        os.path.join(APP_DIR, "assets", name),
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(0, os.path.join(meipass, name))
        candidates.insert(0, os.path.join(meipass, "assets", name))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return candidates[0]

ICON_PATH = _asset("orspex.ico")
LOGO_PATH = _asset("orspex.png")
DISCLAIMER = (
    f"{APP_NAME} v{APP_VERSION}\n\n"
    "Provided \"as is\", without warranty of any kind, express or implied, "
    "including but not limited to the warranties of merchantability, fitness "
    "for a particular purpose, and non-infringement.\n\n"
    "In no event shall the authors or copyright holders be liable for any "
    "claim, damages, or other liability, whether in an action of contract, "
    "tort, or otherwise, arising from, out of, or in connection with the "
    "software or the use or other dealings in the software.\n\n"
    "This tool calls Ghostscript (© Artifex Software) which must be installed "
    "separately. Always keep a backup of your original files. ORSPEX does not "
    "upload, transmit, or retain any of your documents — all processing is "
    "performed locally on this computer."
)

# ---------- settings ----------
CFG_DIR  = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "ORSPEX")
CFG_FILE = os.path.join(CFG_DIR, "pdf_compressor.ini")

def load_cfg():
    c = configparser.ConfigParser()
    if os.path.isfile(CFG_FILE):
        c.read(CFG_FILE)
    return c

def save_cfg(c):
    os.makedirs(CFG_DIR, exist_ok=True)
    with open(CFG_FILE, "w") as f:
        c.write(f)

# ---------- Ghostscript ----------
def find_gs():
    candidates = [
        r"C:\Program Files\gs\gs10.08.0\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs10.07.0\bin\gswin64c.exe",
        r"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe",
        r"C:\Program Files (x86)\gs\gs10.08.0\bin\gswin32c.exe",
    ]
    import shutil
    p = shutil.which("gswin64c") or shutil.which("gswin32c") or shutil.which("gs")
    if p:
        candidates.insert(0, p)
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None

GS = find_gs()

PRESETS = {
    "High (300 dpi, Q=85)":    dict(dpi=300, q=85),
    "Medium (150 dpi, Q=70)":  dict(dpi=150, q=70),
    "Low (100 dpi, Q=50)":     dict(dpi=100, q=50),
    "Tiny (72 dpi, Q=40)":     dict(dpi=72,  q=40),
}

def build_cmd(src, dst, dpi, q):
    return [
        GS, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5",
        "-dNOPAUSE", "-dBATCH",
        "-dDownsampleColorImages=true", f"-dColorImageResolution={dpi}",
        "-dColorImageDownsampleType=/Bicubic",
        "-dDownsampleGrayImages=true",  f"-dGrayImageResolution={dpi}",
        "-dGrayImageDownsampleType=/Bicubic",
        "-dDownsampleMonoImages=true",  "-dMonoImageResolution=300",
        "-dAutoFilterColorImages=false", "-dColorImageFilter=/DCTEncode",
        "-dAutoFilterGrayImages=false",  "-dGrayImageFilter=/DCTEncode",
        f"-dJPEGQ={q}",
        "-dEmbedAllFonts=false", "-dSubsetFonts=true", "-dCompressFonts=true",
        "-dDetectDuplicateImages=true",
        f"-sOutputFile={dst}", src,
    ]

def compress(src, dst, dpi, q, log_fn):
    cmd = build_cmd(src, dst, dpi, q)
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
    if proc.returncode != 0:
        log_fn(proc.stderr or proc.stdout)
        return False
    return True

# ---------- About window ----------
def show_about(parent):
    w = tk.Toplevel(parent)
    w.title(f"About {APP_NAME}")
    w.geometry("480x360")
    w.resizable(False, False)
    w.transient(parent)
    w.grab_set()
    set_window_icon(w)

    tk.Label(w, text="ORSPEX", font=("Segoe UI", 22, "bold")).pack(pady=(20, 0))
    tk.Label(w, text=APP_NAME, font=("Segoe UI", 11)).pack()
    tk.Label(w, text=f"Version {APP_VERSION}", foreground="#666").pack(pady=(2, 14))

    txt = tk.Text(w, wrap="word", height=12, relief="flat", background=w.cget("bg"))
    txt.pack(fill="both", expand=True, padx=16, pady=(0, 10))
    txt.insert("1.0", DISCLAIMER)
    txt.config(state="disabled")

    ttk.Button(w, text="Close", command=w.destroy).pack(pady=(0, 14))

# ---------- window icon helper ----------
def set_window_icon(window):
    # NEW: apply .ico to any Tk window if it exists
    if os.path.isfile(ICON_PATH):
        try:
            window.iconbitmap(ICON_PATH)
        except Exception:
            pass

# ---------- Main app ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("640x580")
        self.minsize(560, 520)
        set_window_icon(self)   # NEW

        self.src = tk.StringVar()
        self.dst = tk.StringVar()
        self.preset = tk.StringVar(value="Medium (150 dpi, Q=70)")
        self.target_mb = tk.StringVar(value="")

        self._logo_img = None   # NEW: keep a reference so Tk doesn't GC it

        self.cfg = load_cfg()
        self._build_ui()
        self._build_menu()

        if not GS:
            messagebox.showerror(
                f"{APP_NAME} — Missing dependency",
                "Ghostscript was not found on this computer.\n\n"
                "Please install Ghostscript from https://ghostscript.com/releases/"
            )

        if not self.cfg.getboolean("ui", "disclaimer_accepted", fallback=False):
            self.after(200, self._show_disclaimer)

    def _build_menu(self):
        m = tk.Menu(self)
        helpm = tk.Menu(m, tearoff=0)
        helpm.add_command(label=f"About {APP_NAME}", command=lambda: show_about(self))
        m.add_cascade(label="Help", menu=helpm)
        self.config(menu=m)

    def _show_disclaimer(self):
        dlg = tk.Toplevel(self)
        dlg.title("Disclaimer — please read")
        dlg.geometry("520x420")
        dlg.transient(self)
        dlg.grab_set()
        set_window_icon(dlg)

        tk.Label(dlg, text="ORSPEX", font=("Segoe UI", 18, "bold")).pack(pady=(16, 0))
        tk.Label(dlg, text="Before you use this tool", font=("Segoe UI", 10)).pack(pady=(0, 10))

        txt = tk.Text(dlg, wrap="word", height=15, relief="flat")
        txt.pack(fill="both", expand=True, padx=16)
        txt.insert("1.0", DISCLAIMER)
        txt.config(state="disabled")

        dont = tk.BooleanVar(value=False)
        tk.Checkbutton(dlg, text="Don't show this again", variable=dont).pack(pady=8)

        def accept():
            if dont.get():
                if not self.cfg.has_section("ui"):
                    self.cfg.add_section("ui")
                self.cfg.set("ui", "disclaimer_accepted", "true")
                save_cfg(self.cfg)
            dlg.destroy()

        ttk.Button(dlg, text="I understand", command=accept).pack(pady=(0, 14))
        dlg.protocol("WM_DELETE_WINDOW", accept)

    def _build_ui(self):
        pad = dict(padx=10, pady=4)

        # NEW: header with optional logo image
        header = tk.Frame(self, bg="#1e3a5f", height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        if HAVE_PIL and os.path.isfile(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH).convert("RGBA")
                img.thumbnail((48, 48), Image.LANCZOS)
                self._logo_img = ImageTk.PhotoImage(img)
                tk.Label(header, image=self._logo_img,
                         bg="#1e3a5f").pack(side="left", padx=(14, 8))
            except Exception:
                self._logo_img = None

        # If no logo image, show a placeholder rounded "O" mark
        if self._logo_img is None:
            tk.Label(header, text="O", bg="#f0a500", fg="#1e3a5f",
                     font=("Segoe UI", 22, "bold"), width=2, height=1
                     ).pack(side="left", padx=(14, 8), pady=8)

        tk.Label(header, text="ORSPEX", bg="#1e3a5f", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=(0, 6))
        tk.Label(header, text="PDF Compressor", bg="#1e3a5f", fg="#b8c9dd",
                 font=("Segoe UI", 16)).pack(side="left")

        ttk.Label(self, text="Source PDF:").pack(anchor="w", **pad)
        f1 = ttk.Frame(self); f1.pack(fill="x", padx=10)
        ttk.Entry(f1, textvariable=self.src).pack(side="left", fill="x", expand=True)
        ttk.Button(f1, text="Browse…", command=self.pick_src).pack(side="left", padx=(6,0))

        ttk.Label(self, text="Output PDF:").pack(anchor="w", **pad)
        f2 = ttk.Frame(self); f2.pack(fill="x", padx=10)
        ttk.Entry(f2, textvariable=self.dst).pack(side="left", fill="x", expand=True)
        ttk.Button(f2, text="Save as…", command=self.pick_dst).pack(side="left", padx=(6,0))

        ttk.Label(self, text="Quality preset:").pack(anchor="w", **pad)
        ttk.Combobox(self, textvariable=self.preset, values=list(PRESETS),
                     state="readonly").pack(fill="x", padx=10)

        ttk.Label(self, text="Target size (MB, optional):").pack(anchor="w", **pad)
        ttk.Entry(self, textvariable=self.target_mb, width=12).pack(anchor="w", padx=10)

        self.run_btn = ttk.Button(self, text="Compress", command=self.run)
        self.run_btn.pack(pady=12)

        self.status = tk.StringVar(value="Ready." if GS else "Ghostscript not found.")
        ttk.Label(self, textvariable=self.status).pack(anchor="w", padx=10)

        self.pbar = ttk.Progressbar(self, mode="indeterminate")
        self.pbar.pack(fill="x", padx=10, pady=6)

        ttk.Label(self, text="Log:").pack(anchor="w", padx=10)
        self.log = tk.Text(self, height=9, wrap="word")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        tk.Label(self, text=f"© {APP_AUTHOR} — processing is 100% local",
                 fg="#888", font=("Segoe UI", 8)).pack(pady=(0, 6))

    def pick_src(self):
        p = filedialog.askopenfilename(filetypes=[("PDF","*.pdf")])
        if p:
            self.src.set(p)
            base, _ = os.path.splitext(p)
            self.dst.set(base + "_compressed.pdf")

    def pick_dst(self):
        p = filedialog.asksaveasfilename(defaultextension=".pdf",
                                         filetypes=[("PDF","*.pdf")])
        if p:
            self.dst.set(p)

    def write_log(self, text):
        self.log.insert("end", text)
        self.log.see("end")

    def run(self):
        if not GS:
            messagebox.showerror("Ghostscript missing", "Cannot run without Ghostscript.")
            return
        s, d = self.src.get(), self.dst.get()
        if not (s and d):
            messagebox.showerror("Missing info", "Select source and output files.")
            return
        if not os.path.isfile(s):
            messagebox.showerror("Not found", f"Source not found:\n{s}")
            return

        self.run_btn.config(state="disabled")
        self.pbar.start(10)
        self.log.delete("1.0", "end")
        self.status.set("Working…")

        threading.Thread(target=self._worker, args=(s, d), daemon=True).start()

    def _worker(self, src, dst):
        try:
            target = self.target_mb.get().strip()
            target_bytes = int(float(target) * 1_000_000) if target else None

            if target_bytes:
                order = ["High (300 dpi, Q=85)",
                         "Medium (150 dpi, Q=70)",
                         "Low (100 dpi, Q=50)",
                         "Tiny (72 dpi, Q=40)"]
                for name in order:
                    self._log(f"\n--- Trying preset: {name} ---\n")
                    p = PRESETS[name]
                    ok = compress(src, dst, p["dpi"], p["q"], self._log)
                    if not ok:
                        continue
                    size = os.path.getsize(dst)
                    self._log(f"Result size: {size/1_000_000:.2f} MB\n")
                    if size <= target_bytes:
                        break
                else:
                    self._log("Could not reach target even at lowest quality.\n")
            else:
                p = PRESETS[self.preset.get()]
                self._log(f"Compressing with preset: {self.preset.get()}\n")
                ok = compress(src, dst, p["dpi"], p["q"], self._log)
                if not ok:
                    self._finish("Failed — see log.", False)
                    return

            a, b = os.path.getsize(src), os.path.getsize(dst)
            pct = 100 * (1 - b / a) if a else 0
            msg = f"Done: {a/1_000_000:.2f} MB → {b/1_000_000:.2f} MB ({pct:.0f}% smaller)"
            self._finish(msg, True)
        except Exception as e:
            self._log(f"\nError: {e}\n")
            self._finish("Error — see log.", False)

    def _log(self, text):
        self.after(0, lambda: self.write_log(text))

    def _finish(self, status_text, ok):
        def done():
            self.pbar.stop()
            self.run_btn.config(state="normal")
            self.status.set(status_text)
            if ok:
                messagebox.showinfo("Finished", status_text)
        self.after(0, done)


if __name__ == "__main__":
    App().mainloop()