"""
run_team1.py - one command to run Team 1 (Transducer) code and save all outputs.

    macOS / Linux :  python3 run_team1.py
    Windows       :  python run_team1.py

What it does
  Demo 1  Runs the team's own main.py demo exactly as written.
  Demo 2  Uses the team's functions for the project probe
          (Philips L12-4 reference model, PZT-5H, 4 to 12 MHz = 4000 to 12000 kHz).
  Demo 3  Sends wrong inputs to the team's code to show its validation errors.

The team's files in code/ are not changed. This script only imports and calls them.
All frequencies are in kHz, the unit used by the team's main.py.
Everything is saved in the output/ folder.
"""
import csv
import io
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE / "code"
INPUT = HERE / "input" / "team1_inputs.json"
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)

# The team's modules import each other by plain name (e.g. "from registry import registry"),
# so the code/ folder must be on the import path.
sys.path.insert(0, str(CODE))
sys.dont_write_bytecode = True  # keep code/ clean (no __pycache__ folder)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


class Tee(io.TextIOBase):
    """Prints to the screen and keeps a copy of the text for the log file."""

    def __init__(self, screen):
        self.screen, self.buf = screen, io.StringIO()

    def write(self, s):
        self.screen.write(s)
        self.buf.write(s)
        return len(s)

    def flush(self):
        self.screen.flush()


def banner(text):
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def console_to_png(text, out_png, title="Terminal", width_chars=106, max_lines=120):
    """Save the console text as a terminal-style picture."""
    lines = []
    for line in text.rstrip("\n").expandtabs(4).splitlines():
        while len(line) > width_chars:
            lines.append(line[:width_chars])
            line = "    " + line[width_chars:]
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [f"... ({len(lines) - max_lines + 1} more lines, see console_log.txt)"]
    h = 0.62 + 0.165 * len(lines)
    fig = plt.figure(figsize=(0.083 * width_chars + 0.4, h))
    fig.patch.set_facecolor("#1e1e1e")
    fig.text(0.012, 1 - 0.28 / h, "o o o   " + title, color="#9a9a9a", fontsize=9, family="DejaVu Sans Mono", va="center")
    for i, ln in enumerate(lines):
        fig.text(0.012, 1 - (0.55 + 0.165 * i) / h, ln, color="#e6e6e6", fontsize=8.6,
                 family="DejaVu Sans Mono", va="top")
    fig.savefig(out_png, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    t0 = time.perf_counter()
    cfg = json.loads(INPUT.read_text())
    seed = cfg["random_seed"]

    # The team's process_material() uses random.uniform() with no seed.
    # We fix the seed here so that every run prints the same numbers.
    random.seed(seed)

    # Import the team's original modules (unchanged copies in code/).
    import main as team_main
    from registry import registry
    from process import process_material
    from piezo import Piezo
    from exceptions import PiezoError, PiezoValidationError, PiezoNotFoundError

    print("NITK-UsoundSim  |  Team 1: Transducer (piezoelectric material registry)")
    print(f"Team code folder : code/   (original files, not modified)")
    print(f"Input file       : input/team1_inputs.json")
    print(f"Random seed      : {seed}  (set by run_team1.py so results repeat)")
    print("Frequency unit   : kHz  (1 MHz = 1000 kHz), same as the team's main.py")

    # ------------------------------------------------------------------
    banner("DEMO 1: the team's own main.py (run exactly as written)")
    team_main.main()
    print("\nRegistry after Demo 1:")
    for name in registry.list_materials():
        lo, hi = registry.get_material(name).freq_range
        print(f"  {name:<10s} {lo:9.1f} to {hi:9.1f} kHz")
    print("Note: main.py's 'BadRange' test uses (500, 1000), which is a VALID range,")
    print("      so no validation error is raised there and 'BadRange' is registered.")
    print("      Demo 3 below shows the validation errors with really invalid ranges.")

    demo1_freqs = {}
    # Re-create the numbers main.py printed, to mark them on the figure.
    random.seed(seed)
    registry.clear()
    demo1_freqs["Quartz"] = process_material("Quartz", (100.0, 500.0), create_new=True)
    demo1_freqs["PZT-5H"] = process_material("PZT-5H", (1000.0, 5000.0), create_new=True)
    print("\n(Check) registry.clear(), seed reset, Quartz and PZT-5H registered again:")
    print(f"        Quartz {demo1_freqs['Quartz']:.2f} kHz and PZT-5H {demo1_freqs['PZT-5H']:.2f} kHz,"
          " the same as above, so the run is repeatable.")

    # ------------------------------------------------------------------
    banner("DEMO 2: the project probe (Philips L12-4 reference model)")
    p = cfg["demo_2_project_probe"]
    lo_in, hi_in = p["freq_range_khz"]
    print(f"Probe            : {p['probe_name']}")
    print(f"Material         : {p['material']}")
    print(f"Elements         : {p['n_elements']}  (element positions are made elsewhere, by Team 3's code)")
    print(f"Operating range  : {lo_in/1000:.0f} to {hi_in/1000:.0f} MHz = {lo_in:.0f} to {hi_in:.0f} kHz")

    f_probe = process_material(p["name"], (lo_in, hi_in), create_new=True)
    print(f"\nprocess_material('{p['name']}', ({lo_in:.0f}, {hi_in:.0f}), create_new=True)")
    print(f"  -> random frequency inside the range: {f_probe:.2f} kHz = {f_probe/1000:.3f} MHz")

    obj = registry.get_material(p["name"].lower())  # lookup is case-insensitive
    print(f"registry.get_material('{p['name'].lower()}') -> Piezo(name='{obj.name}', freq_range={obj.freq_range})")
    bw = obj.freq_range[1] - obj.freq_range[0]
    centre = (obj.freq_range[0] + obj.freq_range[1]) / 2
    print(f"  bandwidth = max - min = {bw:.0f} kHz, middle of range = {centre:.0f} kHz "
          f"(project centre frequency {p['center_frequency_khz']:.0f} kHz)")
    print(f"  fractional bandwidth = bandwidth / middle = {bw/centre*100:.0f} %")

    n = p["n_random_draws"]
    draws = [process_material(p["name"], create_new=False) for _ in range(n)]
    inside = sum(lo_in <= f <= hi_in for f in draws)
    print(f"\n{n} more calls with create_new=False (look up only):")
    print(f"  smallest = {min(draws):.2f} kHz, largest = {max(draws):.2f} kHz, "
          f"average = {sum(draws)/n:.2f} kHz")
    print(f"  values inside {lo_in:.0f}..{hi_in:.0f} kHz: {inside} of {n}")
    print(f"Registered materials now: {registry.list_materials()}")

    # Save registry contents (valid materials only) for the figure and CSV.
    reg_rows = []
    for name in registry.list_materials():
        m = registry.get_material(name)
        gen = demo1_freqs.get(name, f_probe if name == p["name"] else None)
        reg_rows.append((name, m.freq_range[0], m.freq_range[1], gen))

    # ------------------------------------------------------------------
    banner("DEMO 3: validation errors (wrong inputs)")
    print("3a) Making a Piezo object directly with a bad range:")
    for case in cfg["demo_3_invalid_inputs"]:
        rng = case["freq_range"]
        rng = tuple(rng) if isinstance(rng, list) else rng
        try:
            Piezo(case["name"], rng)
            print(f"  {case['name']:<12s} {rng!r}: accepted (no error)")
        except PiezoValidationError as e:
            print(f"  {case['name']:<12s} {rng!r}")
            print(f"      problem : {case['problem']}")
            print(f"      caught  : PiezoValidationError: {e}")

    print("\n3b) The same kind of bad input through process_material():")
    try:
        process_material("Swapped", (12000.0, 4000.0), create_new=True)
    except PiezoValidationError as e:
        print(f"  caught PiezoValidationError: {e}")
    left = registry.get_material("Swapped")
    print(f"  but 'Swapped' is still in the registry with freq_range={left.freq_range}")
    print("  (newPiezoMaterial() adds it with (0.0, 0.0) BEFORE the range is checked)")

    print("\n3c) Looking up a material that was never registered:")
    try:
        registry.get_material("PZT-8")
    except PiezoNotFoundError as e:
        print(f"  caught PiezoNotFoundError: {e}")

    print("\n3d) Exception family (from exceptions.py):")
    print(f"  PiezoValidationError is a PiezoError: {issubclass(PiezoValidationError, PiezoError)}, "
          f"is a ValueError: {issubclass(PiezoValidationError, ValueError)}")
    print(f"  PiezoNotFoundError   is a PiezoError: {issubclass(PiezoNotFoundError, PiezoError)}, "
          f"is a KeyError  : {issubclass(PiezoNotFoundError, KeyError)}")

    # ------------------------------------------------------------------
    banner("SAVING OUTPUTS")
    csv_path = OUT / "registry_contents.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["material", "min_freq_khz", "max_freq_khz", "bandwidth_khz", "generated_freq_khz"])
        for name, lo, hi, gen in reg_rows:
            w.writerow([name, lo, hi, hi - lo, "" if gen is None else round(gen, 2)])
    print(f"saved {csv_path.relative_to(HERE)}")

    # Figure 1: frequency ranges of valid registered materials.
    fig, ax = plt.subplots(figsize=(9, 3.8))
    colours = {"Quartz": "#8c8c8c", "PZT-5H": "#2e6da4", "BadRange": "#c0a060", p["name"]: "#b0413e"}
    for i, (name, lo, hi, gen) in enumerate(reg_rows):
        ax.barh(i, hi - lo, left=lo, height=0.5, color=colours.get(name, "#555"), alpha=0.85)
        ax.text(hi * 1.06, i, f"{lo:g} to {hi:g} kHz", va="center", fontsize=9)
        if gen is not None:
            ax.plot(gen, i, marker="v", color="black", markersize=10)
            ax.text(gen, i + 0.33, f"{gen:.1f}", ha="center", fontsize=8)
    ax.set_yticks(range(len(reg_rows)), [r[0] for r in reg_rows])
    ax.set_xscale("log")
    ax.set_xlim(60, 40000)
    ax.set_ylim(-0.6, len(reg_rows) - 0.3)
    ax.set_xlabel("Frequency (kHz, log scale)")
    ax.set_title(f"Registered piezo materials: frequency range (bar) and random frequency from process_material() (triangle), seed {seed}",
                 fontsize=9.5)
    ax.grid(axis="x", which="both", alpha=0.3)
    fig.tight_layout()
    f1 = OUT / "fig1_material_frequency_ranges.png"
    fig.savefig(f1, dpi=150)
    plt.close(fig)
    print(f"saved {f1.relative_to(HERE)}")

    # Figure 2: histogram of the random frequencies for the project probe.
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.hist([d / 1000 for d in draws], bins=40, range=(3, 13), color="#b0413e", alpha=0.8, edgecolor="white")
    ax.axvline(lo_in / 1000, color="black", ls="--", lw=1)
    ax.axvline(hi_in / 1000, color="black", ls="--", lw=1)
    ax.axvline(p["center_frequency_khz"] / 1000, color="#2e6da4", lw=1.5)
    ymax = ax.get_ylim()[1] * 1.25
    ax.set_ylim(0, ymax)
    ax.text(lo_in / 1000, ymax * 0.95, " min 4 MHz", fontsize=8, va="top")
    ax.text(hi_in / 1000, ymax * 0.95, " max 12 MHz", fontsize=8, va="top")
    ax.text(p["center_frequency_khz"] / 1000, ymax * 0.85, " centre 8 MHz", fontsize=8, va="top", color="#2e6da4")
    ax.set_xlabel("Frequency returned by process_material() (MHz)")
    ax.set_ylabel("Count")
    ax.set_title(f"L12-4 PZT-5H: {n} calls to process_material(create_new=False), seed {seed}", fontsize=10)
    fig.tight_layout()
    f2 = OUT / "fig2_l12_4_random_frequencies.png"
    fig.savefig(f2, dpi=150)
    plt.close(fig)
    print(f"saved {f2.relative_to(HERE)}")

    print(f"saved output/console_log.txt")
    print(f"saved output/console_screenshot.png")
    print(f"\nDone in {time.perf_counter() - t0:.1f} s. All outputs are in the output/ folder.")


if __name__ == "__main__":
    tee = Tee(sys.stdout)
    sys.stdout = tee
    try:
        main()
    finally:
        sys.stdout = tee.screen
    text = tee.buf.getvalue()
    (OUT / "console_log.txt").write_text(text)
    console_to_png(text, OUT / "console_screenshot.png", title="python3 run_team1.py")
