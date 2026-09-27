# Team 6: Image Reconstruction (NITK-UsoundSim)

This folder shows the **Image Reconstruction** stage of the NITK-UsoundSim ultrasound simulator project.

**Stage order**

1. **Image Reconstruction (Team 6, this folder)**: beamformed RF -> envelope with the Hilbert transform ->
   normalisation to the peak -> **log compression (dB)**. The log-compressed envelope data is handed to Team 7.
2. **B-mode Image Formation (Team 7)**: applies the dynamic range to Team 6's dB data, maps it to grayscale
   brightness 0-1 and forms/saves the B-mode image.
3. **Post-Image Processing (Team 8)**: despeckles the finished grayscale image.

One command runs the stage on **real in-vivo carotid artery RF data** and saves every result, including the
handoff files for Team 7, in `output/`.

Full explanation (theory, code walk-through, input, output, run steps, viva questions):
**`Team_6_Image_Reconstruction_Explanation.pdf`**

## Folder contents

| Path | What it is | Origin |
|---|---|---|
| `run_team6.py` | The one script to run. Runs the notebooks' code (does not change them) and saves all outputs. | added for this demo |
| `requirements.txt` | Python packages needed. | added for this demo |
| `code/B_mode.ipynb` | Carotid notebook (9 code cells). Its steps 1-4 (cells 1-4 and the first half of cell 5) are this stage's job; the rest is Team 7's. | team original, byte-identical copy of `teams/T6_B_mode/B_mode_real_carotid_final/B_mode.ipynb` |
| `code/image_reconstruction.ipynb` | Second notebook: simulated 5 MHz RF -> DC removal -> band-pass -> Hilbert envelope -> scan conversion. | team original, unchanged (renamed copy of `UsoundIMGRECsample (2).ipynb`) |
| `code/carotid_1_rf.npy` | Copy of `input/carotid_1_rf.npy`, placed next to `B_mode.ipynb` because the notebook loads it by bare file name. | copy |
| `input/carotid_1_rf.npy`, `input/carotid_2_rf.npy` | Real in-vivo beamformed carotid RF, 1218 depth samples x 128 scan lines, float32. | team data (EPFL LTS5 us-non-stationary-deconv, L12-50 probe, 5 MHz, fs 31.25 MHz) |
| `output/` | Everything written by `run_team6.py` (see below). | made by `run_team6.py` |

## What run_team6.py does

**Part 1 (main demo, real carotid data, `code/B_mode.ipynb`)**, for carotid_1 and carotid_2:

- runs code cells 1, 2, 3, 4 in order (load RF, probe settings, Hilbert envelope, RF + envelope plot of one line);
- runs only the **first half of code cell 5**: its sections `3. NORMALIZE ENVELOPE` and `4. LOG COMPRESSION`.
  Cell 5 is split at the comment line `# 5. APPLY DYNAMIC RANGE`; the `# ====` line just above it is the start of
  that heading block, so it goes to the second half. The second half (dynamic range, brightness) and cells 6-9 are
  Team 7's steps and are not run;
- for carotid_2 only the line `DATA_FILE = "carotid_1_rf.npy"` is replaced in memory. The notebook file is never edited;
- saves the handoff for Team 7 and two runner figures per frame.

**Part 2 (`code/image_reconstruction.ipynb`)**: runs all its code cells unchanged and adds checks and two figures.

## Handoff for Team 7

`output/reconstructed_carotid_1.npz` and `output/reconstructed_carotid_2.npz` (made with `np.savez`, not compressed):

| Key | Shape | dtype | Meaning |
|---|---|---|---|
| `rf` | (1218, 128) | float32 | beamformed RF input (as loaded) |
| `envelope` | (1218, 128) | float32 | `abs(hilbert(rf, axis=0))` |
| `envelope_norm` | (1218, 128) | float32 | envelope / max, peak = 1 |
| `envelope_db` | (1218, 128) | float32 | `20*log10(envelope_norm + 1e-12)`, 0 dB = peak, **not clipped** |
| `fs`, `f0`, `c`, `pitch`, `depth_start_mm` | () | float64 | 31.25e6 Hz, 5e6 Hz, 1540 m/s, 0.1953e-3 m, 5.0 mm (notebook cell 2) |

This run: `envelope_db` goes from -90.65 to 0 dB (carotid_1) and from -86.10 to 0 dB (carotid_2).

## Requirements

- Python 3.9 or newer (tested with Python 3.12.4, numpy 1.26.4, scipy 1.16.0, matplotlib 3.8.3)
- Packages: `numpy`, `scipy`, `matplotlib` (listed in `requirements.txt`)
- No internet connection is needed.

## How to run

1. Install Python 3 from https://www.python.org (on Windows tick "Add Python to PATH").
2. Open a terminal in this folder, for example
   - macOS / Linux: `cd path/to/Team_6_Image_Reconstruction`
   - Windows: `cd path\to\Team_6_Image_Reconstruction`
3. Install the packages (once):
   - macOS / Linux: `python3 -m pip install -r requirements.txt`
   - Windows: `python -m pip install -r requirements.txt`
4. Run the demo:
   - macOS / Linux: `python3 run_team6.py`
   - Windows: `python run_team6.py`
5. Open the `output/` folder to see the pictures, the handoff files and the console log.

To open the notebooks yourself, see "Running the individual code files" below.

## What you will see

Key console lines from a real run:

```
Code cell 5 split at line 15 (the '=' line above '# 5. APPLY DYNAMIC RANGE'):
  envelope_db   : shape (1218, 128), dtype float32, min -90.655, max 0
  envelope max / min = 34100  ->  90.7 dB between the strongest and the weakest echo
Handoff for Team 7 (B-mode Image Formation): output/reconstructed_carotid_1.npz
Handoff for Team 7 (B-mode Image Formation): output/reconstructed_carotid_2.npz
  target at   15 mm on line 32: envelope peak found at  14.88 mm, peak value 1.008 (reflectivity 1.0)
```

Files in `output/`:

| File | Meaning |
|---|---|
| `carotid_N_01_notebook_rf_and_envelope.png` | Notebook's own figure (cell 4): RF and Hilbert envelope of scan line 64. |
| `carotid_N_02_runner_rf_envelope_db.png` | Runner figure: RF input, linear envelope, log-compressed envelope (display window -60..0 dB). |
| `carotid_N_03_runner_db_full_range_and_histogram.png` | Runner figure: envelope_db over its full unclipped range and a histogram of its values. |
| `reconstructed_carotid_N.npz` | **Handoff for Team 7** (see above). |
| `sim_A1_notebook_rf_envelope_and_scan_conversion.png` | image_reconstruction.ipynb's own figure: filtered RF + envelope of line 32, scan-converted image. |
| `sim_A2_runner_raw_rf_input.png` | Runner figure: the simulated RF before/after DC removal and band-pass, and the whole RF matrix. |
| `sim_A3_runner_envelope_db_and_scan_converted.png` | Runner figure: envelope linear and in dB, and the scan-converted image in dB. |
| `console_log.txt`, `console_screenshot.png` | Everything printed on the screen, as text and as a picture. |

(N = 1 and 2.) The dynamic-range clipping and the grayscale B-mode image are made by Team 7 from the handoff files.

## Running the individual code files

`run_team6.py` runs everything at once. To run the team's own files one by one:

The two notebooks are in `code/`. Open them with Jupyter (`python3 -m pip install jupyter`, then `jupyter notebook`),
with VS Code (Jupyter extension) or in Google Colab, and run all cells.

| File | What it needs | What it does |
|---|---|---|
| `code/B_mode.ipynb` | `code/carotid_1_rf.npy` (already next to the notebook) | Whole carotid chain; cells 1-4 and the first half of cell 5 are this team's stage. Saves `bmode_carotid_1.*` next to the notebook. |
| `code/image_reconstruction.ipynb` | nothing | Simulated 5 MHz RF -> band-pass -> Hilbert envelope -> scan-converted image. |

In Colab also upload `carotid_1_rf.npy` next to `B_mode.ipynb`.

In VS Code, open this team folder or the whole `NITK-UsoundSim_Team_Projects` folder, pick a Python interpreter that has the packages from `requirements.txt` (bottom-right corner of VS Code), then open a file and press the Run button.

## Expected runtime

About 10-15 seconds in total on a MacBook (this run: 9.7 s reported by the script). Most of it is the `griddata`
interpolation in Part 2.

## Troubleshooting

| Problem | What to do |
|---|---|
| `python3: command not found` (macOS/Linux) or `python` not found (Windows) | Install Python 3; on Windows use `py run_team6.py` or re-install with "Add Python to PATH". |
| `ModuleNotFoundError` for numpy / scipy / matplotlib | Run step 3 again: `python3 -m pip install -r requirements.txt`. |
| `FileNotFoundError` for `input/...` or `code/...` | Keep the folder structure as it is; `input/carotid_1_rf.npy` and `input/carotid_2_rf.npy` must exist. |
| `pip` refuses to install ("externally managed environment") | Make a virtual environment: `python3 -m venv venv`, then `source venv/bin/activate` (Windows: `venv\Scripts\activate`), then step 3 again. |
| No windows open with plots | Normal: plots are saved as PNG files in `output/` instead of being shown. |
