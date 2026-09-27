"""
run_team7.py - Team 7: B-mode Image Formation (demo runner)

One command runs this stage and saves every result in output/:

    python3 run_team7.py        (macOS / Linux)
    python  run_team7.py        (Windows)

Place in the simulator
  Team 6 (Image Reconstruction): Hilbert envelope, normalisation, log compression (dB)
  -> Team 7 (THIS STAGE): dynamic range (clipping), grayscale brightness 0..1,
     depth/width axes, display and saving of the final grayscale B-mode image
  -> Team 8 (Post-Image Processing): despeckling of the finished image

Input
  input/reconstructed_carotid_1.npz, input/reconstructed_carotid_2.npz
  = the output of Team 6 (Image Reconstruction), copied here as input.
  Keys: rf, envelope, envelope_norm, envelope_db (dB, 0 dB = peak, not yet clipped),
        fs, f0, c, pitch, depth_start_mm.

What it does
  Part 1  Shows the input (Team 6's log-compressed envelope in dB).
  Part 2  Runs the B-mode part of code/B_mode.ipynb on carotid_1 and carotid_2:
          code cell 2 (settings, gives dynamic_range), code cell 5 from section
          "5. APPLY DYNAMIC RANGE" to its end (sections 5 and 6), code cells 6, 7, 8, 9.
          Code cells 1, 3, 4 and the first half of cell 5 (sections 1 to 4: load RF,
          Hilbert envelope, normalise, log compression) are Team 6's work; their
          results come from the input file instead.
  Part 3  Dynamic-range comparison (40 / 50 / 60 dB) made from the input envelope_db.
  Part 4  Reproducibility check: this run's output/bmode_carotid_1.npy against the image
          the notebook saved earlier (input/reference/bmode_carotid_1.npy).
  Part 5  Summary, timings, console log and console pictures.

code/B_mode.ipynb is the team's original notebook and is NOT changed.
This runner only reads it.
"""

import io
import json
import os
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True  # keep code/ clean (no __pycache__)

import matplotlib  # noqa: E402

matplotlib.use("Agg")  # save figures to files, no windows
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent
CODE = ROOT / "code"
INPUT = ROOT / "input"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)


# ----------------------------------------------------------------------
# Console: print to the screen AND keep a copy for output/console_log.txt
# ----------------------------------------------------------------------
class Tee(io.TextIOBase):
    def __init__(self, stream):
        self.stream = stream
        self.buffer_text = io.StringIO()

    def write(self, s):
        self.stream.write(s)
        self.buffer_text.write(s)
        return len(s)

    def flush(self):
        self.stream.flush()


tee = Tee(sys.stdout)
sys.stdout = tee


def banner(text):
    print()
    print("=" * 78)
    print(text)
    print("=" * 78)


def rng(a):
    return f"{float(np.min(a)):.6g} to {float(np.max(a)):.6g}"


# ----------------------------------------------------------------------
# plt.show() replacement: save each figure to output/ with a numbered name
# ----------------------------------------------------------------------
saved_figures = []
_fig_state = {"prefix": "fig", "names": [], "count": 0}


def _save_and_close(*args, **kwargs):
    _fig_state["count"] += 1
    n = _fig_state["count"]
    names = _fig_state["names"]
    label = names[n - 1] if n <= len(names) else f"figure{n}"
    path = OUTPUT / f"{_fig_state['prefix']}_{n:02d}_{label}.png"
    plt.gcf().savefig(path, dpi=110, bbox_inches="tight")
    plt.close("all")
    saved_figures.append(path.name)
    print(f"    [figure saved] output/{path.name}")


plt.show = _save_and_close


def code_cells(notebook_path):
    """Return the source text of every code cell of a Jupyter notebook."""
    nb = json.loads(Path(notebook_path).read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def run_source(src, label, namespace, workdir=None):
    """Execute one piece of notebook code in the shared namespace."""
    print(f"--- {label}")
    start_dir = os.getcwd()
    try:
        if workdir is not None:
            os.chdir(workdir)
        exec(compile(src, label, "exec"), namespace)
    finally:
        os.chdir(start_dir)


# ----------------------------------------------------------------------
# Split code/B_mode.ipynb into Team 6's part and this stage's part
# ----------------------------------------------------------------------
NB = CODE / "B_mode.ipynb"
cells = code_cells(NB)
MARK = "# 5. APPLY DYNAMIC RANGE"
cell5 = cells[4]
cut = cell5.rindex("# ====", 0, cell5.index(MARK))  # the '=' line just before the marker
CELL5_TEAM7 = cell5[cut:]                            # sections 5 and 6 of code cell 5
# cell 1's import lines only (NOT its np.load): numpy and matplotlib.pyplot
IMPORTS = "\n".join(ln for ln in cells[0].splitlines()
                    if ln.startswith("import numpy") or ln.startswith("import matplotlib.pyplot"))

HANDOFF_KEYS = ["rf", "envelope", "envelope_norm", "envelope_db", "fs", "f0", "c", "pitch", "depth_start_mm"]


def load_handoff(n):
    """Load Team 6's handoff file into a fresh namespace (arrays + Python scalars)."""
    d = np.load(INPUT / f"reconstructed_carotid_{n}.npz")
    ns = {"__name__": "__main__"}
    for k in HANDOFF_KEYS:
        v = d[k]
        ns[k] = v.item() if v.ndim == 0 else v
    ns["DATA_FILE"] = f"carotid_{n}_rf.npy"  # cell 9 derives the output name from it
    return ns


timings = {}
t_total = time.perf_counter()

banner("TEAM 7 - B-MODE IMAGE FORMATION  (NITK-UsoundSim)")
print("Stage order: Team 6 Image Reconstruction (Hilbert envelope + log compression)")
print("          -> Team 7 B-mode Image Formation (THIS STAGE: dynamic range, gray levels, axes, final image)")
print("          -> Team 8 Post-Image Processing (despeckling)")
print("Folder :", ROOT.name)
print("Python :", sys.version.split()[0], "| numpy", np.__version__, "| matplotlib", matplotlib.__version__)

# ----------------------------------------------------------------------
# PART 1: the input (Team 6's handoff)
# ----------------------------------------------------------------------
banner("PART 1: INPUT = output of Team 6 (Image Reconstruction), copied into input/")
t = time.perf_counter()
handoff = {}
for n in (1, 2):
    d = np.load(INPUT / f"reconstructed_carotid_{n}.npz")
    handoff[n] = d
    print(f"input/reconstructed_carotid_{n}.npz")
    for k in HANDOFF_KEYS:
        v = d[k]
        if v.ndim == 0:
            print(f"  {k:<15s} scalar {v.dtype}  = {v.item()}")
        else:
            print(f"  {k:<15s} shape {v.shape}, {v.dtype}, values {rng(v)}")

fig, ax = plt.subplots(1, 3, figsize=(16, 6), gridspec_kw={"width_ratios": [1, 1, 1.25]})
for k, n in enumerate((1, 2)):
    d = handoff[n]
    L = d["envelope_db"]
    nz, nx = L.shape
    dmm = float(d["depth_start_mm"]) + np.arange(nz) / float(d["fs"]) * float(d["c"]) / 2 * 1000
    wmm = (np.arange(nx) - nx / 2) * float(d["pitch"]) * 1000
    im = ax[k].imshow(L, cmap="gray", vmin=float(L.min()), vmax=0, extent=[wmm[0], wmm[-1], dmm[-1], dmm[0]])
    ax[k].set_title(f"reconstructed_carotid_{n}.npz: envelope_db\n(full range {L.min():.1f} to 0 dB, not clipped)")
    ax[k].set_xlabel("Lateral (mm)")
    ax[k].set_ylabel("Depth (mm)")
    plt.colorbar(im, ax=ax[k], label="dB (0 dB = peak)")
    ax[2].hist(L.ravel(), bins=180, histtype="step", lw=1.2, label=f"carotid_{n}")
for dr, ls in [(40, ":"), (50, "--"), (60, "-")]:
    ax[2].axvline(-dr, color="k", ls=ls, lw=1, label=f"-{dr} dB (clip level for DR = {dr} dB)")
ax[2].set_xlabel("envelope_db value (dB)")
ax[2].set_ylabel("Number of pixels")
ax[2].set_title("Histogram of the input dB values")
ax[2].legend(fontsize=8)
fig.tight_layout()
fig.savefig(OUTPUT / "input_envelope_db_overview.png", dpi=110)
plt.close(fig)
saved_figures.append("input_envelope_db_overview.png")
print("    [figure saved] output/input_envelope_db_overview.png  (runner figure)")
timings["Part 1 input overview"] = time.perf_counter() - t

# ----------------------------------------------------------------------
# PART 2: this stage's notebook code on the handoff data
# ----------------------------------------------------------------------
carotid_figs = ["all_steps", "final_bmode"]
ns_all = {}
for n in (1, 2):
    banner(f"PART 2.{n}: code/B_mode.ipynb, B-mode part, on reconstructed_carotid_{n}.npz")
    print("Loaded into the namespace from the input file: " + ", ".join(HANDOFF_KEYS))
    print(f'Runner sets DATA_FILE = "carotid_{n}_rf.npy" (only used by cell 9 to name the saved files).')
    print("Not run here (Team 6's work): cell 1 np.load, cell 3 Hilbert, cell 4 scan-line plot,")
    print("cell 5 sections 3-4 (normalise, log compression).")
    t = time.perf_counter()
    _fig_state.update(prefix=f"carotid_{n}", names=carotid_figs, count=0)
    ns = load_handoff(n)
    run_source(IMPORTS, "cell 1, import lines only: " + IMPORTS.replace("\n", "; "), ns)
    run_source(cells[1], "B_mode.ipynb code cell 2 (settings; gives dynamic_range)", ns)
    run_source(CELL5_TEAM7, "B_mode.ipynb code cell 5, sections 5-6 (clip to dynamic range, brightness 0..1)", ns)
    run_source(cells[5], "B_mode.ipynb code cell 6 (depth and width axes)", ns)
    run_source(cells[6], "B_mode.ipynb code cell 7 (display all steps)", ns)
    run_source(cells[7], "B_mode.ipynb code cell 8 (final B-mode image)", ns)
    run_source(cells[8], "B_mode.ipynb code cell 9 (save, run inside output/)", ns, workdir=OUTPUT)
    ns_all[n] = ns
    timings[f"Part 2.{n} notebook stage, carotid_{n}"] = time.perf_counter() - t

# ----------------------------------------------------------------------
# PART 3: dynamic range comparison (runner figure, the notebook's formula)
# ----------------------------------------------------------------------
banner("PART 3: effect of the dynamic range (runner figure, notebook formula)")
print("For DR = 40, 50, 60 dB:  B = (clip(envelope_db, -DR, 0) + DR) / DR  from the input envelope_db")
t = time.perf_counter()
dr_images = {}
black = {}
for n in (1, 2):
    L = handoff[n]["envelope_db"]
    for dr in (40, 50, 60):
        b = (np.clip(L, -dr, 0) + dr) / dr
        dr_images[(n, dr)] = b
        black[(n, dr)] = 100.0 * np.mean(b == 0)
        print(f"  carotid_{n}, DR {dr} dB: mean brightness {b.mean():.3f}, "
              f"black (clipped) pixels {black[(n, dr)]:5.2f} %, pixels at full white {np.sum(b == 1)}")
ext = ns_all[1]["extent"]
fig, ax = plt.subplots(2, 3, figsize=(12, 10.5))
for r, n in enumerate((1, 2)):
    for k, dr in enumerate((40, 50, 60)):
        im = ax[r, k].imshow(dr_images[(n, dr)], cmap="gray", vmin=0, vmax=1, extent=ext)
        ax[r, k].set_title(f"carotid_{n}, DR {dr} dB\n(black pixels {black[(n, dr)]:.1f} %)")
        ax[r, k].set_xlabel("Lateral (mm)")
        ax[r, k].set_ylabel("Depth (mm)")
fig.colorbar(im, ax=ax, fraction=0.025, label="Brightness (0 = black, 1 = white)")
fig.suptitle("Runner figure: dynamic range 40 / 50 / 60 dB applied to Team 6's envelope_db")
fig.savefig(OUTPUT / "dynamic_range_40_50_60dB.png", dpi=110, bbox_inches="tight")
plt.close(fig)
saved_figures.append("dynamic_range_40_50_60dB.png")
print("    [figure saved] output/dynamic_range_40_50_60dB.png  (runner figure)")
same60 = np.array_equal(dr_images[(1, 60)], ns_all[1]["bmode"])
print(f"  60 dB image here identical to the notebook's bmode for carotid_1: {same60}")
timings["Part 3 dynamic range comparison"] = time.perf_counter() - t

# ----------------------------------------------------------------------
# PART 4: reproducibility check against the notebook's earlier saved image
# ----------------------------------------------------------------------
banner("PART 4: reproducibility check (this run vs the image the notebook saved earlier)")
t = time.perf_counter()
ref = np.load(INPUT / "reference" / "bmode_carotid_1.npy")
ref_axes = np.load(INPUT / "reference" / "bmode_carotid_1_axes.npz")
saved_today = np.load(OUTPUT / "bmode_carotid_1.npy")
axes_today = np.load(OUTPUT / "bmode_carotid_1_axes.npz")
diff = np.abs(saved_today.astype(np.float64) - ref.astype(np.float64))
d_nb = float(diff.max())
axes_same = all(np.array_equal(ref_axes[k], axes_today[k]) for k in ("depth_mm", "width_mm"))
gray_diff = np.abs(np.round(255 * saved_today.astype(np.float64)) - np.round(255 * ref.astype(np.float64)))
print(f"  this run  output/bmode_carotid_1.npy          : shape {saved_today.shape}, {saved_today.dtype}, values {rng(saved_today)}")
print(f"  reference input/reference/bmode_carotid_1.npy : shape {ref.shape}, {ref.dtype}, values {rng(ref)}")
print(f"  max |this run - reference|                     = {d_nb:.3g}")
print(f"  mean |this run - reference|                    = {float(diff.mean()):.3g}")
print(f"  8-bit gray levels round(255 * B): {int(np.sum(gray_diff > 0))} of {gray_diff.size} pixels differ, "
      f"by at most {int(gray_diff.max())} level (values that sit right on a rounding boundary)")
print(f"  depth_mm and width_mm identical to reference   : {axes_same}")
ok = d_nb < 1e-5 and axes_same
print("  RESULT:", "PASS - same image (difference is float32 rounding, far below one gray level 1/255 = 0.0039)"
      if ok else "FAIL - results differ")
timings["Part 4 reproducibility check"] = time.perf_counter() - t

fig, ax = plt.subplots(1, 3, figsize=(13, 6))
for a, img, title in [(ax[0], ref, "Saved reference\n(input/reference/bmode_carotid_1.npy)"),
                      (ax[1], saved_today, "This run\n(output/bmode_carotid_1.npy, 60 dB)")]:
    a.imshow(img, cmap="gray", vmin=0, vmax=1, extent=ext)
    a.set_title(title)
    a.set_xlabel("Lateral (mm)")
    a.set_ylabel("Depth (mm)")
im = ax[2].imshow(diff, cmap="magma", extent=ext)
ax[2].set_title(f"|this run - reference|\n(max {d_nb:.2g})")
ax[2].set_xlabel("Lateral (mm)")
plt.colorbar(im, ax=ax[2])
fig.tight_layout()
fig.savefig(OUTPUT / "reproducibility_check_60dB.png", dpi=110)
plt.close(fig)
saved_figures.append("reproducibility_check_60dB.png")
print("    [figure saved] output/reproducibility_check_60dB.png  (runner figure)")

# ----------------------------------------------------------------------
# PART 6: summary
# ----------------------------------------------------------------------
banner("PART 5: SUMMARY")
for n in (1, 2):
    ns = ns_all[n]
    L_in = handoff[n]["envelope_db"]
    print(f"carotid_{n}:")
    print(f"  input envelope_db  {L_in.shape}, {L_in.dtype}, values {rng(L_in)} dB")
    print(f"  dynamic range      {ns['dynamic_range']} dB  -> clipped dB values {rng(ns['envelope_db'])} dB")
    print(f"  B-mode brightness  {ns['bmode'].dtype}, values {rng(ns['bmode'])}, mean {ns['bmode'].mean():.3f}")
    print(f"  8-bit gray levels  0 to 255 (round(255 * B)): mean {np.round(255 * ns['bmode']).mean():.1f}")
    print(f"  axes               depth {ns['depth_mm'][0]:.1f} to {ns['depth_mm'][-1]:.1f} mm, "
          f"lateral {ns['width_mm'][0]:.1f} to {ns['width_mm'][-1]:.1f} mm")
    print("  black pixels       " + ", ".join(f"{dr} dB: {black[(n, dr)]:.2f} %" for dr in (40, 50, 60)))
print(f"Reproducibility (carotid_1): max |this run - reference| = {d_nb:.3g}  ({'PASS' if ok else 'FAIL'})")
print("\nTimings:")
for k, v in timings.items():
    print(f"  {k:<40s} {v:6.2f} s")
total = time.perf_counter() - t_total
print(f"  {'TOTAL':<40s} {total:6.2f} s")

print("\nFiles written to output/:")
for f in sorted(p.name for p in OUTPUT.iterdir() if not p.name.startswith("console_")):
    print("  ", f)
print("   console_log.txt")
print("   console_screenshot_1.png, _2.png, ... (pictures of this console text, 75 lines each)")
print("\nDone.")

# ----------------------------------------------------------------------
# Save the console text and a screenshot-style picture of it
# ----------------------------------------------------------------------
sys.stdout = tee.stream
text = tee.buffer_text.getvalue()
(OUTPUT / "console_log.txt").write_text(text, encoding="utf-8")

lines = []
for line in text.splitlines():
    while len(line) > 125:
        lines.append(line[:125])
        line = "    " + line[125:]
    lines.append(line)
# one picture per 75 lines, so each picture fits on a page
chunks = [lines[i:i + 75] for i in range(0, len(lines), 75)]
shots = []
for k, chunk in enumerate(chunks, start=1):
    h = 0.6 + 0.165 * len(chunk)
    fig = plt.figure(figsize=(13.5, h), facecolor="#1e1e1e")
    fig.text(0.01, 1 - 0.25 / h, f"Terminal - python3 run_team7.py   (part {k} of {len(chunks)})", color="#9cdcfe",
             family="monospace", fontsize=9, va="top", weight="bold")
    fig.text(0.01, 1 - 0.55 / h, "\n".join(chunk), color="#e8e8e8", family="monospace",
             fontsize=8.2, va="top", linespacing=1.25)
    name = f"console_screenshot_{k}.png"
    fig.savefig(OUTPUT / name, dpi=100, facecolor="#1e1e1e")
    plt.close(fig)
    shots.append(name)
print("Console log saved to output/console_log.txt and output/" + ", output/".join(shots))
