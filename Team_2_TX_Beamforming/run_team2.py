"""
run_team2.py  -  one-command demo for Team 2: Transmit (TX) Beamforming.

What this script does (the team's own code in code/ is NOT changed):
  1. Copies code/ into a temporary working folder and puts the two input
     files from input/ into its config/ folder.
  2. Runs the team's pipeline in the order they designed it:
        python run_transmit_beamforming.py
        python visualize_transmit_beamforming.py
     (the second script calls plt.show(); here each figure is saved to a PNG
      instead of opening a window).
  3. Runs the team's tests (tests/test_beamformer.py) by importing the module
     and calling every test_* function directly (pytest is not needed).
  4. Prints a summary read from the team's own output files.
  5. Makes a few extra figures using the team's own functions (file names
     start with "extra_").
  6. Saves everything to output/, including the console log and a
     screenshot-style PNG of the console.

Run:  python3 run_team2.py      (Windows: python run_team2.py)
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
CODE = HERE / "code"
INPUT = HERE / "input"
OUT = HERE / "output"
sys.dont_write_bytecode = True


# ----------------------------------------------------------------------------
# Console: print to screen and keep a copy for output/console_log.txt
# ----------------------------------------------------------------------------
class Tee(io.TextIOBase):
    def __init__(self, stream):
        self.stream, self.buf = stream, io.StringIO()

    def write(self, s):
        self.stream.write(s); self.buf.write(s); return len(s)

    def flush(self):
        self.stream.flush()


def banner(text):
    print("\n" + "=" * 72 + f"\n{text}\n" + "=" * 72)


def run_script(cmd_args, cwd, label):
    """Run a Python command in `cwd`, show its output, stop on failure."""
    env = dict(os.environ, MPLBACKEND="Agg", PYTHONDONTWRITEBYTECODE="1")
    t0 = time.time()
    r = subprocess.run([sys.executable] + cmd_args, cwd=cwd, env=env,
                       capture_output=True, text=True)
    for line in r.stdout.rstrip().splitlines():
        print("  | " + line)
    if r.returncode != 0:
        print(r.stderr)
        raise SystemExit(f"ERROR: {label} failed (exit code {r.returncode}).")
    print(f"  ({label} finished in {time.time() - t0:.2f} s)")


# Small wrapper so the team's visualize script can run without opening windows:
# every plt.show() saves the current figure to a numbered PNG in output/.
VIS_WRAPPER = r"""
import sys, runpy, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
out_dir = sys.argv[1]
names = ["team_fig1_delay_vs_element.png", "team_fig2_position_vs_delay.png"]
count = [0]
def _save_instead_of_show(*a, **k):
    i = count[0]
    name = names[i] if i < len(names) else f"team_fig{i + 1}.png"
    plt.gcf().savefig(out_dir + "/" + name, dpi=130)
    plt.close("all")
    count[0] += 1
plt.show = _save_instead_of_show
runpy.run_path("visualize_transmit_beamforming.py", run_name="__main__")
"""

# The team's tests are plain functions; call each one and report pass/fail.
TEST_WRAPPER = r"""
import importlib, traceback
m = importlib.import_module("tests.test_beamformer")
names = sorted(n for n in dir(m) if n.startswith("test_"))
failed = 0
for n in names:
    try:
        getattr(m, n)(); print(f"PASS  {n}")
    except Exception as e:
        failed += 1; print(f"FAIL  {n}: {type(e).__name__}: {e}")
print(f"RESULT {len(names) - failed}/{len(names)} tests passed")
raise SystemExit(1 if failed else 0)
"""


def console_to_png(text, out_png, title="Terminal", width_chars=100, max_lines=90):
    """Draw the captured console text as a screenshot-style PNG."""
    lines = []
    for line in text.expandtabs(4).rstrip("\n").splitlines():
        while len(line) > width_chars:
            lines.append(line[:width_chars]); line = "  -> " + line[width_chars:]
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [f"... ({len(lines) - max_lines + 1} more lines, see console_log.txt)"]
    h = 0.62 + 0.165 * len(lines)
    fig = plt.figure(figsize=(0.083 * width_chars + 0.4, h))
    fig.patch.set_facecolor("#1e1e1e")
    fig.text(0.012, 1 - 0.28 / h, "o o o   " + title, color="#9a9a9a", fontsize=9,
             family="DejaVu Sans Mono", va="center")
    for i, ln in enumerate(lines):
        fig.text(0.012, 1 - (0.55 + 0.165 * i) / h, ln, color="#e6e6e6", fontsize=8.6,
                 family="DejaVu Sans Mono", va="top")
    fig.savefig(out_png, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


# ----------------------------------------------------------------------------
# Extra figures (made by this runner with the team's own functions/outputs)
# ----------------------------------------------------------------------------
def pulse_pair_energy(dt, f0, sigma_cycles):
    """Exact integral of p(t-a)*p(t-b) dt for the team's Gaussian pulse, dt=a-b."""
    s = sigma_cycles / (2 * np.pi * f0); w = 2 * np.pi * f0
    return 0.5 * s * np.sqrt(np.pi) * np.exp(-dt ** 2 / (4 * s ** 2)) * (np.cos(w * dt) - np.exp(-(w * s) ** 2))


def field_energy_map(x_el, delays, weights, c, f0, sigma_cycles, gx, gz):
    """Energy of the summed pulse at every grid point (x, z).

    Element n fires at delays[n]; its pulse reaches (x, z) at
    T_n = delays[n] + r_n / c. The energy of sum_n w_n p(t - T_n) is
    sum_n sum_m w_n w_m K(T_n - T_m) with K = pulse_pair_energy.
    Spreading loss and element directivity are ignored (simple picture).
    """
    X, Z = np.meshgrid(gx, gz)
    pts = np.column_stack([X.ravel(), Z.ravel()])
    E = np.empty(len(pts))
    for i in range(0, len(pts), 400):
        p = pts[i:i + 400]
        T = delays[None, :] + np.hypot(p[:, :1] - x_el[None, :], p[:, 1:]) / c
        K = pulse_pair_energy(T[:, :, None] - T[:, None, :], f0, sigma_cycles)
        E[i:i + 400] = np.einsum("n,pnm,m->p", weights, K, weights)
    return E.reshape(X.shape)


def make_extra_figures(work, pkg, beam_cfg):
    sys.path.insert(0, str(work))
    from src.beamformer import make_apodization, gaussian_pulse, calculate_tx_delays

    x = pkg["element_x_m"]; tau = pkg["tx_delays_s"]; w = pkg["tx_weights"]
    f0 = float(pkg["tx_frequency_hz"]); c = float(pkg["sound_speed_m_s"])
    xf = float(pkg["focus_x_m"]); zf = float(pkg["focus_z_m"])
    sig = float(beam_cfg.get("pulse_duration_sigma_cycles", 1.0))
    n = len(x); el = np.arange(1, n + 1)
    made, info = [], []

    # 1. Delay profile + weights actually used, plus a steering-only example
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    ax[0].plot(el, tau * 1e6, "o-", ms=2.5, color="#1f5f99")
    ax[0].set(title=f"Focusing delays (focus x={xf*1e3:.0f} mm, z={zf*1e3:.0f} mm)",
              xlabel="Element number", ylabel="Delay (us)")
    ax[0].annotate("edge elements fire first\n(delay = 0)", xy=(n, 0), xytext=(70, tau.max() * 1e6 * 0.08),
                   arrowprops=dict(arrowstyle="->"), fontsize=8)
    ax[0].annotate(f"centre fires last\n({tau.max()*1e6:.3f} us)", xy=(n / 2, tau.max() * 1e6),
                   xytext=(n / 2 - 20, tau.max() * 1e6 * 0.35), arrowprops=dict(arrowstyle="->"), fontsize=8)
    ax[1].plot(el, w, "o-", ms=2.5, color="#2a7a3a")
    ax[1].set(title=f"Apodization weights used ({beam_cfg.get('apodization')})",
              xlabel="Element number", ylabel="Weight", ylim=(-0.05, 1.1))
    for ang in (-15, 15):
        ax[2].plot(el, calculate_tx_delays(x, xf, zf, c, ang) * 1e6, label=f"steering {ang:+d} deg")
    ax[2].set(title="Example only: steering delays (team function)", xlabel="Element number", ylabel="Delay (us)")
    ax[2].legend(fontsize=8)
    for a in ax: a.grid(alpha=0.3)
    fig.suptitle("Extra figure (made by run_team2.py from the team's output and functions)", fontsize=9, color="grey")
    fig.tight_layout(); p = OUT / "extra_1_delays_and_weights.png"; fig.savefig(p, dpi=130); plt.close(fig); made.append(p)

    # 2. Apodization windows from make_apodization
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    k_wave = 2 * np.pi * f0 / c
    u_zoom = np.sin(np.radians(np.linspace(-4, 4, 1601)))
    u_wide = np.sin(np.radians(np.linspace(-60, 60, 4801)))
    for kind, col in (("rect", "#888888"), ("hann", "#1f5f99"), ("hamming", "#c77d0a")):
        wk = make_apodization(n, kind)
        ax[0].plot(el, wk, label=kind, color=col)
        # continuous-wave far-field beam pattern (array factor) of these weights
        af = np.abs(np.exp(1j * k_wave * np.outer(u_zoom, x)) @ wk)
        db = 20 * np.log10(af / af.max() + 1e-12); ang = np.degrees(np.arcsin(u_zoom))
        main = ang[db >= -6]; ic = len(db) // 2
        j = ic
        while j + 1 < len(db) and db[j + 1] <= db[j]:
            j += 1                                   # walk down the main lobe to the first null
        info.append(f"  Window {kind:<8}: -6 dB main-lobe width {main.max() - main.min():.3f} deg, "
                    f"highest side lobe {db[j:].max():.1f} dB")
        ax[1].plot(np.degrees(np.arcsin(u_zoom)), 20 * np.log10(af / af.max() + 1e-12), label=kind, color=col, lw=1)
    wh = make_apodization(n, beam_cfg.get("apodization", "hann"))
    af = np.abs(np.exp(1j * k_wave * np.outer(u_wide, x)) @ wh)
    ax[2].plot(np.degrees(np.arcsin(u_wide)), 20 * np.log10(af / af.max() + 1e-12), color="#1f5f99", lw=1)
    g_ang = np.degrees(np.arcsin(min(1.0, c / f0 / (x[1] - x[0]))))
    for sgn in (-1, 1):
        ax[2].annotate("grating lobe", xy=(sgn * g_ang, 0), xytext=(sgn * g_ang - 12, -25), fontsize=8,
                       arrowprops=dict(arrowstyle="->"))
    ax[0].set(title="make_apodization(128, kind)", xlabel="Element number", ylabel="Weight")
    ax[1].set(title=f"Beam pattern near the axis, {f0/1e6:.0f} MHz", xlabel="Angle (deg)", ylabel="Level (dB)",
              ylim=(-80, 3), xlim=(-4, 4))
    ax[2].set(title=f"Wide view, {beam_cfg.get('apodization')} weights (pitch > wavelength/2)",
              xlabel="Angle (deg)", ylabel="Level (dB)", ylim=(-80, 3), xlim=(-60, 60))
    ax[0].legend(fontsize=8); ax[1].legend(fontsize=8)
    for a in ax: a.grid(alpha=0.3)
    fig.suptitle("Extra figure (array factor, continuous wave): rect = narrow main lobe but high side lobes; "
                 "Hann/Hamming = wider main lobe, low side lobes", fontsize=9, color="grey")
    fig.tight_layout(); p = OUT / "extra_2_apodization_windows.png"; fig.savefig(p, dpi=130); plt.close(fig); made.append(p)

    # 3. The pulse: one Gaussian pulse and a few element pulses from tx_element_pulses.npz
    pul = np.load(work / "outputs" / "tx_element_pulses.npz")
    ts, ps = pul["time_s"], pul["pulses"]
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    t = np.linspace(-0.15e-6, 0.15e-6, 1200)
    g = gaussian_pulse(t, f0, sig)
    ax[0].plot(t * 1e6, g, color="#1f5f99")
    ax[0].plot(t * 1e6, np.exp(-0.5 * (t * 2 * np.pi * f0 / sig) ** 2), "--", color="grey", label="Gaussian envelope")
    ax[0].set(title=f"gaussian_pulse(t, {f0/1e6:.0f} MHz, sigma_cycles={sig:g})", xlabel="Time (us)", ylabel="Amplitude")
    ax[0].legend(fontsize=8)
    fs = 1 / (ts[1] - ts[0])
    spec = np.abs(np.fft.rfft(g, 65536)); fr = np.fft.rfftfreq(65536, t[1] - t[0])
    ax[1].plot(fr / 1e6, 20 * np.log10(spec / spec.max() + 1e-12), color="#2a7a3a")
    sdb = 20 * np.log10(spec / spec.max() + 1e-12); band = fr[sdb >= -6]
    info.append(f"  Pulse spectrum: peak at {fr[np.argmax(spec)]/1e6:.2f} MHz, "
                f"-6 dB band {band.min()/1e6:.2f} ... {band.max()/1e6:.2f} MHz")
    info.append(f"  Grating-lobe angle for this pitch at f0: asin(wavelength/pitch) = "
                f"{np.degrees(np.arcsin(min(1.0, c / f0 / (x[1] - x[0])))):.1f} deg")
    ax[1].axvspan(4, 12, color="orange", alpha=0.15, label="probe band 4-12 MHz")
    ax[1].set(title="Spectrum of the pulse", xlabel="Frequency (MHz)", ylabel="dB", xlim=(0, 25), ylim=(-60, 3))
    ax[1].legend(fontsize=8)
    for k, col in zip((7, 31, 47, 63), ("#b0413e", "#c77d0a", "#2a7a3a", "#1f5f99")):
        ax[2].plot(ts * 1e6, ps[k], color=col, lw=1, label=f"element {k+1} (delay {tau[k]*1e6:.2f} us)")
    ax[2].set(title="tx_element_pulses.npz: a few element signals", xlabel="Time (us)", ylabel="Weighted amplitude",
              xlim=(tau[7] * 1e6 - 0.3, tau.max() * 1e6 + 0.3))
    ax[2].legend(fontsize=7)
    for a in ax: a.grid(alpha=0.3)
    fig.suptitle("Extra figure (made by run_team2.py from the team's functions and output)", fontsize=9, color="grey")
    fig.tight_layout(); p = OUT / "extra_3_pulse.png"; fig.savefig(p, dpi=130); plt.close(fig); made.append(p)

    # 4. Simple 2-D transmit field map: team delays vs. no delays
    gx = np.arange(-10e-3, 10e-3 + 1e-9, 0.1e-3)
    gz = np.arange(5e-3, 70e-3 + 1e-9, 0.5e-3)
    t0 = time.time()
    E_foc = field_energy_map(x, tau, w, c, f0, sig, gx, gz)
    E_flat = field_energy_map(x, np.zeros_like(tau), w, c, f0, sig, gx, gz)
    ref = max(E_foc.max(), E_flat.max())
    fig, ax = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw=dict(width_ratios=[1, 1, 1.1]))
    for a, E, ttl in ((ax[0], E_foc, "With the team's TX delays"), (ax[1], E_flat, "All delays = 0 (no focusing)")):
        im = a.imshow(10 * np.log10(np.maximum(E, 1e-30) / ref), extent=[gx[0]*1e3, gx[-1]*1e3, gz[-1]*1e3, gz[0]*1e3],
                      cmap="inferno", vmin=-30, vmax=0, aspect="auto")
        a.plot(xf * 1e3, zf * 1e3, "c+", ms=14, mew=2)
        a.set(title=ttl, xlabel="x (mm)", ylabel="Depth z (mm)")
    fig.colorbar(im, ax=ax[:2], label="Pulse energy (dB, both maps same scale)", shrink=0.85)
    # fine 1-D profile across the beam at the focus depth (0.005 mm steps)
    lx = np.arange(-3e-3, 3e-3 + 1e-9, 0.005e-3)
    L_foc = field_energy_map(x, tau, w, c, f0, sig, lx, np.array([zf]))[0]
    L_flat = field_energy_map(x, np.zeros_like(tau), w, c, f0, sig, lx, np.array([zf]))[0]
    lref = L_foc.max()
    for L, lab, col in ((L_foc, "with TX delays", "#1f5f99"), (L_flat, "no delays", "#888888")):
        ax[2].plot(lx * 1e3, 10 * np.log10(np.maximum(L, 1e-30) / lref), label=lab, color=col)
    ax[2].axhline(-6, color="red", ls=":", lw=1, label="-6 dB")
    ax[2].set(title=f"Across the beam at z = {zf*1e3:.1f} mm (zoom)", xlabel="x (mm)",
              ylabel="dB (re. focus peak)", ylim=(-30, 2))
    ax[2].grid(alpha=0.3); ax[2].legend(fontsize=8)
    fig.suptitle("Extra figure: simple transmit-field map (sum of the delayed, weighted pulses; spreading loss ignored)",
                 fontsize=9, color="grey")
    p = OUT / "extra_4_tx_field_map.png"; fig.savefig(p, dpi=130); plt.close(fig); made.append(p)

    # numbers from the map, for the console
    ix0 = np.argmin(np.abs(gx - xf))
    axis_peak_z = gz[np.argmax(E_foc[:, ix0])]
    above = lx[L_foc / L_foc.max() >= 10 ** (-6 / 10)]
    width6 = above.max() - above.min()
    i0 = np.argmin(np.abs(lx - xf))
    gain = L_foc[i0] / L_flat[i0]
    fmap = dict(time=time.time() - t0, npts=E_foc.size * 2 + 2 * len(lx), axis_peak_z=axis_peak_z, width6=width6,
                gain_db=10 * np.log10(gain), grid_dz=gz[1] - gz[0], grid_dx=gx[1] - gx[0])
    return made, fmap, info


def main():
    t_start = time.time()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    tee = Tee(sys.stdout); sys.stdout = tee
    ok_tests = None
    try:
        banner("TEAM 2 - TRANSMIT (TX) BEAMFORMING  |  NITK-UsoundSim")
        print(f"Python      : {sys.version.split()[0]}  ({sys.executable})")
        print(f"Team folder : {HERE}")

        # --- Step 0: working copy -------------------------------------------------
        banner("STEP 0  Prepare a working copy of the team's code")
        tmp = tempfile.TemporaryDirectory(prefix="team2_work_")
        work = Path(tmp.name) / "Usound"
        shutil.copytree(CODE, work, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
        shutil.rmtree(work / "outputs", ignore_errors=True)   # start clean: all outputs are made fresh
        for f in ("transducer_interface.json", "beamforming.json"):
            shutil.copy2(INPUT / f, work / "config" / f)
            print(f"  input/{f}  ->  config/{f}")
        t_cfg = json.loads((INPUT / "transducer_interface.json").read_text())
        b_cfg = json.loads((INPUT / "beamforming.json").read_text())
        print("  Probe input      :", ", ".join(f"{k}={v}" for k, v in t_cfg.items() if k != "notes"))
        print("  Beamformer input :", ", ".join(f"{k}={v}" for k, v in b_cfg.items()))

        # --- Step 1 ------------------------------------------------------------------
        banner("STEP 1  Team script: python run_transmit_beamforming.py")
        run_script(["run_transmit_beamforming.py"], work, "run_transmit_beamforming.py")
        print("  (the 'Handoff' path above is the temporary working copy; the files are copied to output/)")

        # --- Step 2 ------------------------------------------------------------------
        banner("STEP 2  Team script: python visualize_transmit_beamforming.py")
        print("  (plt.show() is replaced by 'save to PNG', so no windows open)")
        run_script(["-c", VIS_WRAPPER, str(OUT)], work, "visualize_transmit_beamforming.py")

        # --- Step 3 ------------------------------------------------------------------
        banner("STEP 3  Team tests: tests/test_beamformer.py (each test_* called directly)")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, "-c", TEST_WRAPPER], cwd=work, env=env, capture_output=True, text=True)
        for line in (r.stdout + r.stderr).rstrip().splitlines():
            print("  | " + line)
        ok_tests = r.returncode == 0

        # --- Collect outputs ---------------------------------------------------------
        for f in sorted((work / "outputs").iterdir()):
            shutil.copy2(f, OUT / f.name)

        # --- Step 4: summary from the team's own files ------------------------------
        banner("STEP 4  Summary read from the team's output files")
        pkg = dict(np.load(OUT / "tx_beamforming_package.npz"))
        summ = json.loads((OUT / "tx_beamforming_summary.json").read_text())
        pul = np.load(OUT / "tx_element_pulses.npz")
        x, tau, w = pkg["element_x_m"], pkg["tx_delays_s"], pkg["tx_weights"]
        f0, c = float(pkg["tx_frequency_hz"]), float(pkg["sound_speed_m_s"])
        lam = c / f0
        first = np.flatnonzero(np.isclose(tau, tau.min())) + 1
        last = np.flatnonzero(np.isclose(tau, tau.max())) + 1
        rows = [
            ("Probe", summ["probe"]),
            ("Number of elements", f"{len(x)}"),
            ("Pitch", f"{summ['pitch_m']*1e3:.3f} mm"),
            ("Element x range", f"{x.min()*1e3:.2f} mm ... {x.max()*1e3:.2f} mm"),
            ("Aperture (first to last centre)", f"{(x.max()-x.min())*1e3:.2f} mm"),
            ("Centre frequency f0", f"{f0/1e6:.2f} MHz"),
            ("Sound speed c", f"{c:.0f} m/s"),
            ("Wavelength c/f0", f"{lam*1e3:.4f} mm  (pitch = {summ['pitch_m']/lam:.2f} wavelengths)"),
            ("Focus (x, z)", f"({float(pkg['focus_x_m'])*1e3:.1f} mm, {float(pkg['focus_z_m'])*1e3:.1f} mm)"),
            ("Steering angle", f"{float(pkg['steering_angle_deg']):.1f} deg"),
            ("F-number (focus depth / aperture)", f"{float(pkg['focus_z_m'])/(x.max()-x.min()):.2f}"),
            ("Delay min / max", f"{tau.min()*1e6:.4f} us / {tau.max()*1e6:.4f} us"),
            ("Elements that fire first", ", ".join(map(str, first))),
            ("Elements that fire last", ", ".join(map(str, last))),
            ("Apodization", f"{b_cfg.get('apodization')}  (weights min {w.min():.4f}, max {w.max():.4f}, "
                            f"element 1 = {w[0]:.4f}, element 64 = {w[63]:.4f})"),
            ("Pulse file", f"pulses {pul['pulses'].shape}, time samples {pul['time_s'].shape[0]}, "
                           f"fs = {1/(pul['time_s'][1]-pul['time_s'][0])/1e6:.0f} MHz, "
                           f"t = {pul['time_s'][0]*1e6:.3f} ... {pul['time_s'][-1]*1e6:.3f} us"),
        ]
        for k, v in rows:
            print(f"  {k:<34}: {v}")
        print("  Hand-off package keys (tx_beamforming_package.npz):")
        for k, v in pkg.items():
            print(f"      {k:<20} shape {str(np.shape(v)):<8} dtype {v.dtype}")
        sys.path.insert(0, str(work))
        from src.acoustic_handoff import load_tx_package
        load_tx_package(OUT / "tx_beamforming_package.npz")
        print("  load_tx_package() check (the next team's loader): OK - all required fields, shape (128,)")

        # --- Step 5: extra figures ---------------------------------------------------
        banner("STEP 5  Extra figures (made by this runner with the team's functions)")
        made, fmap, info = make_extra_figures(work, pkg, b_cfg)
        print("\n".join(info))
        for p in made:
            print(f"  saved {p.name}")
        print(f"  Field map: {fmap['npts']} grid points in {fmap['time']:.1f} s "
              f"(grid step x {fmap['grid_dx']*1e3:.1f} mm, z {fmap['grid_dz']*1e3:.1f} mm)")
        print(f"  Field map: strongest point on the centre line at z = {fmap['axis_peak_z']*1e3:.1f} mm "
              f"(focus set to {float(pkg['focus_z_m'])*1e3:.1f} mm)")
        print(f"  Field map: -6 dB beam width at focus depth = {fmap['width6']*1e3:.2f} mm")
        print(f"  Field map: energy at the focus is {fmap['gain_db']:.1f} dB higher than with no delays")
        tmp.cleanup()

        # --- Done ----------------------------------------------------------------------
        banner("DONE")
        print(f"  Tests: {'ALL PASSED' if ok_tests else 'SOME FAILED (see STEP 3)'}")
        print(f"  Output folder: {OUT}")
        for f in sorted(OUT.iterdir()):
            print(f"      {f.name}")
        print("      console_log.txt")
        print("      console_screenshot.png")
        print(f"  Total run time: {time.time() - t_start:.1f} s")
    except SystemExit as e:
        print(e); raise
    except Exception:
        traceback.print_exc(file=sys.stdout); raise
    finally:
        sys.stdout = tee.stream
        text = tee.buf.getvalue()
        (OUT / "console_log.txt").write_text(text, encoding="utf-8")
        try:
            console_to_png(text, OUT / "console_screenshot.png", title="python3 run_team2.py")
        except Exception as e:  # never hide the real result because of the picture
            print("Could not draw console screenshot:", e)
    return 0 if ok_tests else 1


if __name__ == "__main__":
    sys.exit(main())
