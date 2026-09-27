"""
run_team6.py - Team 6 demo: Image Reconstruction (NITK-UsoundSim).

Stage order in the project:
    Image Reconstruction (Team 6, THIS folder): Hilbert envelope -> normalisation -> log compression (dB)
    -> B-mode Image Formation (Team 7): dynamic range, grayscale brightness 0-1, final B-mode image
    -> Post-Image Processing (Team 8): despeckling of the finished image

One command runs the stage and saves every result into output/:

    python3 run_team6.py        (macOS / Linux)
    python  run_team6.py        (Windows)

Part 1 (main demo, real in-vivo carotid RF data, code/B_mode.ipynb):
    runs code cells 1, 2, 3, 4 of the notebook in order, then ONLY the first half of code cell 5
    (sections "3. NORMALIZE ENVELOPE" and "4. LOG COMPRESSION"). The second half of cell 5 (dynamic range and
    brightness) and cells 6-9 belong to Team 7 and are not run here. This is done for carotid_1 and carotid_2.
    The result is saved as the handoff for Team 7: output/reconstructed_carotid_1.npz, output/reconstructed_carotid_2.npz

Part 2 (the team's second notebook, code/image_reconstruction.ipynb):
    simulated 5 MHz RF -> DC removal -> band-pass filter -> Hilbert envelope -> scan conversion.

The notebooks in code/ are NOT changed; this script only reads them and runs their code.
"""
import io
import json
import os
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # save figures to files, do not open windows
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
CODE, INPUT, OUTPUT = HERE / "code", HERE / "input", HERE / "output"
OUTPUT.mkdir(exist_ok=True)


# ----------------------------------------------------------------------------------------
# Console helper: everything printed goes to the screen AND to output/console_log.txt
# ----------------------------------------------------------------------------------------
class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
        return len(s)

    def flush(self):
        for st in self.streams:
            st.flush()


LOG = io.StringIO()
REAL_STDOUT = sys.stdout
sys.stdout = Tee(REAL_STDOUT, LOG)
SAVED = []  # list of (file name, meaning)


def save(fig, name, meaning, dpi=130):
    fig.savefig(OUTPUT / name, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    SAVED.append((name, meaning))
    print(f"  saved output/{name}")


def banner(text):
    print("\n" + "=" * 78 + f"\n{text}\n" + "=" * 78)


def code_cells(nb_path):
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


t_start = time.time()
banner("TEAM 6: IMAGE RECONSTRUCTION  (NITK-UsoundSim)")
print(f"Python {sys.version.split()[0]}, numpy {np.__version__}, matplotlib {matplotlib.__version__}")
print("Stage order: Image Reconstruction (Team 6: Hilbert envelope + log compression)")
print("          -> B-mode Image Formation (Team 7: dynamic range + grayscale image)")
print("          -> Post-Image Processing (Team 8: despeckling)")

# ========================================================================================
# PART 1: real carotid RF data, code/B_mode.ipynb, steps 1-4 only
# ========================================================================================
banner("PART 1: real in-vivo carotid RF  (code/B_mode.ipynb, steps 1-4)")
bm_cells = code_cells(CODE / "B_mode.ipynb")
print(f"B_mode.ipynb has {len(bm_cells)} code cells. This stage runs cells 1, 2, 3, 4 and the first half of cell 5.")

# Split code cell 5 at the "# 5. APPLY DYNAMIC RANGE" heading. The heading is a 3-line comment block
#   # ==========================================
#   # 5. APPLY DYNAMIC RANGE
#   # ==========================================
# so the '=' line just above the marker already belongs to the second half (Team 7's part).
cell5_lines = bm_cells[4].split("\n")
k = next(i for i, ln in enumerate(cell5_lines) if "# 5. APPLY DYNAMIC RANGE" in ln)
assert cell5_lines[k - 1].strip().startswith("# ====="), "unexpected layout of code cell 5"
cell5_part1 = "\n".join(cell5_lines[:k - 1]).rstrip() + "\n"   # sections 3 (normalise) and 4 (log compression)
cell5_part2 = "\n".join(cell5_lines[k - 1:])                     # sections 5 and 6: Team 7, NOT run here
print(f"Code cell 5 split at line {k} (the '=' line above '# 5. APPLY DYNAMIC RANGE'):")
print(f"  first half  = lines 1-{k - 1}  (3. NORMALIZE ENVELOPE, 4. LOG COMPRESSION)  -> run here")
print(f"  second half = lines {k}-{len(cell5_lines)}  (5. APPLY DYNAMIC RANGE, 6. CONVERT dB TO BRIGHTNESS) -> Team 7")

OLD_LINE = 'DATA_FILE = "carotid_1_rf.npy"'
PARAMS = ["fs", "f0", "c", "pitch", "depth_start_mm"]
HANDOFF = {}

for n in (1, 2):
    name = f"carotid_{n}"
    banner(f"Part 1, {name}: run notebook cells 1-4 and cell 5 (first half)")
    cells = [bm_cells[0], bm_cells[1], bm_cells[2], bm_cells[3], cell5_part1]
    if n == 2:  # change only the file name line, in memory (the notebook file is not edited)
        assert bm_cells[0].count(OLD_LINE) == 1
        cells[0] = bm_cells[0].replace(OLD_LINE, 'DATA_FILE = "carotid_2_rf.npy"')
        print(f"  (in memory only) replaced the line {OLD_LINE} by DATA_FILE = \"carotid_2_rf.npy\"")
    labels = ["cell 1", "cell 2", "cell 3", "cell 4", "cell 5 (first half)"]

    fig_no = [0]

    def show_and_save(*args, _name=name, **kwargs):
        """Replacement for plt.show(): saves the notebook's current figure to output/."""
        fig_no[0] += 1
        save(plt.gcf(), f"{_name}_01_notebook_rf_and_envelope.png",
             f"{_name}: figure drawn by the notebook itself (code cell 4): RF signal and its Hilbert envelope of the "
             f"middle scan line.")

    ns = {"__name__": "__main__"}
    real_show, old_cwd = plt.show, os.getcwd()
    plt.show = show_and_save
    os.chdir(INPUT)  # the notebook loads the bare file name "carotid_N_rf.npy"
    try:
        t0 = time.time()
        for lab, src in zip(labels, cells):
            print(f"--- running B_mode.ipynb {lab} ({len(src.strip().splitlines())} lines) ---")
            exec(compile(src, f"B_mode.ipynb[{lab}]", "exec"), ns)
    finally:
        os.chdir(old_cwd)
        plt.show = real_show
    print(f"Notebook code finished in {time.time() - t0:.1f} s")

    rf, env, env_n, env_db = ns["rf"], ns["envelope"], ns["envelope_norm"], ns["envelope_db"]
    print("\nRunner checks on the notebook's variables:")
    for v in ("rf", "envelope", "envelope_norm", "envelope_db"):
        a = ns[v]
        print(f"  {v:14s}: shape {a.shape}, dtype {a.dtype}, min {a.min():.6g}, max {a.max():.6g}")
    print(f"  envelope >= |rf| everywhere (tolerance 1e-3 x max): "
          f"{bool(np.all(env >= np.abs(rf) - 1e-3 * env.max()))}")
    print(f"  envelope max / min = {env.max() / env.min():.0f}  ->  {20 * np.log10(env.max() / env.min()):.1f} dB "
          f"between the strongest and the weakest echo")
    print(f"  envelope_db: min {env_db.min():.2f} dB, max {env_db.max():.2f} dB (0 dB = peak), "
          f"median {np.median(env_db):.2f} dB")
    for lim in (40, 50, 60):
        print(f"  pixels below -{lim} dB: {100 * np.mean(env_db < -lim):5.2f} %")
    print("  (envelope_db is NOT clipped here: choosing the dynamic range and clipping is Team 7's step)")

    # ---- handoff file for Team 7
    out = OUTPUT / f"reconstructed_{name}.npz"
    np.savez(out, rf=rf, envelope=env, envelope_norm=env_n, envelope_db=env_db,
             **{p: np.float64(ns[p]) for p in PARAMS})
    HANDOFF[name] = out
    SAVED.append((out.name, f"HANDOFF for Team 7: rf, envelope, envelope_norm, envelope_db + fs, f0, c, pitch, "
                            f"depth_start_mm of {name}"))
    print(f"\nHandoff for Team 7 (B-mode Image Formation): output/{out.name}")
    with np.load(out) as d:
        for key in d.files:
            a = d[key]
            extra = f"value {a.item():g}" if a.ndim == 0 else f"min {a.min():.6g}, max {a.max():.6g}"
            print(f"    {key:15s} shape {str(a.shape):12s} dtype {str(a.dtype):8s} {extra}")

    # ---- runner figures
    z = ns["depth_axis_mm"]                                              # notebook cell 4 variable
    x = (np.arange(rf.shape[1]) - rf.shape[1] / 2) * ns["pitch"] * 1000   # same formula as notebook cell 6
    ext = [x[0], x[-1], z[-1], z[0]]
    rf_lim = np.percentile(np.abs(rf), 99)

    fig, ax = plt.subplots(1, 3, figsize=(15, 6.2))
    im = ax[0].imshow(rf, cmap="gray", extent=ext, vmin=-rf_lim, vmax=rf_lim)
    ax[0].set_title(f"Input: beamformed RF\n(colour limits +/- 99th percentile of |rf|)", fontsize=10)
    plt.colorbar(im, ax=ax[0], label="amplitude")
    im = ax[1].imshow(env, cmap="gray", extent=ext)
    ax[1].set_title("Envelope |hilbert(rf)|, linear scale\n(only the strongest echoes are visible)", fontsize=10)
    plt.colorbar(im, ax=ax[1], label="amplitude")
    im = ax[2].imshow(env_db, cmap="gray", extent=ext, vmin=-60, vmax=0)
    ax[2].set_title("Log-compressed envelope_db\n(display window -60..0 dB)", fontsize=10)
    plt.colorbar(im, ax=ax[2], label="dB (0 dB = peak)")
    for a in ax:
        a.set_xlabel("lateral (mm)"); a.set_ylabel("depth (mm)")
    fig.suptitle(f"Runner figure, {name}: RF input -> envelope -> log compression (Team 6 output)", fontsize=11)
    fig.tight_layout()
    save(fig, f"{name}_02_runner_rf_envelope_db.png",
         f"Runner figure, {name}: the RF input, the linear envelope and the log-compressed envelope (dB).")

    fig, ax = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw=dict(width_ratios=[1, 1.25]))
    im = ax[0].imshow(env_db, cmap="viridis", extent=ext, vmin=env_db.min(), vmax=0)
    ax[0].set_title(f"envelope_db, full unclipped range\n({env_db.min():.1f} to 0 dB)", fontsize=10)
    ax[0].set_xlabel("lateral (mm)"); ax[0].set_ylabel("depth (mm)")
    plt.colorbar(im, ax=ax[0], label="dB")
    ax[1].hist(env_db.ravel(), bins=120, color="tab:blue", alpha=0.85)
    for lim, col in ((40, "tab:red"), (50, "tab:orange"), (60, "tab:green")):
        ax[1].axvline(-lim, color=col, ls="--", lw=1.2, label=f"-{lim} dB ({100 * np.mean(env_db < -lim):.1f} % below)")
    ax[1].set_xlabel("envelope_db (dB)"); ax[1].set_ylabel("number of pixels")
    ax[1].set_title("Histogram of envelope_db values\n(dashed lines: possible dynamic-range limits Team 7 may choose)",
                    fontsize=10)
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    fig.suptitle(f"Runner figure, {name}: the log-compressed data handed to Team 7 (not clipped)", fontsize=11)
    fig.tight_layout()
    save(fig, f"{name}_03_runner_db_full_range_and_histogram.png",
         f"Runner figure, {name}: envelope_db over its whole range and the histogram of its values.")

# ========================================================================================
# PART 2: code/image_reconstruction.ipynb (simulated RF, all code cells, unchanged)
# ========================================================================================
banner("PART 2: simulated RF  (code/image_reconstruction.ipynb)")
cells = code_cells(CODE / "image_reconstruction.ipynb")
print(f"Notebook has {len(cells)} code cells. Running them in order...\n")


def show_and_save_sim(*args, **kwargs):
    save(plt.gcf(), "sim_A1_notebook_rf_envelope_and_scan_conversion.png",
         "Figure made by image_reconstruction.ipynb itself: left = band-pass filtered RF of scan line 32 with its "
         "Hilbert envelope; right = scan-converted (reconstructed) envelope image.")


ns = {"__name__": "__main__"}
real_show = plt.show
plt.show = show_and_save_sim
t0 = time.time()
try:
    for i, src in enumerate(cells):
        print(f"--- running code cell {i} ({len(src.splitlines())} lines) ---")
        exec(compile(src, f"image_reconstruction.ipynb[cell {i}]", "exec"), ns)
finally:
    plt.show = real_show
print(f"\nNotebook code finished in {time.time() - t0:.1f} s")

print("\nRunner checks on the notebook's variables:")
print(f"  simulated raw RF matrix : {ns['raw_rf_input'].shape[0]} samples x {ns['raw_rf_input'].shape[1]} scan lines "
      f"(fs = {ns['fs'] / 1e6:.0f} MHz, fc = {ns['fc'] / 1e6:.0f} MHz)")
print(f"  band-pass filter        : Butterworth order 2, {ns['low_cut'] / 1e6:.0f}-{ns['high_cut'] / 1e6:.0f} MHz, "
      f"zero-phase (filtfilt)")
print(f"  mean of raw RF (DC)     : {ns['raw_rf_input'].mean():.4f}  ->  after DC removal + filter: "
      f"{ns['preprocessed_rf'].mean():.2e}")
for depth, line, strength in ns["targets"]:
    e = ns["envelope"][:, line]
    kk = np.argmax(e)
    print(f"  target at {depth * 1e3:4.0f} mm on line {line:2d}: envelope peak found at "
          f"{ns['depth_mm'][kk]:6.2f} mm, peak value {e[kk]:.3f} (reflectivity {strength})")
rec = ns["reconstructed_envelope"]
print(f"  reconstructed image     : {rec.shape}, min {rec.min():.3f}, max {rec.max():.3f}, "
      f"zero-filled (outside sector) pixels {100 * np.mean(rec == 0):.1f} %")

d, raw, pre, env = ns["depth_mm"], ns["raw_rf_input"], ns["preprocessed_rf"], ns["envelope"]
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
ax[0].plot(d, raw[:, 32], lw=0.7, color="0.4", label="raw simulated RF (with DC bias + noise)")
ax[0].plot(d, pre[:, 32], lw=0.9, color="tab:blue", label="after DC removal + 2-8 MHz band-pass")
ax[0].set_xlim(10, 20); ax[0].set_xlabel("depth (mm)"); ax[0].set_ylabel("amplitude"); ax[0].grid(alpha=0.3)
ax[0].set_title("Scan line 32, zoom 10-20 mm (target at 15 mm)"); ax[0].legend(fontsize=8)
nb10 = raw.shape[0] // 10
blk = np.abs(raw[:nb10 * 10] - raw.mean()).reshape(nb10, 10, -1).max(axis=1)  # peak |RF| per 10 samples
im = ax[1].imshow(blk, aspect="auto", cmap="gray", vmin=0, vmax=0.8, extent=[0, raw.shape[1] - 1, d[-1], d[0]])
ax[1].set_xlabel("scan line index"); ax[1].set_ylabel("depth (mm)")
ax[1].set_title("Simulated raw RF matrix:\npeak |RF| per 10 samples, DC removed for display", fontsize=10)
plt.colorbar(im, ax=ax[1], label="|amplitude|")
fig.suptitle("Runner figure (Part 2): the simulated RF input of image_reconstruction.ipynb", fontsize=11, y=1.04)
save(fig, "sim_A2_runner_raw_rf_input.png",
     "Runner figure (Part 2): the simulated raw RF for line 32 before/after filtering, and the full RF matrix.")

env_db = 20 * np.log10(env / env.max() + 1e-6)
rec_db = 20 * np.log10(np.maximum(rec, 1e-6) / rec.max())
fig, ax = plt.subplots(1, 3, figsize=(16, 5.6), gridspec_kw=dict(width_ratios=[1, 1, 1.35]))
ax[0].imshow(env, aspect="auto", cmap="gray", extent=[0, 63, d[-1], d[0]])
ax[0].set_title("Envelope (linear), lines x depth"); ax[0].set_xlabel("scan line"); ax[0].set_ylabel("depth (mm)")
ax[1].imshow(env_db, aspect="auto", cmap="gray", vmin=-40, vmax=0, extent=[0, 63, d[-1], d[0]])
ax[1].set_title("Envelope in dB (display window -40..0 dB)"); ax[1].set_xlabel("scan line")
xc, zc = ns["x_cart"], ns["z_cart"]
im = ax[2].imshow(rec_db, cmap="gray", vmin=-40, vmax=0, extent=[xc[0], xc[-1], zc[-1], zc[0]], aspect="equal")
ax[2].set_title("Scan-converted image in dB\n(display window -40..0 dB)"); ax[2].set_xlabel("lateral (mm)")
ax[2].set_ylabel("depth (mm)"); plt.colorbar(im, ax=ax[2], label="dB")
fig.suptitle("Runner figure (Part 2): envelope before and after scan conversion, linear and in dB "
             "(the notebook itself stops at the linear envelope)", fontsize=10)
save(fig, "sim_A3_runner_envelope_db_and_scan_converted.png",
     "Runner figure (Part 2): envelope as lines x depth (linear and in dB) and the scan-converted sector image in dB.")

# ========================================================================================
banner("SUMMARY")
for name, path in HANDOFF.items():
    with np.load(path) as dd:
        print(f"{name}: envelope_db {dd['envelope_db'].shape} {dd['envelope_db'].dtype}, "
              f"{dd['envelope_db'].min():.2f} to {dd['envelope_db'].max():.2f} dB")
    print(f"  Handoff for Team 7 (B-mode Image Formation): output/{path.name}")
print(f"Part 2: reconstructed (scan-converted) envelope {ns['reconstructed_envelope'].shape}; envelope peaks found for "
      f"all {len(ns['targets'])} targets.")
print(f"Files written to output/: {len(SAVED) + 2} (including console_log.txt and console_screenshot.png)")
print(f"Total run time: {time.time() - t_start:.1f} s")

# ---------------------------------------------------------------- console log + screenshot
sys.stdout = REAL_STDOUT
text = LOG.getvalue()
(OUTPUT / "console_log.txt").write_text(text, encoding="utf-8")


def console_png(text, out_png, width=112):
    lines = []
    for ln in text.rstrip("\n").splitlines():
        while len(ln) > width:
            lines.append(ln[:width]); ln = "   " + ln[width:]
        lines.append(ln)
    h = 0.6 + 0.16 * len(lines)
    fig = plt.figure(figsize=(0.083 * width + 0.4, h))
    fig.patch.set_facecolor("#1e1e1e")
    fig.text(0.01, 1 - 0.28 / h, "Terminal: python3 run_team6.py", color="#9a9a9a", fontsize=9, family="monospace",
             va="center")
    for i, ln in enumerate(lines):
        fig.text(0.01, 1 - (0.55 + 0.16 * i) / h, ln, color="#e6e6e6", fontsize=8.4, family="monospace", va="top")
    fig.savefig(out_png, dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)


console_png(text, OUTPUT / "console_screenshot.png")
print("Saved output/console_log.txt and output/console_screenshot.png")
