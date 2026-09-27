# Team 5: Receive (RX) Beamforming (delay-and-sum)

NITK-UsoundSim, a 2-D ultrasound simulator. Team 5 turns the raw echo signals of all 128 probe elements
(raw RF) into a beamformed RF image. For every scan line and every depth, each element's signal is delayed
by its own travel time and then all elements are added (delay-and-sum, with dynamic receive focus, a Hann
receive window and F-number 1.0). Points that are in focus add up strongly; echoes from other places mostly
cancel. The output (3118 depths x 256 scan lines, 0-60 mm deep, x = -10..+10 mm) goes to the next stage,
which does envelope detection and log compression.

The full explanation (theory, code walk-through, input, output, viva questions) is in
**`Team_5_RX_Beamforming_Explanation.pdf`**.

## Folder contents

| Path | What it is |
|---|---|
| `run_team5.py` | ONE command that runs everything and saves all outputs to `output/` |
| `requirements.txt` | Python libraries needed (numpy, scipy, matplotlib) |
| `code/verify_beamformer.py` | Team 5's four verification tests (delivered by Team 5) |
| `code/receive_beamforming.py` | `das_beamform()`, the delay-and-sum beamformer (written during project integration, verified with Team 5's tests) |
| `code/mock_data.py` | point-target test RF for the tests (written during project integration) |
| `code/config.py` | probe, axes and receive settings: local copy of the project's `simulator/config.py`, same values, paths point inside this folder |
| `code/support/` | input generator copied unchanged from other teams (Team 3 propagation, Team 4 tissue, `tissue_phantoms.py`). **Not Team 5's work**; only used by the tests to make fresh RF |
| `input/point_targets_rf.npz` | raw RF (128 x 3574) + `t_axis`: 3 point targets at (-5,10), (0,20), (+5,30) mm |
| `input/cyst_rf.npz` | raw RF (128 x 3574) + `t_axis`: speckle tissue with an anechoic cyst, centre (0,30) mm, radius 6 mm |
| `output/` | everything produced by `run_team5.py` |
| `Team_5_RX_Beamforming_Explanation.pdf` | the explanation document |

The three Team 5 files in `code/` are unchanged copies of the project files.

## Requirements

- Python 3.9 or newer
- numpy, scipy, matplotlib (`pip install -r requirements.txt`)

## How to run

1. Install Python from python.org (Windows: tick "Add Python to PATH").
2. Open a terminal and go into this folder:
   `cd path/to/Team_5_RX_Beamforming`
3. Install the libraries (once):
   - macOS / Linux: `python3 -m pip install -r requirements.txt`
   - Windows: `python -m pip install -r requirements.txt`
4. Run:
   - macOS / Linux: `python3 run_team5.py`
   - Windows: `python run_team5.py`
5. Look at the console, then open the `output/` folder.

(To run only Team 5's tests: `cd code` and then `python3 verify_beamformer.py`.)

## What you will see

The console shows six steps:

1. **Team 5's tests**: 4/4 pass. Depth errors 0.008 mm (30 mm), 0.034 mm (15 mm), 0.040 mm (40 mm),
   0.036 mm (55 mm); correct delays give peak 0.327 vs 0.066 without per-element delays.
2. **Inputs** loaded: rf (128, 3574), t_axis from -0.750 us to 88.575 us in 25 ns steps.
3. **Delay idea** at (0, 20) mm: the echo reaches the edge element 4.95 us later than the centre element.
4. **Beamforming** of both inputs: output shape (3118, 256).
5. **Measurements**: the three targets are found within 0.04 mm of their true positions;
   -6 dB axial width 0.342 mm, lateral width 0.456 mm at (0, 20) mm; cyst inside is 25.2 dB darker than the tissue around it.
6. **Apodization comparison** (lateral -6 dB width / highest side lobe): rect 0.300 mm / -18.1 dB,
   hamming 0.430 mm / -33.3 dB, hann 0.456 mm / -32.6 dB (plus F# = 2 and a fixed full aperture).

Output files in `output/`:

| File | Meaning |
|---|---|
| `01_input_point_targets_raw_rf.png` | raw RF input of the point targets: full view, zoom (one pixel per sample), one channel |
| `02_input_cyst_raw_rf.png` | raw RF input of the cyst phantom |
| `03_delay_alignment_0_20mm.png` | echo curve before delays, straight line after delays, and the summed line |
| `04_beamformed_rf_point_targets.png` | Team 5's output for the point targets (beamformed RF) |
| `05_display_point_targets.png` | display image (envelope + log, 50 dB): for display only, this is the next team's job |
| `06_beamformed_rf_cyst.png` | Team 5's output for the cyst phantom (beamformed RF) |
| `07_display_cyst.png` | display image of the cyst result (for display only) |
| `08_resolution_profiles_0_20mm.png` | axial and lateral profiles with the -6 dB widths |
| `09_apodization_comparison.png` | receive windows and lateral profiles for rect / hamming / hann and aperture choices |
| `beamformed_point_targets.npz`, `beamformed_cyst.npz` | beamformed RF data (`beamformed`, `z_axis`, `x_lines`) for the next stage |
| `console_log.txt` | everything printed in the console |
| `console_screenshot.png` | the console output as a picture |

## Running the individual code files

`run_team5.py` runs everything at once. To run the team's own files one by one:

From the `code/` folder (`cd code`):

| File | Command | What it does |
|---|---|---|
| `verify_beamformer.py` | `python3 verify_beamformer.py` | Team's own test file (4 checks of the delay-and-sum beamformer). |
| `receive_beamforming.py` | `python3 receive_beamforming.py` | Library: the delay-and-sum beamformer used by the files above. |
| `mock_data.py` | `python3 mock_data.py` | Library: makes test RF data through `support/`. |
| `support/tissue_phantoms.py` | not run on its own | Copied project module; it needs this folder's `config.py`, which `verify_beamformer.py` loads first. Check it with `python3 -c "import config, tissue_phantoms"` (from `code/`, with `support` on the path: `PYTHONPATH=support`). |
| other `support/` files | `python3 support/<file>` | Unchanged copies of Team 3 / Team 4 code, used to make the test RF. |

In VS Code, open this team folder (File > Open Folder) or the whole `NITK-UsoundSim_Team_Projects` folder, pick a Python interpreter that has the packages from `requirements.txt` (bottom-right corner of VS Code), then open a file and press the Run button. The `.vscode/settings.json` file sets the import paths, so the files below run as they are.

## Expected runtime

About 30 to 40 seconds on a normal computer (measured 31.8 s and 36.2 s); up to about 1 minute when the
computer is busy (measured up to 60 s). Team 5's tests take the longest because they simulate fresh RF.

## Troubleshooting

| Problem | What to do |
|---|---|
| `ModuleNotFoundError: numpy` (or scipy / matplotlib) | Run step 3 again with the same Python you use in step 4 |
| `'python3' is not recognized` (Windows) | Use `python run_team5.py` or `py run_team5.py` |
| `FileNotFoundError` for `input/...npz` | Keep the folder structure as it is; run the command inside `Team_5_RX_Beamforming` |
| It seems slow | Normal on a busy computer; wait until `DONE` appears |
| No plot windows open | Correct: plots are saved as PNG files in `output/` |
| Permission error when writing `output/` | Copy the folder to a place where you can write (for example the Desktop) |
