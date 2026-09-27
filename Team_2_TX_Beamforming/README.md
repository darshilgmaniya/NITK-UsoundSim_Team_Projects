# Team 2: Transmit (TX) Beamforming - NITK-UsoundSim

This folder shows the work of **Team 2 (Transmit Beamforming)**. The team's code takes the
probe description (a 128-element linear array, Philips L12-4 reference model: 0.30 mm pitch,
4 to 12 MHz, 8 MHz centre, PZT-5H) and the beam settings (focus at x = 0 mm, z = 40 mm,
sound speed 1540 m/s, Hann apodization). It works out **when each of the 128 elements must
fire** (the transmit delays) and **how strongly** (the apodization weights), so that all the
waves arrive at the focus at the same moment. It saves these as a "TX package" that the next
team (Acoustic Propagation) loads. One command runs everything and saves all results in
`output/`.

The full explanation (theory, code walk-through, input, output, viva questions) is in
**`Team_2_TX_Beamforming_Explanation.pdf`**.

## Folder contents

| Item | What it is |
|---|---|
| `run_team2.py` | The one command to run. Runs the team's scripts and tests, prints a summary, saves every output to `output/`. |
| `requirements.txt` | Python packages needed (numpy, matplotlib). |
| `code/` | The team's **original** code, copied unchanged (same folder layout as the team's `Usound/` folder). |
| `code/src/beamformer.py` | Array positions, delays, apodization, Gaussian pulse, TX package. |
| `code/src/transducer_interface.py` | Reads and checks the probe settings. |
| `code/src/acoustic_handoff.py` | Loader used by the next team to read the TX package. |
| `code/run_transmit_beamforming.py` | Team's main script (step 1). |
| `code/visualize_transmit_beamforming.py` | Team's plotting script (step 2). |
| `code/tests/test_beamformer.py` | Team's two tests. |
| `code/config/` | Team's original settings files. |
| `code/docs/` | Team's notes (`RUN_ORDER.txt`, two `.md` files) plus seven `.py` files that are byte-identical reference copies of Team 1's (Transducer) piezo-material code. Nothing in Team 2's code imports them; they are not run. |
| `code/outputs/` | The outputs the team had saved before (kept as-is for reference). |
| `input/` | The two input files used by the run (`transducer_interface.json`, `beamforming.json`). They start as exact copies of `code/config/`. |
| `output/` | Everything made by `run_team2.py` (it is emptied and re-made on every run). |
| `Team_2_TX_Beamforming_Explanation.pdf` | The explanation document. |

## Requirements

- Python **3.10 or newer** (the team's code uses the `float | None` type style, which needs 3.10+).
- numpy and matplotlib (`pip install -r requirements.txt`).
- No internet needed. pytest is **not** needed.

## How to run

1. Install Python 3.10+ from <https://www.python.org> (on Windows tick "Add Python to PATH").
2. Open a terminal (macOS: Terminal; Windows: Command Prompt or PowerShell).
3. Go into this folder:
   - macOS / Linux: `cd path/to/Team_2_TX_Beamforming`
   - Windows: `cd path\to\Team_2_TX_Beamforming`
4. Install the packages (only the first time):
   - macOS / Linux: `python3 -m pip install -r requirements.txt`
   - Windows: `python -m pip install -r requirements.txt`
5. Run the demo:
   - macOS / Linux: `python3 run_team2.py`
   - Windows: `python run_team2.py`
6. Open the `output/` folder to see the pictures and files.

What `run_team2.py` does, in order:

1. Copies `code/` to a temporary working folder and puts the two files from `input/` into its
   `config/` folder (so `code/` itself is never changed).
2. Runs the team's `run_transmit_beamforming.py` (as in the team's `docs/RUN_ORDER.txt`).
3. Runs the team's `visualize_transmit_beamforming.py`. That script calls `plt.show()`; the
   runner turns each `plt.show()` into "save the figure as PNG", so no windows open.
4. Runs the team's tests: it imports `tests/test_beamformer.py` and **calls each `test_*`
   function directly**, printing PASS or FAIL (pytest is not used).
5. Copies the team's output files to `output/` and prints a summary read from them.
6. Makes four extra figures with the team's own functions (files starting with `extra_`).
7. Saves the console text and a screenshot-style picture of it.

To try other settings, edit the files in `input/` (for example change `focus_z_m` to `0.02`
or `apodization` to `"rect"`) and run again.

## What you will see

The console prints six sections (STEP 0 to STEP 5, then DONE). Key lines from the real run:

```
  | TX beamforming completed
  | Elements: 128
  | Frequency MHz: 8.0
  | Delay range us: 0.0 2.7950482224488855
...
  | PASS  test_delay
  | PASS  test_shapes
  | RESULT 2/2 tests passed
...
  Aperture (first to last centre)   : 38.10 mm
  Wavelength c/f0                   : 0.1925 mm  (pitch = 1.56 wavelengths)
  Focus (x, z)                      : (0.0 mm, 40.0 mm)
  Delay min / max                   : 0.0000 us / 2.7950 us
  Elements that fire first          : 1, 128
  Elements that fire last           : 61, 62, 63, 64, 65, 66, 67, 68
...
  Field map: strongest point on the centre line at z = 40.0 mm (focus set to 40.0 mm)
  Field map: -6 dB beam width at focus depth = 0.36 mm
  Field map: energy at the focus is 16.8 dB higher than with no delays
```

Output files in `output/`:

| File | Made by | Meaning |
|---|---|---|
| `tx_beamforming_package.npz` | team code | **The hand-off to Acoustic Propagation**: element positions, delays, weights (128 each), frequency, sound speed, focus, steering. |
| `tx_beamforming_summary.json` | team code | Short readable summary (probe, focus, min/max delay). |
| `tx_element_pulses.npz` | team code | The delayed, weighted pulse of every element (128 x 688 samples) and the time axis. |
| `team_fig1_delay_vs_element.png` | team code | Delay of each element: an upside-down bowl (edges 0 us, centre 2.795 us). |
| `team_fig2_position_vs_delay.png` | team code | Same delays plotted against element position in mm. |
| `extra_1_delays_and_weights.png` | runner (extra) | Delays with labels, the Hann weights used, and an example of steering-only delays (+/-15 deg). |
| `extra_2_apodization_windows.png` | runner (extra) | Rect / Hann / Hamming weights from `make_apodization` and their beam patterns (main lobe vs side lobes, grating lobes). |
| `extra_3_pulse.png` | runner (extra) | The team's Gaussian pulse, its spectrum, and a few element signals from `tx_element_pulses.npz`. |
| `extra_4_tx_field_map.png` | runner (extra) | Simple 2-D map of where the delayed pulses add up: bright spot at the focus; compared with no delays. |
| `console_log.txt` | runner | Everything printed on the screen. |
| `console_screenshot.png` | runner | Picture of the console output. |

## Running the individual code files

`run_team2.py` runs everything at once. To run the team's own files one by one:

From the `code/` folder (`cd code`):

| File | Command | What it does |
|---|---|---|
| `run_transmit_beamforming.py` | `python3 run_transmit_beamforming.py` | Team's own run: builds the transmit package in `code/outputs/`. |
| `visualize_transmit_beamforming.py` | `python3 visualize_transmit_beamforming.py` | Team's plots of the transmit delays and weights from `code/outputs/` (opens plot windows). |
| `tests/test_beamformer.py` | `python3 -m pytest tests` | Unit tests (2 tests). Needs `pytest` (in `requirements.txt`). Running the file with plain `python3` only imports it and runs no test. |
| `src/beamformer.py` | not run on its own | Library module with a relative import (`from .transducer_interface import ...`); it is used by the files above. To check it imports: `python3 -c "import src.beamformer"`. |
| `src/transducer_interface.py`, `src/acoustic_handoff.py` | `python3 src/<file>` | Library modules used by the files above. |

In VS Code, open this team folder (File > Open Folder) or the whole `NITK-UsoundSim_Team_Projects` folder, pick a Python interpreter that has the packages from `requirements.txt` (bottom-right corner of VS Code), then open a file and press the Run button. The `.vscode/settings.json` file sets the import paths, so the files below run as they are.

## Expected runtime

About **20 seconds** on a laptop (measured 18.8 s to 21.8 s on a shared 8-core Mac).
The team's own two scripts take under 1 second; most of the time is the extra field map.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python3: command not found` / `python is not recognized` | Install Python 3.10+; on Windows use `python` (or `py`) and tick "Add Python to PATH" during install. |
| `ModuleNotFoundError: No module named 'numpy'` (or `matplotlib`) | Run the pip command in step 4 with the same Python you use to run the demo. |
| `TypeError: unsupported operand type(s) for \|` | Your Python is older than 3.10. Install a newer Python. |
| `ValueError: This interface requires 128 elements` | `n_elements` in `input/transducer_interface.json` must stay 128 (the team's code enforces this). |
| `ValueError: center_frequency_hz must be inside operating range` | Keep `center_frequency_hz` between `frequency_min_hz` and `frequency_max_hz`. |
| `ValueError: sound speed and focus depth must be positive` | `focus_z_m` and `sound_speed_m_s` in `input/beamforming.json` must be > 0. |
| `PermissionError` when writing `output/` | Copy the folder to a place you can write to (for example your Desktop) and run again. |
| No picture windows open | Normal: all figures are saved as PNG files in `output/`. |
