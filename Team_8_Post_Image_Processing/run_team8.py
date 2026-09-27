"""
run_team8.py - Team 8 demo: Post-Image Processing (despeckling).

One command runs the stage and saves every result into the output/ folder:

    python3 run_team8.py        (macOS / Linux)
    python  run_team8.py        (Windows)

It loads two finished grayscale B-mode images from input/ (the output of the B-mode Image
Formation stage), despeckles them with postprocess() from code/post_processing.py (guided
filter, r = 4, eps = 0.001), and measures image quality before and after with the module's
own metric functions.

The team's files in code/ are NOT changed; this script only calls them.
"""
import io
import json
import sys
import time
import types
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


def save(fig, name, meaning):
    fig.savefig(OUTPUT / name, dpi=130, bbox_inches="tight")
    plt.close(fig)
    SAVED.append((name, meaning))
    print(f"  saved output/{name}")


def banner(text):
    print("\n" + "=" * 78 + f"\n{text}\n" + "=" * 78)



t_start = time.time()
banner("TEAM 8: POST-IMAGE PROCESSING  (NITK-UsoundSim)")
print(f"Python {sys.version.split()[0]}, numpy {np.__version__}, matplotlib {matplotlib.__version__}")
print(f"Folder: {HERE.name}")

# ========================================================================================
# Post-Image Processing (despeckling with the guided filter)
# ========================================================================================
banner("Post-Image Processing  (code/post_processing.py)")
sys.dont_write_bytecode = True  # keep code/ clean (no __pycache__ folder)
sys.path.insert(0, str(CODE))
try:
    import config  # noqa: F401  (the full project's settings file)
except ImportError:
    # post_processing.py does "import config" for its scan_convert() function, which belongs to
    # the B-mode team and is NOT used in this demo. The project's config.py is not part of this
    # folder, so an empty placeholder module is registered to let the file import unchanged.
    sys.modules["config"] = types.ModuleType("config")
    print("Note: project config.py not in this folder -> empty placeholder used")
    print("      (only scan_convert() needs it, and scan_convert() is not used in this demo).")
import post_processing as pp  # noqa: E402

print("Filter: postprocess(image) with its defaults -> method='guided', r=4, eps=0.001, gamma=1.0\n")

data = {}
for name in ["cyst_lesion", "scatterers"]:
    z = np.load(INPUT / f"{name}_image.npz")
    img = z["image"].astype(float)
    t0 = time.time()
    out = pp.postprocess(img)
    ms = 1000 * (time.time() - t0)
    data[name] = dict(img=img, out=out, x=z["x_img"] * 1e3, z=z["z_img"] * 1e3, ms=ms)
    print(f"{name:12s}: input {img.shape}, range {img.min():.3f}-{img.max():.3f}  ->  output range "
          f"{out.min():.3f}-{out.max():.3f}, time {ms:.1f} ms")

# Lesion mask for the cyst: circle, radius 6 mm, centre (x = 0, z = 30) mm on the image grid
C = data["cyst_lesion"]
XX, ZZ = np.meshgrid(C["x"], C["z"])
lesion = (XX - 0.0) ** 2 + (ZZ - 30.0) ** 2 <= 6.0 ** 2
ring = pp.lesion_ring(lesion)
print(f"\nCyst lesion mask: circle r = 6 mm at (0, 30) mm -> {lesion.sum()} px; background ring "
      f"({pp.RING} px wide) -> {ring.sum()} px")


def measure(img01):
    u8 = pp.to_uint8(img01)
    f = u8.astype(float) / 255
    return dict(SI=pp.speckle_index(u8), contrast_db=50 * (f[lesion].mean() - f[ring].mean()),
                CNR=pp.cnr(u8, lesion), gCNR=pp.gcnr(u8, lesion), edge=pp.edge_sharpness(u8, lesion))


print("\nQuality metrics (computed on uint8 images with the module's own functions):")
print(f"{'image':12s} {'metric':34s} {'before':>9s} {'after':>9s} {'change':>10s}")
print("-" * 78)
for name in ["scatterers", "cyst_lesion"]:
    D = data[name]
    si0, si1 = pp.speckle_index(pp.to_uint8(D["img"])), pp.speckle_index(pp.to_uint8(D["out"]))
    D["SI"] = (si0, si1)
    print(f"{name:12s} {'speckle index SI (lower = smoother)':34s} {si0:9.3f} {si1:9.3f} {100 * (si1 / si0 - 1):+9.1f}%")
m0, m1 = measure(C["img"]), measure(C["out"])
C["m0"], C["m1"] = m0, m1
for key, label in [("contrast_db", "contrast lesion-ring (dB, 50 dB DR)"), ("CNR", "CNR (higher = better)"),
                   ("gCNR", "gCNR (0..1, higher = better)"), ("edge", "edge sharpness (Sobel, grey/px)")]:
    ch = m1[key] - m0[key]
    print(f"{'cyst_lesion':12s} {label:34s} {m0[key]:9.3f} {m1[key]:9.3f} {ch:+10.3f}")
print(f"{'cyst_lesion':12s} {'edge sharpness kept':34s} {'':9s} {100 * m1['edge'] / m0['edge']:8.1f}%")

# eps comparison on the cyst
print("\nEffect of eps (r = 4) on the cyst image:")
print(f"{'eps':>8s} {'SI':>8s} {'gCNR':>8s} {'CNR':>8s} {'edge kept':>10s}")
eps_list = [0.001, 0.002, 0.005, 0.01]
eps_res = {}
for eps in eps_list:
    o = pp.postprocess(C["img"], eps=eps)
    m = measure(o)
    eps_res[eps] = (o, m)
    print(f"{eps:8.3f} {m['SI']:8.3f} {m['gCNR']:8.3f} {m['CNR']:8.3f} {100 * m['edge'] / m0['edge']:9.1f}%")

# ---------------------------------------------------------------- figures
print("\nSaving figures:")
circle = lambda ax: ax.add_patch(plt.Circle((0, 30), 6, fill=False, ec="red", lw=0.8, ls="--"))

fig, ax = plt.subplots(1, 4, figsize=(15, 7.5))
for k, name in enumerate(["scatterers", "cyst_lesion"]):
    D = data[name]
    ext = [D["x"][0], D["x"][-1], D["z"][-1], D["z"][0]]
    for j, (im, t) in enumerate([(D["img"], "before"), (D["out"], "after guided filter")]):
        a = ax[2 * k + j]
        a.imshow(im, cmap="gray", vmin=0, vmax=1, extent=ext)
        si = D["SI"][j]
        a.set_title(f"{name}\n{t}\nSI = {si:.3f}", fontsize=10); a.set_xlabel("x (mm)")
        if name == "cyst_lesion":
            circle(a)
ax[0].set_ylabel("depth z (mm)")
fig.suptitle("Before / after despeckling (postprocess, r = 4, eps = 0.001); red dashed = cyst mask", fontsize=11)
save(fig, "B1_before_after.png", "Both input images before and after the guided filter, with speckle index.")

y0, y1 = np.searchsorted(C["z"], [22, 38])
x0, x1 = np.searchsorted(C["x"], [-8, 8])
fig, ax = plt.subplots(1, 2, figsize=(11, 5.8))
for a, im, t in [(ax[0], C["img"], "before"), (ax[1], C["out"], "after")]:
    a.imshow(im[y0:y1, x0:x1], cmap="gray", vmin=0, vmax=1, interpolation="nearest",
             extent=[C["x"][x0], C["x"][x1 - 1], C["z"][y1 - 1], C["z"][y0]])
    circle(a); a.set_xlabel("x (mm)"); a.set_ylabel("z (mm)")
    a.set_title(f"cyst zoom {t}: gCNR {C['m0' if t == 'before' else 'm1']['gCNR']:.3f}, "
                f"edge {C['m0' if t == 'before' else 'm1']['edge']:.1f}", fontsize=10)
fig.suptitle("Zoom on the cyst edge (x -8..8 mm, z 22..38 mm)", fontsize=11)
save(fig, "B2_cyst_edge_zoom.png", "Close-up of the cyst border before and after: speckle smoother, border kept.")

fig, ax = plt.subplots(1, 2, figsize=(11, 6.5))
for a, name in zip(ax, ["scatterers", "cyst_lesion"]):
    D = data[name]
    diff = D["out"] - D["img"]
    lim = np.percentile(np.abs(diff), 99)
    im = a.imshow(diff, cmap="seismic", vmin=-lim, vmax=lim, extent=[D["x"][0], D["x"][-1], D["z"][-1], D["z"][0]])
    a.set_title(f"{name}: after - before\n(mean |diff| = {np.abs(diff).mean():.3f})", fontsize=10)
    a.set_xlabel("x (mm)"); plt.colorbar(im, ax=a, fraction=0.046, label="brightness change")
ax[0].set_ylabel("z (mm)")
fig.suptitle("Difference map (after - before): red = pixel became brighter, blue = darker", fontsize=11)
save(fig, "B3_difference_map.png", "After minus before: the filter removes fine speckle grains everywhere.")

row = int(np.argmin(np.abs(C["z"] - 30)))
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.plot(C["x"], C["img"][row], color="0.6", lw=1, label="before")
ax.plot(C["x"], C["out"][row], color="tab:red", lw=1.6, label="after guided filter")
for xe in (-6, 6):
    ax.axvline(xe, color="k", ls="--", lw=0.8)
ax.set_xlabel("x (mm)"); ax.set_ylabel("brightness (0-1)"); ax.grid(alpha=0.3); ax.legend()
ax.set_title(f"Brightness profile along row z = {C['z'][row]:.2f} mm through the cyst centre (dashed = cyst edges)")
save(fig, "B4_brightness_profile.png", "One image row through the cyst: fluctuations reduced, edge step kept.")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
bins = np.linspace(0, 1, 65)
for a, name in zip(ax, ["scatterers", "cyst_lesion"]):
    D = data[name]
    a.hist(D["img"].ravel(), bins, alpha=0.55, color="0.4", label="before")
    a.hist(D["out"].ravel(), bins, alpha=0.55, color="tab:red", label="after")
    a.set_title(name); a.set_xlabel("brightness (0-1)"); a.set_ylabel("pixel count"); a.legend()
fig.suptitle("Grey-level histograms before / after: fewer extreme values (tails and the spike at 0 shrink)", fontsize=11)
save(fig, "B5_histograms.png", "Grey-level histograms before/after for both images.")

fig = plt.figure(figsize=(14, 7.5))
gs = fig.add_gridspec(2, 4)
for k, eps in enumerate(eps_list):
    a = fig.add_subplot(gs[k // 2, k % 2])
    a.imshow(eps_res[eps][0][y0:y1, x0:x1], cmap="gray", vmin=0, vmax=1,
             extent=[C["x"][x0], C["x"][x1 - 1], C["z"][y1 - 1], C["z"][y0]])
    m = eps_res[eps][1]
    a.set_title(f"eps = {eps}: SI {m['SI']:.3f}, gCNR {m['gCNR']:.3f}", fontsize=9); a.set_xticks([]); a.set_yticks([])
a = fig.add_subplot(gs[:, 2:])
er = [100 * eps_res[e][1]["edge"] / m0["edge"] for e in eps_list]
gc = [eps_res[e][1]["gCNR"] for e in eps_list]
a.plot(eps_list, er, "o-", color="tab:blue", label="edge kept (%)")
a.set_xscale("log"); a.set_xlabel("eps"); a.set_ylabel("edge kept (%)", color="tab:blue"); a.grid(alpha=0.3)
a2 = a.twinx(); a2.plot(eps_list, gc, "s--", color="tab:red", label="gCNR"); a2.set_ylabel("gCNR", color="tab:red")
a.set_title("bigger eps = more smoothing, less edge")
fig.suptitle("eps comparison on the cyst (zoom x -8..8, z 22..38 mm)", fontsize=11)
fig.tight_layout()
save(fig, "B6_eps_comparison.png", "Cyst zoom for eps 0.001/0.002/0.005/0.01 and a plot of edge kept and gCNR vs eps.")

np.savez(OUTPUT / "B_postprocessed_images.npz", cyst_lesion=C["out"].astype(np.float32),
         scatterers=data["scatterers"]["out"].astype(np.float32))
SAVED.append(("B_postprocessed_images.npz", "The two despeckled images as numbers (float32, 0-1)."))
print("  saved output/B_postprocessed_images.npz")

# ========================================================================================
banner("SUMMARY")
print(f"Cyst image: SI {C['SI'][0]:.3f} -> {C['SI'][1]:.3f}, gCNR {m0['gCNR']:.3f} -> {m1['gCNR']:.3f}, "
      f"edge kept {100 * m1['edge'] / m0['edge']:.0f} %")
print(f"Files written to output/: {len(SAVED) + 2} (including console_log.txt and console_screenshot.png)")
print(f"Total run time: {time.time() - t_start:.1f} s")

# ---------------------------------------------------------------- console log + screenshot
# ---------------------------------------------------------------- console log + screenshot
sys.stdout = REAL_STDOUT
text = LOG.getvalue()
(OUTPUT / "console_log.txt").write_text(text, encoding="utf-8")


def console_png(text, out_png, width=110):
    lines = []
    for ln in text.rstrip("\n").splitlines():
        while len(ln) > width:
            lines.append(ln[:width]); ln = "   " + ln[width:]
        lines.append(ln)
    h = 0.6 + 0.16 * len(lines)
    fig = plt.figure(figsize=(0.083 * width + 0.4, h))
    fig.patch.set_facecolor("#1e1e1e")
    fig.text(0.01, 1 - 0.28 / h, "Terminal: python3 run_team8.py", color="#9a9a9a", fontsize=9, family="monospace",
             va="center")
    for i, ln in enumerate(lines):
        fig.text(0.01, 1 - (0.55 + 0.16 * i) / h, ln, color="#e6e6e6", fontsize=8.4, family="monospace", va="top")
    fig.savefig(out_png, dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)


console_png(text, OUTPUT / "console_screenshot.png")
print("Saved output/console_log.txt and output/console_screenshot.png")
