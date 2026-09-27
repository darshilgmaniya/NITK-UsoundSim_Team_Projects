# Team 1: Transducer (Piezoelectric Material Registry)

Team 1 wrote a small Python package that stores **piezoelectric materials** (the crystal or ceramic inside an ultrasound probe) together with their **operating frequency range**. A `Piezo` object checks that every range is valid (two numbers, not negative, minimum not larger than maximum). A `PiezoRegistry` keeps all materials in a dictionary so they can be added and found by name. `process_material()` registers a material and returns a random frequency inside its range. `run_team1.py` runs the team's own demo (`main.py`), then uses the same functions for the project's probe (Philips L12-4 reference model, PZT-5H, 4 to 12 MHz), and finally shows the validation errors. In the full simulator, this part describes the probe material and its frequency band. The element geometry of the 128-element array is computed elsewhere in the project (by Team 3's code), not here.

The full explanation (theory, code walk-through, input, output, viva questions) is in **`Team_1_Transducer_Explanation.pdf`**.

## Folder contents

| Path | What it is |
|---|---|
| `run_team1.py` | The one script to run. It calls the team's code and saves all outputs. |
| `code/` | The team's original code, copied without any change: `piezo.py`, `registry.py`, `exceptions.py`, `new_piezo.py`, `add_attributes.py`, `process.py`, `main.py` |
| `input/team1_inputs.json` | The sample inputs: random seed, the L12-4 probe values, and the wrong inputs used to test validation |
| `output/` | Everything made by `run_team1.py` (figures, CSV, console log, console screenshot) |
| `requirements.txt` | Python packages needed |
| `Team_1_Transducer_Explanation.pdf` | Full explanation document |

## Requirements

- Python 3.9 or newer (the team's code uses `tuple[float, float]` type hints, which need 3.9+). Tested with Python 3.12.
- `matplotlib` (only used by `run_team1.py` to draw figures; the team's code itself uses only the Python standard library).

## How to run

1. Install Python 3.9+ from https://www.python.org (on Windows, tick "Add Python to PATH").
2. Open a terminal (macOS/Linux: Terminal; Windows: Command Prompt or PowerShell) in this folder.
3. Install the requirement:
   - macOS / Linux: `python3 -m pip install -r requirements.txt`
   - Windows: `python -m pip install -r requirements.txt`
4. Run:
   - macOS / Linux: `python3 run_team1.py`
   - Windows: `python run_team1.py`
5. Open the `output/` folder to see the results.

## What you will see

The console prints three demos:

- **Demo 1: the team's `main.py`, run as written.** It registers Quartz (100 to 500 kHz) and PZT-5H (1000 to 5000 kHz) and prints a random frequency for each (355.77 kHz and 1100.04 kHz with seed 42), retrieves Quartz again (210.01 kHz), and catches a lookup error for `UnknownMat`.
- **Demo 2: the project probe.** Registers `L12-4 PZT-5H` with 4000 to 12000 kHz (4 to 12 MHz), gets 6200.23 kHz, then makes 2000 more calls: all 2000 values fall inside the range (average 8046.37 kHz).
- **Demo 3: validation errors.** Wrong inputs (min > max, negative, text, three values, a single number) each raise `PiezoValidationError`; an unknown name raises `PiezoNotFoundError`.

**Random seed:** the team's `process_material()` uses `random.uniform()` without a seed. `run_team1.py` calls `random.seed(42)` first (the seed is in `input/team1_inputs.json`), so every run prints the same numbers. The team's code is not changed for this.

**Units:** all frequencies are in **kHz**, the same unit the team's `main.py` uses (1 MHz = 1000 kHz).

Output files (in `output/`):

| File | Meaning |
|---|---|
| `console_log.txt` | Full text printed by the run |
| `console_screenshot.png` | Picture of the console output |
| `fig1_material_frequency_ranges.png` | Frequency range of each registered material (bars) with the random frequency returned by `process_material()` (triangle) |
| `fig2_l12_4_random_frequencies.png` | Histogram of 2000 random frequencies for the L12-4 probe: they spread evenly between 4 and 12 MHz |
| `registry_contents.csv` | Table of the materials in the registry: min, max, bandwidth, generated frequency |

## Running the individual code files

`run_team1.py` runs everything at once. To run the team's own files one by one:

From the `code/` folder (`cd code`):

| File | Command | What it does |
|---|---|---|
| `main.py` | `python3 main.py` | Team's own entry point: registers the piezo materials (Quartz, PZT-5H) and prints their frequencies. |
| `registry.py`, `piezo.py`, `new_piezo.py`, `process.py`, `add_attributes.py`, `exceptions.py` | `python3 <file>` | Library files used by `main.py`; they run without error but print little on their own. |

In VS Code, open this team folder or the whole `NITK-UsoundSim_Team_Projects` folder, pick a Python interpreter that has the packages from `requirements.txt` (bottom-right corner of VS Code), then open a file and press the Run button.

## Expected runtime

About 1 second (measured: 1.1 s wall time on a MacBook, Python 3.12).

## Things to know (honest notes)

- In `main.py`, the "BadRange" test uses `(500.0, 1000.0)`, which is a *valid* range. So no validation error is printed there and "BadRange" is registered. Demo 3 shows real validation errors.
- When `process_material()` gets a bad range, the material is first added with `(0.0, 0.0)` and only then the range is checked. So after the error the material is still in the registry with `(0.0, 0.0)` (shown in Demo 3b).

## Troubleshooting

| Problem | Fix |
|---|---|
| `python3: command not found` (Windows) | Use `python` instead of `python3`. |
| `ModuleNotFoundError: No module named 'matplotlib'` | Run step 3 again (`pip install -r requirements.txt`). |
| `TypeError: 'type' object is not subscriptable` | Your Python is older than 3.9. Install a newer Python. |
| `ModuleNotFoundError: No module named 'registry'` | Run the command from inside this folder, and keep `code/` next to `run_team1.py`. |
| Numbers differ from this README | Check that `random_seed` in `input/team1_inputs.json` is still 42. |
