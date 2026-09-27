"""
run_team5.py - one-command demo of Team 5: Receive (RX) Beamforming (delay-and-sum)

Run from this folder:
    python3 run_team5.py        (macOS / Linux)
    python  run_team5.py        (Windows)

What it does
  Step 1  runs Team 5's verification tests (code/verify_beamformer.py)
  Step 2  loads the two sample RF inputs from input/ and plots the raw RF
  Step 3  shows the delay idea for the point target at (0, 20) mm
  Step 4  beamforms both inputs with das_beamform() and saves the results
  Step 5  measures target positions and -6 dB resolution at (0, 20) mm
  Step 6  compares receive apodization windows (rect / hamming / hann) and apertures (F#)
Everything is saved to output/ (plots, beamformed data, console log, console screenshot).
"""

import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CODE = HERE / "code"
INPUT = HERE / "input"
OUTPUT = HERE / "output"
OUTPUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CODE))  # Team 5's code + local config.py (config adds code/support)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy.signal import hilbert  # noqa: E402

import config  # noqa: E402  (code/config.py)
from receive_beamforming import das_beamform  # noqa: E402  (Team 5's beamformer)


# ----------------------------------------------------------------------
# Console log: everything printed goes to the screen AND to output/console_log.txt
# ----------------------------------------------------------------------
class Tee:
    def __init__(self, stream):
        self.stream, self.lines = stream, []

    def write(self, s):
        self.stream.write(s)
        self.lines.append(s)

    def flush(self):
        self.stream.flush()

    def text(self):
        return "".join(self.lines)


LOG = Tee(sys.stdout)
sys.stdout = LOG
T_START = time.time()


def banner(text):
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78)


def save(fig, name):
    path = OUTPUT / name
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved output/{name}")


def console_png(text, out_png, title="Terminal", width_chars=100, max_lines=160):
    """Render the captured console text as a screenshot-style PNG (dark background)."""
    lines = []
    for line in text.expandtabs(4).rstrip("\n").splitlines():
        while len(line) > width_chars:
            lines.append(line[:width_chars])
            line = "  -> " + line[width_chars:]
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [f"... ({len(lines) - max_lines + 1} more lines)"]
    h = 0.62 + 0.165 * len(lines)
    fig = plt.figure(figsize=(0.083 * width_chars + 0.4, h))
    fig.patch.set_facecolor("#1e1e1e")
    fig.text(0.012, 1 - 0.28 / h, "o o o   " + title, color="#9a9a9a", fontsize=9, family="DejaVu Sans Mono",
             va="center")
    for i, ln in enumerate(lines):
        fig.text(0.012, 1 - (0.55 + 0.165 * i) / h, ln, color="#e6e6e6", fontsize=8.6, family="DejaVu Sans Mono",
                 va="top")
    fig.savefig(out_png, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def envelope_db(bf, ref=None):
    """Envelope (Hilbert, along depth) in dB. FOR DISPLAY / MEASUREMENT ONLY (next team's job)."""
    env = np.abs(hilbert(bf, axis=0))
    ref = env.max() if ref is None else ref
    return env, 20 * np.log10(np.maximum(env / ref, 1e-12))


def width_at(profile, axis, i_peak, level=0.5):
    """Full width where profile >= level * peak, with linear interpolation at both crossings."""
    p = profile / profile[i_peak]
    i = i_peak
    while i > 0 and p[i] >= level:
        i -= 1
    left = axis[i] + (level - p[i]) * (axis[i + 1] - axis[i]) / (p[i + 1] - p[i])
    j = i_peak
    while j < len(p) - 1 and p[j] >= level:
        j += 1
    right = axis[j - 1] + (p[j - 1] - level) * (axis[j] - axis[j - 1]) / (p[j - 1] - p[j])
    return right - left


# ----------------------------------------------------------------------
banner("NITK-UsoundSim  |  Team 5: Receive (RX) Beamforming, delay-and-sum")
print(f"Probe   : {config.PROBE_NAME}")
print(f"          {config.N_ELEMENTS} elements, pitch {config.PITCH*1e3:.2f} mm, f0 {config.F0/1e6:.0f} MHz, "
      f"fs {config.FS/1e6:.0f} MHz, c {config.C:.0f} m/s")
print(f"Lines   : {config.N_SCANLINES} scan lines, x = {config.SCANLINE_X_MIN*1e3:+.0f} .. "
      f"{config.SCANLINE_X_MAX*1e3:+.0f} mm")
print(f"Receive : apodization '{config.RX_APODIZATION}', F-number {config.RX_F_NUMBER}")
print(f"Python  : {sys.version.split()[0]}   numpy {np.__version__}")
import receive_beamforming  # noqa: E402

print(f"Beamformer loaded from: {Path(receive_beamforming.__file__).relative_to(HERE)}")

# ----------------------------------------------------------------------
banner("STEP 1  Team 5 verification tests (code/verify_beamformer.py)")
print("Test RF is generated fresh by mock_data.py -> support/tissue_phantoms.simulate_rf ...\n")
t0 = time.time()
res = subprocess.run([sys.executable, "verify_beamformer.py"], cwd=CODE, capture_output=True, text=True)
out = res.stdout.strip("\n")
print(out)
if res.returncode != 0:
    print(res.stderr)
    print("  !! verify_beamformer.py exited with an error (see above)")
n_pass, n_fail = out.count("[PASS]"), out.count("[FAIL]")
test_blocks = out.split("--- Test ")[1:]
n_tests_passed = sum(1 for b in test_blocks if "[PASS]" in b and "[FAIL]" not in b)
print(f"\nSummary: {n_tests_passed}/{len(test_blocks)} tests passed "
      f"({n_pass} PASS checks, {n_fail} FAIL checks)   [{time.time()-t0:.1f} s]")

# ----------------------------------------------------------------------
banner("STEP 2  Load the sample inputs (input/*.npz)")
inputs = {}
for name, file, desc in [
    ("point_targets", "point_targets_rf.npz", "3 point targets at (-5,10), (0,20), (+5,30) mm"),
    ("cyst", "cyst_rf.npz", "speckle tissue with an anechoic cyst, centre (0,30) mm, radius 6 mm"),
]:
    d = np.load(INPUT / file)
    rf, t_axis = d["rf"].astype(float), d["t_axis"]
    inputs[name] = (rf, t_axis)
    print(f"{file:22s}: {desc}")
    print(f"{'':22s}  rf {rf.shape} (elements x time samples), |rf| max {np.abs(rf).max():.3g}")
    print(f"{'':22s}  t_axis {t_axis[0]*1e6:+.3f} .. {t_axis[-1]*1e6:.3f} us, step {np.diff(t_axis).mean()*1e9:.1f} ns "
          f"(= 1/fs)")

element_x = config.get_element_positions()
x_lines = config.get_scanline_positions()


def plot_raw(name, title, zoom_t, trace_el=64):
    rf, t_axis = inputs[name]
    t_us = t_axis * 1e6
    lim = np.abs(rf).max()
    fig, ax = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.1, 1, 1.3]})
    ax[0].imshow(rf.T, aspect="auto", cmap="gray", vmin=-lim / 3, vmax=lim / 3,
                 extent=[0.5, rf.shape[0] + 0.5, t_us[-1], t_us[0]], interpolation="none")
    ax[0].set(xlabel="element number (1..128)", ylabel="time t [us]", title="Full raw RF (one broadcast shot)")
    ax[0].add_patch(plt.Rectangle((trace_el - 12, zoom_t[0]), 24, zoom_t[1] - zoom_t[0], fill=False, ec="r", lw=1.5))
    it = (t_us >= zoom_t[0]) & (t_us <= zoom_t[1])
    sub = rf[trace_el - 13:trace_el + 11, it]
    ax[1].imshow(sub.T, aspect="auto", cmap="seismic", vmin=-np.abs(sub).max(), vmax=np.abs(sub).max(),
                 extent=[trace_el - 12.5, trace_el + 11.5, t_us[it][-1], t_us[it][0]], interpolation="none")
    ax[1].set(xlabel="element number", ylabel="time t [us]", title="Zoom (red box): each pixel = one sample")
    ax[2].plot(t_us[it], rf[trace_el - 1, it], "k-", lw=0.9, marker=".", ms=3)
    ax[2].set(xlabel="time t [us]", ylabel="amplitude", title=f"One channel: element {trace_el} (dots = samples)")
    ax[2].grid(alpha=0.3)
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    return fig


print()
save(plot_raw("point_targets", "INPUT: raw RF of the point-target phantom (before beamforming)", (25.4, 27.4)),
     "01_input_point_targets_raw_rf.png")
save(plot_raw("cyst", "INPUT: raw RF of the cyst phantom (speckle; before beamforming)", (38.0, 40.0)),
     "02_input_cyst_raw_rf.png")

# ----------------------------------------------------------------------
banner("STEP 3  The delay idea for the target at (0, 20) mm")
rf, t_axis = inputs["point_targets"]
c = config.C
xl, zt = 0.0, 0.020
tau_tx = np.hypot(xl - element_x, zt).min() / c
tau_rx = np.hypot(xl - element_x, zt) / c
arrival = tau_tx + tau_rx
print(f"tau_TX at (0,20) mm = {tau_tx*1e6:.3f} us (nearest element fires first, broadcast)")
print(f"tau_TX + tau_RX: centre element {arrival[63]*1e6:.3f} us, edge element 1 {arrival[0]*1e6:.3f} us")
print(f"  -> the echo reaches the edge element {(arrival[0]-arrival[63])*1e6:.2f} us later than the centre")
z_win = np.arange(0.0185, 0.0215, config.DZ)
aligned = np.zeros((element_x.size, z_win.size))
for m in range(element_x.size):
    tt = np.hypot(xl - element_x, z_win[:, None]).min(axis=1) / c + np.hypot(xl - element_x[m], z_win) / c
    aligned[m] = np.interp(tt, t_axis, rf[m], left=0.0, right=0.0)
line_f, z_axis = das_beamform(rf, element_x, [xl], config, t_axis=t_axis)
line_u, _ = das_beamform(rf, element_x, [xl], config, t_axis=t_axis, apply_focus=False)
print(f"peak |RF| on line x=0 near 20 mm: with RX delays {np.abs(line_f[:, 0]).max():.3f}, "
      f"without per-element delays {np.abs(line_u[:, 0]).max():.3f}")

t_us = t_axis * 1e6
it = (t_us > 24.5) & (t_us < 32.5)
fig, ax = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1, 1, 1.1]})
lim = np.abs(rf[:, it]).max() / 2
ax[0].imshow(rf[:, it].T, aspect="auto", cmap="seismic", vmin=-lim, vmax=lim, interpolation="none",
             extent=[0.5, 128.5, t_us[it][-1], t_us[it][0]])
ax[0].plot(np.arange(1, 129), arrival * 1e6, "k--", lw=1, label="tau_TX + tau_RX,m")
ax[0].set(xlabel="element number", ylabel="time t [us]", title="BEFORE delays: echo is a curve")
ax[0].legend(loc="lower center", fontsize=8)
lim2 = np.abs(aligned).max() / 2
ax[1].imshow(aligned.T, aspect="auto", cmap="seismic", vmin=-lim2, vmax=lim2, interpolation="none",
             extent=[0.5, 128.5, z_win[-1] * 1e3, z_win[0] * 1e3])
ax[1].axhline(20, color="k", ls="--", lw=0.8)
ax[1].set(xlabel="element number", ylabel="depth z [mm]", title="AFTER delays: echo is a straight line")
zz = (z_axis > 0.0185) & (z_axis < 0.0215)
ax[2].plot(z_axis[zz] * 1e3, line_f[zz, 0], "b-", lw=1.2, label="with RX delays (focused)")
ax[2].plot(z_axis[zz] * 1e3, line_u[zz, 0], "r-", lw=1.0, label="no per-element delay (apply_focus=False)")
ax[2].set(xlabel="depth z [mm]", ylabel="beamformed RF", title="SUM over elements, scan line x = 0")
ax[2].legend(fontsize=8)
ax[2].grid(alpha=0.3)
fig.suptitle("Delay-and-sum for the point target at (0, 20) mm (elements outside the F#=1 aperture get weight 0 "
             "in the sum)", fontsize=11)
fig.tight_layout()
save(fig, "03_delay_alignment_0_20mm.png")

# ----------------------------------------------------------------------
banner("STEP 4  Beamform both inputs with das_beamform() (hann, F# = 1, 256 lines)")
results = {}
for name in ("point_targets", "cyst"):
    rf, t_axis = inputs[name]
    t0 = time.time()
    bf, z_axis = das_beamform(rf, element_x, x_lines, config, t_axis=t_axis)
    results[name] = bf
    print(f"{name:14s}: output {bf.shape} (depths x lines), z {z_axis[0]*1e3:.0f}..{z_axis[-1]*1e3:.0f} mm "
          f"step {config.DZ*1e3:.4f} mm, {time.time()-t0:.1f} s")
    np.savez_compressed(OUTPUT / f"beamformed_{name}.npz", beamformed=bf.astype(np.float32), z_axis=z_axis,
                        x_lines=x_lines)
    print(f"{'':14s}  saved output/beamformed_{name}.npz (Team 5's output for the next stage)")

ext = [x_lines[0] * 1e3, x_lines[-1] * 1e3, 40, 0]
zshow = z_axis <= 0.040 + 1e-9
for k, (name, label) in enumerate([("point_targets", "point targets"), ("cyst", "cyst phantom")]):
    bf = results[name]
    # colour scale: points clipped at 1/3 of the peak so weaker echoes show; speckle at its 99.5th percentile
    lim = np.abs(bf[zshow]).max() / 3 if name == "point_targets" else np.percentile(np.abs(bf[zshow]), 99.5)
    fig, ax = plt.subplots(1, 2, figsize=(12, 7), gridspec_kw={"width_ratios": [1, 1]})
    # overview: red/blue for the sparse point targets; grey for dense speckle (red/blue would blur to purple)
    ax[0].imshow(bf[zshow], cmap="seismic" if name == "point_targets" else "gray", vmin=-lim, vmax=lim, extent=ext,
                 aspect="equal", interpolation="none")
    ax[0].set(xlabel="lateral x [mm]", ylabel="depth z [mm]", title=f"Beamformed RF, {label} (0-40 mm shown)")
    if name == "point_targets":
        mz = np.abs(z_axis - 0.020) < 0.0012   # zoom around the (0, 20) mm target
    else:
        mz = np.abs(z_axis - 0.0235) < 0.0012  # zoom into speckle above the cyst
    mx = np.abs(x_lines) < 0.0012
    sub = bf[np.ix_(mz, mx)]
    ax[1].imshow(sub, cmap="seismic", vmin=-np.abs(sub).max(), vmax=np.abs(sub).max(), interpolation="none",
                 extent=[x_lines[mx][0] * 1e3, x_lines[mx][-1] * 1e3, z_axis[mz][-1] * 1e3, z_axis[mz][0] * 1e3],
                 aspect="auto")
    ax[1].set(xlabel="lateral x [mm]", ylabel="depth z [mm]",
              title="Zoom: RF still oscillates along depth (not an envelope)")
    ax[0].add_patch(plt.Rectangle((x_lines[mx][0] * 1e3, z_axis[mz][0] * 1e3), (x_lines[mx][-1] - x_lines[mx][0]) * 1e3,
                                  (z_axis[mz][-1] - z_axis[mz][0]) * 1e3, fill=False, ec="k", lw=1.2))
    fig.suptitle(f"OUTPUT of Team 5: beamformed RF, {label} (signed RF: red/white = +, blue/black = -)",
                 fontsize=12)
    fig.tight_layout()
    save(fig, f"{4 + 2*k:02d}_beamformed_rf_{name}.png")

    env, db = envelope_db(bf)
    fig, ax = plt.subplots(figsize=(6.2, 8))
    im = ax.imshow(db[zshow], cmap="gray", vmin=-50, vmax=0, extent=ext, aspect="equal", interpolation="none")
    ax.set(xlabel="lateral x [mm]", ylabel="depth z [mm]",
           title=f"{label}: display image (50 dB)\nFOR DISPLAY ONLY: envelope + log are the next team's job")
    if name == "point_targets":
        for (tx_, tz_) in [(-5, 10), (0, 20), (5, 30)]:
            ax.plot(tx_, tz_, "o", mfc="none", mec="c", ms=14, mew=1)
    else:
        th = np.linspace(0, 2 * np.pi, 200)
        ax.plot(6 * np.cos(th), 30 + 6 * np.sin(th), "c--", lw=0.8)
    plt.colorbar(im, ax=ax, label="dB (0 = brightest)", shrink=0.7)
    fig.tight_layout()
    save(fig, f"{5 + 2*k:02d}_display_{name}.png")

# ----------------------------------------------------------------------
banner("STEP 5  Measurements on the beamformed point-target image")
bf = results["point_targets"]
env, _ = envelope_db(bf)
print("(peaks are taken from the envelope of the beamformed RF;")
print(f" grid step dz = {config.DZ*1e3:.4f} mm, dx = {np.diff(x_lines).mean()*1e3:.4f} mm)")
print(f"{'true (x, z) [mm]':>18s} | {'measured (x, z) [mm]':>21s} | {'error x, z [mm]':>16s} | peak level")
peak_ref = env.max()
for tx_, tz_ in [(-5, 10), (0, 20), (5, 30)]:
    m = (np.abs(z_axis[:, None] * 1e3 - tz_) <= 1.5) & (np.abs(x_lines[None, :] * 1e3 - tx_) <= 1.5)
    e = np.where(m, env, 0)
    iz, il = np.unravel_index(np.argmax(e), e.shape)
    mx_, mz_ = x_lines[il] * 1e3, z_axis[iz] * 1e3
    print(f"{f'({tx_:+.0f}, {tz_:.0f})':>18s} | {f'({mx_:+.3f}, {mz_:.3f})':>21s} | "
          f"{f'{mx_-tx_:+.3f}, {mz_-tz_:+.3f}':>16s} | {20*np.log10(env[iz, il]/peak_ref):6.1f} dB")

m = (np.abs(z_axis[:, None] - 0.020) <= 0.0015) & (np.abs(x_lines[None, :]) <= 0.0015)
iz, il = np.unravel_index(np.argmax(np.where(m, env, 0)), env.shape)
ax_w = width_at(env[:, il], z_axis, iz) * 1e3
lat_w = width_at(env[iz, :], x_lines, il) * 1e3
print(f"\n-6 dB resolution at the (0, 20) mm target (peak at x={x_lines[il]*1e3:+.3f}, z={z_axis[iz]*1e3:.3f} mm):")
print(f"  axial   width (along depth) : {ax_w:.3f} mm")
print(f"  lateral width (across lines): {lat_w:.3f} mm")
print(f"  (wavelength = {config.LAMBDA*1e3:.4f} mm; lateral line spacing {np.diff(x_lines).mean()*1e3:.4f} mm)")

fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
za = (z_axis > z_axis[iz] - 0.001) & (z_axis < z_axis[iz] + 0.001)
ax[0].plot(z_axis[za] * 1e3, bf[za, il] / env[iz, il], color="0.6", lw=0.9, label="beamformed RF")
ax[0].plot(z_axis[za] * 1e3, env[za, il] / env[iz, il], "b-", lw=1.5, label="envelope")
ax[0].axhline(0.5, color="r", ls="--", lw=0.8, label="-6 dB (half amplitude)")
ax[0].set(xlabel="depth z [mm]", ylabel="normalised amplitude", title=f"Axial profile: -6 dB width {ax_w:.3f} mm")
ax[0].legend(fontsize=8)
ax[0].grid(alpha=0.3)
xa = np.abs(x_lines) < 0.002
ax[1].plot(x_lines[xa] * 1e3, env[iz, xa] / env[iz, il], "b.-", lw=1.5, label="envelope at peak depth")
ax[1].axhline(0.5, color="r", ls="--", lw=0.8, label="-6 dB (half amplitude)")
ax[1].set(xlabel="lateral x [mm]", ylabel="normalised amplitude",
          title=f"Lateral profile: -6 dB width {lat_w:.3f} mm")
ax[1].legend(fontsize=8)
ax[1].grid(alpha=0.3)
fig.suptitle("Resolution at the point target (0, 20) mm", fontsize=12)
fig.tight_layout()
save(fig, "08_resolution_profiles_0_20mm.png")

bfc = results["cyst"]
envc = np.abs(hilbert(bfc, axis=0))
R = np.hypot(x_lines[None, :] - 0.0, z_axis[:, None] - 0.030)
inside = R < 0.004
ring = (R > 0.0075) & (R < 0.0105) & (z_axis[:, None] < 0.040)
ratio = 20 * np.log10(envc[inside].mean() / envc[ring].mean())
print(f"\nCyst image: mean envelope inside r < 4 mm of (0,30) mm = {ratio:.1f} dB")
print("  relative to the surrounding tissue ring (r = 7.5-10.5 mm)")

# ----------------------------------------------------------------------
banner("STEP 6  Apodization / aperture comparison at the (0, 20) mm target")
rf, t_axis = inputs["point_targets"]
cases = [("rect", "config"), ("hamming", "config"), ("hann", "config"), ("hann", 2.0), ("hann", None)]
zwin = np.abs(z_axis - 0.020) <= 0.001
xwin = np.abs(x_lines) <= 0.005
print("lateral width: -6 dB width across lines at the peak depth")
print("highest side lobe: max over depth 19-21 mm of the envelope, outside the main lobe, |x| <= 5 mm")
print("streak: brightest point right of the (-5,10) mm target (x > 1 mm, z 9.5-16 mm),")
print("        in dB relative to the image maximum")
print(f"{'window':>9s} {'aperture':>16s} | {'lateral -6 dB':>13s} | {'highest side lobe':>17s} | {'streak':>8s}")
streak_zone = (z_axis[:, None] > 0.0095) & (z_axis[:, None] < 0.016) & (x_lines[None, :] > 0.001)
profiles = []
for apod, fnum in cases:
    bf_a, _ = das_beamform(rf, element_x, x_lines, config, t_axis=t_axis, apodization=apod, f_number=fnum)
    env_a = np.abs(hilbert(bf_a, axis=0))
    mm = zwin[:, None] & (np.abs(x_lines[None, :]) <= 0.0015)
    iz_a, il_a = np.unravel_index(np.argmax(np.where(mm, env_a, 0)), env_a.shape)
    w = width_at(env_a[iz_a, :], x_lines, il_a) * 1e3
    proj = env_a[zwin].max(axis=0)
    proj_db = 20 * np.log10(proj / env_a[iz_a, il_a])
    # main lobe: walk out from the peak while the projection keeps falling
    a = il_a
    while a > 0 and proj[a - 1] < proj[a]:
        a -= 1
    b = il_a
    while b < len(proj) - 1 and proj[b + 1] < proj[b]:
        b += 1
    outside = xwin.copy()
    outside[a:b + 1] = False
    sl = proj_db[outside].max()
    streak = 20 * np.log10(np.where(streak_zone, env_a, 0).max() / env_a.max())
    label = {"config": "F# = 1 (dynamic)", 2.0: "F# = 2 (dynamic)", None: "full, fixed"}[fnum]
    print(f"{apod:>9s} {label:>16s} | {w:10.3f} mm | {sl:14.1f} dB | {streak:5.1f} dB")
    profiles.append((f"{apod}, {label}", x_lines, proj_db))

fig, ax = plt.subplots(1, 2, figsize=(13, 4.4), gridspec_kw={"width_ratios": [1, 1.6]})
u = np.linspace(-1, 1, 201)
for nm, f in [("rect", lambda u: np.ones_like(u)), ("hamming", lambda u: 0.54 + 0.46 * np.cos(np.pi * u)),
              ("hann", lambda u: np.cos(np.pi * u / 2) ** 2)]:
    ax[0].plot(u, f(np.abs(u)), lw=1.5, label=nm)
ax[0].set(xlabel="(x_m - x_l) / a(z)   (position inside the receive aperture)", ylabel="weight w",
          title="Receive apodization windows")
ax[0].legend()
ax[0].grid(alpha=0.3)
for (lab, xx, pdb), st in zip(profiles, ["-", "-", "-", "--", ":"]):
    ax[1].plot(xx * 1e3, pdb, st, lw=1.2, label=lab)
ax[1].set(xlim=(-5, 5), ylim=(-80, 3), xlabel="lateral x [mm]", ylabel="dB",
          title="Lateral profile at (0, 20) mm (max over depth 19-21 mm)")
ax[1].legend(fontsize=8)
ax[1].grid(alpha=0.3)
fig.tight_layout()
save(fig, "09_apodization_comparison.png")

# ----------------------------------------------------------------------
banner("DONE")
print(f"Verification tests: {n_tests_passed}/{len(test_blocks)} passed")
print(f"Total run time: {time.time()-T_START:.1f} s")
print("All outputs are in: output/  (9 plots + console_screenshot.png, 2 beamformed .npz, console_log.txt)")
text = LOG.text()
(OUTPUT / "console_log.txt").write_text(text)
console_png(text, OUTPUT / "console_screenshot.png", title="python3 run_team5.py")
sys.stdout = LOG.stream
print("  saved output/console_log.txt and output/console_screenshot.png")
