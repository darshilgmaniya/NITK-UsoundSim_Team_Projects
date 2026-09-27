"""Team 4 (Tissue Interaction) - one-command demo runner.

Run from this folder:
    python3 run_team4.py        (macOS / Linux)
    python  run_team4.py        (Windows)

What it does (the team's original code in code/ is NOT changed, only called):
  Step 1  runs the team's validate_phantom.py and collects its 4 plots
  Step 2  runs the team's 13 unit tests (without needing pytest)
  Step 3  demo: one 8 MHz incident pulse -> tissue_interaction() -> reflected pulse
          for several scatterers, plus reflection coefficients for example impedances
  Step 4  generates liver phantoms (background + 4 lesion types) and plots them
  Step 5  small 1-D speckle illustration (many scatterer echoes added together)
Everything is written to the output/ folder; sample inputs are written to input/.
"""
import csv
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback
import types
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

sys.dont_write_bytecode = True  # keep code/ clean (no __pycache__)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.signal import hilbert  # noqa: E402

HERE = Path(__file__).resolve().parent
CODE = HERE / "code"
INP = HERE / "input"
OUT = HERE / "output"
INP.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CODE))

from phantom import LesionProperties, PhantomConfig, generate_liver_phantom  # noqa: E402
from tissue_interaction import (  # noqa: E402
    interaction_gain, pressure_reflection_coefficient, tissue_interaction,
)


# ---------------------------------------------------------------- console log
class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)

    def flush(self):
        for st in self.streams:
            st.flush()


LOG_PATH = OUT / "console_log.txt"
_log = open(LOG_PATH, "w", encoding="utf-8")
_real_stdout = sys.stdout
sys.stdout = Tee(_real_stdout, _log)


def banner(text):
    print()
    print("=" * 78)
    print(text)
    print("=" * 78)


def save_console_png(text, out_png, title="Terminal - python3 run_team4.py", width_chars=100):
    """Save the console text as a screenshot-style PNG (dark terminal look)."""
    lines = []
    for line in text.rstrip("\n").splitlines():
        while len(line) > width_chars:
            lines.append(line[:width_chars]); line = "  -> " + line[width_chars:]
        lines.append(line)
    h = 0.62 + 0.165 * len(lines)
    fig = plt.figure(figsize=(0.083 * width_chars + 0.4, h))
    fig.patch.set_facecolor("#1e1e1e")
    fig.text(0.012, 1 - 0.28 / h, "o o o   " + title, color="#9a9a9a", fontsize=9, family="DejaVu Sans Mono", va="center")
    for i, ln in enumerate(lines):
        fig.text(0.012, 1 - (0.55 + 0.165 * i) / h, ln, color="#e6e6e6", fontsize=8.6,
                 family="DejaVu Sans Mono", va="top")
    fig.savefig(out_png, dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)


t_start = time.time()
banner("NITK-UsoundSim  |  Team 4: Tissue Interaction  |  demo run")
print(f"Python {sys.version.split()[0]}  numpy {np.__version__}  matplotlib {matplotlib.__version__}")
print(f"Running in folder: {HERE}")
print("Team code: code/    Sample inputs: input/    Results: output/")

# ============================================================ STEP 1
banner("STEP 1: run the team's validate_phantom.py (original script, unchanged)")
env = dict(os.environ, MPLBACKEND="Agg", PYTHONDONTWRITEBYTECODE="1")
# validate_phantom.py writes into ./validation_plots relative to the working
# folder, so we run it with output/ as working folder -> output/validation_plots/
proc = subprocess.run([sys.executable, str(CODE / "validate_phantom.py")], cwd=str(OUT), env=env,
                      capture_output=True, text=True)
print("[validate_phantom.py says]")
for line in proc.stdout.strip().splitlines():
    print("   " + line)
if proc.returncode != 0:
    print("   ERROR (exit code %d):" % proc.returncode)
    print(proc.stderr)
vp = sorted((OUT / "validation_plots").glob("*.png"))
print(f"Plots made by validate_phantom.py ({len(vp)}):")
for p in vp:
    print(f"   output/validation_plots/{p.name}")

# ============================================================ STEP 2
banner("STEP 2: run the team's unit tests (code/tests/test_tissue_interaction.py)")
try:
    import pytest  # noqa: F401
    print("pytest is installed; still running the test functions directly for a clear report.")
except ImportError:
    # The test file does 'import pytest' and uses only pytest.raises(...).
    # pytest is not required for this demo, so we provide a tiny stand-in
    # that does the same job as pytest.raises.
    print("pytest is not installed -> using a tiny built-in stand-in for 'pytest.raises'.")
    stub = types.ModuleType("pytest")

    @contextmanager
    def _raises(exc_type):
        try:
            yield
        except exc_type:
            return
        raise AssertionError(f"DID NOT RAISE {exc_type.__name__}")

    stub.raises = _raises
    sys.modules["pytest"] = stub


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


load_module("conftest", CODE / "tests" / "conftest.py")  # only adds code/ to sys.path
tests = load_module("test_tissue_interaction", CODE / "tests" / "test_tissue_interaction.py")
test_names = [n for n in dir(tests) if n.startswith("test_") and callable(getattr(tests, n))]
test_names.sort(key=lambda n: getattr(tests, n).__code__.co_firstlineno)  # file order
passed = 0
for i, name in enumerate(test_names, 1):
    try:
        getattr(tests, name)()
        passed += 1
        print(f"  [{i:2d}] PASS  {name}")
    except Exception:  # noqa: BLE001
        print(f"  [{i:2d}] FAIL  {name}")
        print("        " + traceback.format_exc().strip().splitlines()[-1])
print(f"Result: {passed}/{len(test_names)} tests passed")

# ============================================================ STEP 3
banner("STEP 3: demo - one 8 MHz incident pulse through tissue_interaction()")
fs = 100e6          # sampling rate [Hz] (chosen for this demo)
f0 = 8e6            # centre frequency [Hz]
n = 200             # samples -> 2 microseconds
t = np.arange(n) / fs
t0 = 1.0e-6         # pulse centre [s]
sigma = 0.15e-6     # Gaussian envelope width [s]
incident = np.exp(-((t - t0) ** 2) / (2 * sigma ** 2)) * np.sin(2 * np.pi * f0 * (t - t0))
with open(INP / "incident_pulse_8MHz.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["time_us", "pressure_relative"])
    for ti, pi in zip(t, incident):
        w.writerow([f"{ti * 1e6:.4f}", f"{pi:.6f}"])
print(f"Incident pulse: Gaussian-modulated sine, f0 = {f0/1e6:.0f} MHz, fs = {fs/1e6:.0f} MHz, "
      f"{n} samples ({n/fs*1e6:.1f} us), envelope sigma = {sigma*1e6:.2f} us")
print(f"  peak |p_incident| = {np.max(np.abs(incident)):.4f}   saved to input/incident_pulse_8MHz.csv")

ZBG = 1.63  # background (liver-like) impedance used by the team's code [MRayl]
cases = [
    ("A  amp = 1.0 (plain scatterer)", {"amp": 1.0}),
    ("B  amp = 0.5 (weaker scatterer)", {"amp": 0.5}),
    ("C  amp = -0.8 (negative amp -> flipped)", {"amp": -0.8}),
    ("D  amp = 1.0, Z = 1.38 (fat-like)", {"amp": 1.0, "background_impedance_mrayl": ZBG, "impedance_mrayl": 1.38}),
    ("E  amp = 1.0, Z = 7.8 (bone-like)", {"amp": 1.0, "background_impedance_mrayl": ZBG, "impedance_mrayl": 7.8}),
    ("F  amp = 1.0, scale = 0.35 (hypoechoic)", {"amp": 1.0, "interaction_scale": 0.35}),
    ("G  amp = 1.0, scale = 1.8 (hyperechoic)", {"amp": 1.0, "interaction_scale": 1.8}),
    ("H  amp = 1.0, scale = 0.0 (anechoic)", {"amp": 1.0, "interaction_scale": 0.0}),
]
with open(INP / "demo_scatterers.json", "w") as fh:
    json.dump({"note": "Scatterer dictionaries passed to tissue_interaction() in Step 3. "
                       "Impedances are example textbook-style values chosen for the demo.",
               "cases": [{"label": lab, "scatterer": sc} for lab, sc in cases]}, fh, indent=2)
print("Scatterer cases (saved to input/demo_scatterers.json):")
print(f"  {'case':44s} {'gain G':>8s} {'peak |p_out|':>13s} {'same shape?':>12s}")
reflected = []
for lab, sc in cases:
    out = tissue_interaction(incident, sc)
    g = interaction_gain(sc)
    reflected.append(out)
    print(f"  {lab:44s} {g:8.4f} {np.max(np.abs(out)):13.4f} {str(out.shape == incident.shape):>12s}")
print("  (G = amp * (1 + |R|) * interaction_scale; output = G * incident, no time shift)")

# Figure: incident vs reflected for each case
fig, axes = plt.subplots(4, 2, figsize=(11, 10), sharex=True, sharey=True)
for ax, (lab, sc), out in zip(axes.ravel(), cases, reflected):
    ax.plot(t * 1e6, incident, color="0.6", lw=1.2, label="incident")
    ax.plot(t * 1e6, out, color="C3", lw=1.4, label="reflected")
    ax.set_title(f"{lab}\nG = {interaction_gain(sc):.3f}", fontsize=9)
    ax.grid(alpha=0.3)
for ax in axes[-1]:
    ax.set_xlabel("Time [µs]")
for ax in axes[:, 0]:
    ax.set_ylabel("Relative pressure")
axes[0, 0].legend(fontsize=8, loc="upper right")
axes[0, 0].set_xlim(0.3, 1.7)
fig.suptitle("Team 4 demo: 8 MHz incident pulse vs reflected pulse from tissue_interaction()", fontsize=11)
fig.tight_layout()
fig.savefig(OUT / "demo_01_incident_vs_reflected.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 3.2))
ax.plot(t * 1e6, incident, color="C0")
ax.set(xlabel="Time [µs]", ylabel="Relative pressure", title="Sample input: Gaussian-modulated 8 MHz incident pulse")
ax.grid(alpha=0.3); fig.tight_layout(); fig.savefig(OUT / "demo_00_incident_pulse.png", dpi=150); plt.close(fig)

print()
print("Pressure reflection coefficient R = (Z2 - Z1)/(Z2 + Z1), Z1 = soft tissue 1.63 MRayl")
print("(the Z2 values below are example textbook-style values chosen as inputs for this demo)")
pairs = [("fat", 1.38), ("water", 1.48), ("blood", 1.61), ("soft tissue (same)", 1.63),
         ("muscle", 1.70), ("bone", 7.80), ("air", 0.0004)]
print(f"  {'Z2 material':20s} {'Z2 [MRayl]':>11s} {'R':>9s} {'R^2 (energy)':>13s} {'1+|R|':>7s}  sign")
r_rows = []
for name, z2 in pairs:
    r = pressure_reflection_coefficient(1.63, z2)
    r_rows.append((name, z2, r))
    sign = "inverted (-)" if r < 0 else ("none" if r == 0 else "same (+)")
    print(f"  {name:20s} {z2:11.4f} {r:9.4f} {r*r:13.4f} {1+abs(r):7.4f}  {sign}")

fig, ax = plt.subplots(figsize=(8, 3.6))
names = [f"{nm}\n{z:g}" for nm, z, _ in r_rows]
vals = [r for *_, r in r_rows]
ax.bar(names, vals, color=["C3" if v < 0 else "C0" for v in vals])
ax.axhline(0, color="k", lw=0.8)
for i, v in enumerate(vals):
    ax.text(i, v + (0.03 if v >= 0 else -0.03), f"{v:.3f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.set(ylabel="R (pressure)", title="Reflection coefficient from soft tissue (1.63 MRayl) into material Z2 [MRayl]",
       ylim=(-1.15, 1.0))
ax.tick_params(axis="x", labelsize=8)
fig.tight_layout(); fig.savefig(OUT / "demo_02_reflection_coefficients.png", dpi=150); plt.close(fig)

# ============================================================ STEP 4
banner("STEP 4: liver phantoms with generate_liver_phantom() - background + 4 lesion types")
geo = dict(center_x_m=0.0, center_z_m=0.035, radius_x_m=0.007, radius_z_m=0.008)
phantom_cases = [
    ("background (no lesion)", None),
    ("hypoechoic lesion", LesionProperties(echo_class="hypoechoic", **geo)),
    ("isoechoic lesion", LesionProperties(echo_class="isoechoic", **geo)),
    ("hyperechoic lesion", LesionProperties(echo_class="hyperechoic", **geo)),
    ("anechoic cyst (scale 0.0)", LesionProperties(echo_class="hypoechoic", scattering_scale=0.0, **geo)),
]
DENSITY, SEED = 120_000.0, 2026
cfg_dump = []
phantoms = []
for lab, les in phantom_cases:
    cfg = PhantomConfig(seed=SEED, scatterer_density_m2=DENSITY, lesion=les)
    ph = generate_liver_phantom(cfg)
    phantoms.append((lab, cfg, ph))
    cfg_dump.append({"name": lab, "config": asdict(cfg)})
with open(INP / "phantom_configs.json", "w") as fh:
    json.dump({"note": "PhantomConfig values passed to generate_liver_phantom() in Step 4 (SI units, metres).",
               "phantoms": cfg_dump}, fh, indent=2)
print("Phantom configs saved to input/phantom_configs.json")
c0 = phantoms[0][1]
area = (c0.x_max_m - c0.x_min_m) * (c0.z_max_m - c0.z_min_m)
print(f"Region x = {c0.x_min_m*1e3:.0f}..{c0.x_max_m*1e3:.0f} mm, z = {c0.z_min_m*1e3:.0f}..{c0.z_max_m*1e3:.0f} mm, "
      f"area = {area*1e4:.1f} cm^2, density = {DENSITY:,.0f} per m^2, seed = {SEED}")
print(f"Expected N = round(density * area) = {int(round(DENSITY*area))}")
print("Lesion: ellipse centre (0, 35) mm, radii 7 x 8 mm")
print(f"  {'phantom':28s} {'N':>5s} {'in lesion':>9s} {'scale':>6s} {'std(bg)':>8s} {'std(lesion)':>11s} {'ratio':>6s}")
scale_of = {"hypoechoic": 0.35, "isoechoic": 1.0, "hyperechoic": 1.8}
for lab, cfg, ph in phantoms:
    a = np.array([s["amp"] for s in ph.scatterers])
    les = np.array([s["is_lesion"] for s in ph.scatterers])
    if cfg.lesion is None:
        print(f"  {lab:28s} {ph.num_scatterers:5d} {'-':>9s} {'-':>6s} {np.std(a):8.3f} {'-':>11s} {'-':>6s}")
    else:
        sc = cfg.lesion.scattering_scale if cfg.lesion.scattering_scale is not None else scale_of[cfg.lesion.echo_class]
        sb, sl = np.std(a[~les]), np.std(a[les])
        print(f"  {lab:28s} {ph.num_scatterers:5d} {int(les.sum()):9d} {sc:6.2f} {sb:8.3f} {sl:11.3f} {sl/sb:6.2f}")
    with open(OUT / f"phantom_{lab.split()[0]}_scatterers.csv", "w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(["x_mm", "z_mm", "amp", "is_lesion"])
        for s in ph.scatterers:
            wr.writerow([f"{s['x']*1e3:.4f}", f"{s['z']*1e3:.4f}", f"{s['amp']:.5f}", int(s["is_lesion"])])
print("Same seed -> the SAME positions in all 5 phantoms; only amplitudes inside the lesion change.")
print("Scatterer lists saved as output/phantom_<type>_scatterers.csv")

tt = np.linspace(0, 2 * np.pi, 300)
lim = max(np.max(np.abs([s["amp"] for s in ph.scatterers])) for _, _, ph in phantoms)
fig, axes = plt.subplots(1, 5, figsize=(17, 4.2), sharey=True, layout="constrained")
for ax, (lab, cfg, ph) in zip(axes, phantoms):
    x = np.array([s["x"] for s in ph.scatterers]) * 1e3
    z = np.array([s["z"] for s in ph.scatterers]) * 1e3
    a = np.array([s["amp"] for s in ph.scatterers])
    sc_ = ax.scatter(x, z, c=a, cmap="coolwarm", vmin=-lim, vmax=lim, s=10 + 25 * np.abs(a), edgecolors="k",
                     linewidths=0.2)
    if cfg.lesion is not None:
        L = cfg.lesion
        ax.plot((L.center_x_m + L.radius_x_m * np.cos(tt)) * 1e3, (L.center_z_m + L.radius_z_m * np.sin(tt)) * 1e3,
                "k--", lw=1.2)
    ax.set_title(f"{lab}\nN = {ph.num_scatterers}", fontsize=9)
    ax.set_xlabel("Lateral x [mm]"); ax.set_aspect("equal")
    ax.set_xlim(-25, 25); ax.set_ylim(60, 10)
axes[0].set_ylabel("Depth z [mm]")
fig.colorbar(sc_, ax=axes, label="signed scatterer amplitude", shrink=0.9, pad=0.01)
fig.suptitle("generate_liver_phantom(): scatterer positions coloured by amplitude (dot size ~ |amp|)", fontsize=11)
fig.savefig(OUT / "demo_03_phantoms_scatterers.png", dpi=150, bbox_inches="tight")
plt.close(fig)

fig, axes = plt.subplots(1, 5, figsize=(17, 3.6), sharey=True)
bins = np.linspace(-lim, lim, 25)
for ax, (lab, cfg, ph) in zip(axes, phantoms):
    a = np.array([s["amp"] for s in ph.scatterers])
    les = np.array([s["is_lesion"] for s in ph.scatterers])
    ax.hist(a[~les], bins=bins, color="C0", alpha=0.7, label="background")
    if les.any():
        ax.hist(a[les], bins=bins, color="C3", alpha=0.8, label="inside lesion")
    ax.set_title(lab, fontsize=9); ax.set_xlabel("amplitude"); ax.legend(fontsize=7)
axes[0].set_ylabel("count")
fig.suptitle("Scatterer amplitude histograms (Gaussian, mean 0) - background vs lesion region", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "demo_04_amplitude_histograms.png", dpi=150); plt.close(fig)

# ============================================================ STEP 5
banner("STEP 5: 1-D speckle illustration (many tiny scatterers -> interference)")
print("Note: the time delays below are added by this demo only; in the full simulator")
print("delays are Team 3's job (propagation). Team 4's function only scales each echo.")
rng = np.random.default_rng(7)
c = 1540.0
n_line = 1200
t_line = np.arange(n_line) / fs              # 12 us of RF line
pulse_short = incident[int((t0 - 4 * sigma) * fs): int((t0 + 4 * sigma) * fs)]
rf = np.zeros(n_line + len(pulse_short))
n_sc = 80
depths = rng.uniform(1.5e-3, 7.5e-3, n_sc)   # scatterers between 1.5 and 7.5 mm
amps = rng.normal(0.0, 1.0, n_sc)
for d, a_ in zip(depths, amps):
    echo = tissue_interaction(pulse_short, {"amp": a_})
    k = int(round(2 * d / c * fs))
    rf[k:k + len(echo)] += echo
rf = rf[:n_line]
env_ = np.abs(hilbert(rf))
lam = c / f0
print(f"{n_sc} scatterers placed at random depths 1.5-7.5 mm, Gaussian amplitudes, wavelength = {lam*1e3:.3f} mm")
print(f"About {n_sc / (6.0e-3 / lam):.1f} scatterers per wavelength -> echoes overlap and interfere")
print(f"Envelope (2-10 us): mean = {env_[200:1000].mean():.3f}, std/mean = {env_[200:1000].std()/env_[200:1000].mean():.3f}"
      " (random bright/dark pattern = speckle)")
fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True)
axes[0].stem(2 * depths / c * 1e6, amps, basefmt=" ", markerfmt=".")
axes[0].set(ylabel="scatterer amp", title="Random scatterers (position -> round-trip time 2z/c)")
axes[1].plot(t_line * 1e6, rf, color="0.55", lw=0.8, label="summed RF echoes")
axes[1].plot(t_line * 1e6, env_, color="C3", lw=1.4, label="envelope (|Hilbert|)")
axes[1].set(xlabel="Time [µs]", ylabel="pressure", title="Sum of all echoes: interference gives speckle")
axes[1].legend(fontsize=8)
for ax in axes:
    ax.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(OUT / "demo_05_speckle_1d.png", dpi=150); plt.close(fig)

# ============================================================ SUMMARY
banner("SUMMARY")
print(f"validate_phantom.py : {'OK' if proc.returncode == 0 else 'FAILED'} ({len(vp)} plots)")
print(f"Unit tests          : {passed}/{len(test_names)} passed")
print("Output files:")
for p in sorted(OUT.rglob("*")):
    if p.is_file() and p.name not in ("console_log.txt", "console_screenshot.png"):
        print(f"   output/{p.relative_to(OUT).as_posix()}")
print("   output/console_log.txt")
print("   output/console_screenshot.png")
print(f"Total runtime: {time.time() - t_start:.1f} s")

sys.stdout = _real_stdout
_log.close()
save_console_png(LOG_PATH.read_text(encoding="utf-8"), OUT / "console_screenshot.png")
print("Console log and screenshot saved in output/.")
