# Team 7: B-mode Image Formation (NITK-UsoundSim)

This stage turns the **log-compressed echo data from Team 6** into the final
**grayscale B-mode image**. It applies the **dynamic range** (clipping of the dB values),
maps the dB values to **grayscale brightness 0 to 1** (0 to 255 grey levels in the PNG),
computes the **depth and width axes** in mm, displays the image and saves it for the next stage.
It is shown on **real in-vivo carotid artery data** (two frames).

Stage order in the simulator:

1. **Image Reconstruction (Team 6)**: Hilbert envelope detection, normalisation, log compression (dB).
2. **B-mode Image Formation (Team 7, this folder)**: dynamic range, grayscale brightness, axes, final image.
3. **Post-Image Processing (Team 8)**: despeckling of the finished grayscale image.

Envelope detection (Hilbert transform) and log compression are done by Team 6; this
stage starts from their result.

The full explanation (theory, code walk-through, all results) is in
**`Team_7_B_mode_Image_Formation_Explanation.pdf`**.

## Folder contents

| Path | What it is |
|---|---|
| `run_team7.py` | One script that runs this stage and saves every result in `output/` (written for this demo) |
| `code/B_mode.ipynb` | Team notebook, real carotid data (original, unchanged). The runner executes only its B-mode part (see below) |
| `code/carotid_1_rf.npy` | Raw carotid RF (copy of Team 6's input), only for opening `B_mode.ipynb` on its own; not used by `run_team7.py` |
| `input/reconstructed_carotid_1.npz`, `input/reconstructed_carotid_2.npz` | The output of Team 6 (Image Reconstruction), copied here as input |
| `input/reference/bmode_carotid_1.npy`, `..._axes.npz` | The B-mode image the team's notebook saved earlier (for the reproducibility check) |
| `output/` | Everything produced by `run_team7.py` |
| `requirements.txt` | Python packages needed |
| `Team_7_B_mode_Image_Formation_Explanation.pdf` | Full explanation |

### The input files (Team 6's handoff)

Each `reconstructed_carotid_N.npz` (made with `np.savez`) contains:

| Key | Content (carotid_1) |
|---|---|
| `rf` | beamformed RF, (1218, 128) float32 (only used for display) |
| `envelope` | Hilbert envelope, (1218, 128) float32, 4.99583 to 170356 |
| `envelope_norm` | envelope / its maximum, (1218, 128) float32, 2.93e-05 to 1 |
| `envelope_db` | 20 log10(envelope_norm + 1e-12), (1218, 128) float32, **-90.655 to 0 dB**, 0 dB = peak, not yet clipped |
| `fs`, `f0`, `c`, `pitch`, `depth_start_mm` | 31.25 MHz, 5 MHz, 1540 m/s, 0.1953 mm, 5.0 mm |

For carotid_2, `envelope_db` runs from -86.1025 to 0 dB.

## Which notebook code this stage runs

`code/B_mode.ipynb` contains the whole chain in one notebook. The runner splits it at the
line `# 5. APPLY DYNAMIC RANGE` and runs only this stage's part, unchanged:

| Notebook code | Who | Run here? |
|---|---|---|
| Cell 1 (imports + `np.load` of the RF) | Team 6 | only the lines `import numpy as np` and `import matplotlib.pyplot as plt` |
| Cell 2 (fs, f0, c, pitch, depth start, `dynamic_range = 60`) | shared | yes (gives `dynamic_range`) |
| Cell 3 (Hilbert envelope), cell 4 (one scan line plot) | Team 6 | no, the values come from the input file |
| Cell 5, sections 3-4 (normalise, log compression) | Team 6 | no, `envelope_db` comes from the input file |
| Cell 5, sections 5-6 (clip to dynamic range, brightness 0..1) | **Team 7** | yes |
| Cells 6, 7, 8, 9 (axes, all-steps display, final image, save) | **Team 7** | yes (cell 9 runs inside `output/`) |

The runner also sets `DATA_FILE = "carotid_N_rf.npy"`, because cell 9 builds the output
file names from it. Every `plt.show()` is replaced by "save the figure to `output/`".

## Requirements

- Python 3.9 or newer (tested with Python 3.12.4)
- numpy and matplotlib (tested with numpy 1.26.4, matplotlib 3.8.3)

## How to run

1. Install Python 3 from https://www.python.org (on Windows, tick "Add Python to PATH").
2. Open a terminal (macOS: Terminal; Windows: Command Prompt or PowerShell).
3. Go into this folder:
   - macOS / Linux: `cd path/to/Team_7_B_mode_Image_Formation`
   - Windows: `cd path\to\Team_7_B_mode_Image_Formation`
4. Install the packages (only once):
   - macOS / Linux: `python3 -m pip install -r requirements.txt`
   - Windows: `python -m pip install -r requirements.txt`
5. Run the demo:
   - macOS / Linux: `python3 run_team7.py`
   - Windows: `python run_team7.py`
6. Open the `output/` folder to see the images.

To open `B_mode.ipynb` on its own, see "Running the individual code files" below.

## What you will see

The console prints five parts: (1) the input files, (2) this stage's notebook code for
carotid_1 and carotid_2, (3) the dynamic-range comparison, (4) the reproducibility check,
(5) a summary with timings.

Measured in this run:

| | carotid_1 | carotid_2 |
|---|---|---|
| Black (clipped) pixels at 40 dB | 26.44 % | 30.11 % |
| Black pixels at 50 dB | 4.90 % | 5.74 % |
| Black pixels at 60 dB (notebook setting) | 0.50 % | 0.63 % |
| Mean brightness at 60 dB | 0.447 | 0.415 |
| Depth axis / lateral axis | 5.0 to 35.0 mm / -12.5 to 12.3 mm | same |

Reproducibility check (carotid_1, 60 dB): this run's `output/bmode_carotid_1.npy` against
the image the notebook saved earlier (`input/reference/bmode_carotid_1.npy`). Largest absolute
difference **6.49e-06** (mean 1.11e-07); the depth and width axes are identical. PASS: float32
rounding only, far below one grey level (1/255 = 0.0039); after rounding to 8-bit grey levels
6 of 155904 pixels differ by one level.

Files in `output/`:

| File | Meaning |
|---|---|
| `input_envelope_db_overview.png` | Runner figure: the input `envelope_db` of both frames and a histogram with the 40/50/60 dB clip levels |
| `carotid_1_01_all_steps.png` | Notebook cell 7: RF, envelope (both from Team 6), clipped dB image, final B-mode |
| `carotid_1_02_final_bmode.png` | Notebook cell 8: final B-mode image of carotid_1 (60 dB) |
| `carotid_2_01/02_*.png` | The same two figures for carotid_2 |
| `bmode_carotid_1.npy / .png / _axes.npz` | Notebook cell 9: brightness 0..1 (float32), gray PNG, depth and width axes in mm; goes to Team 8 |
| `bmode_carotid_2.npy / .png / _axes.npz` | The same for carotid_2 |
| `dynamic_range_40_50_60dB.png` | Runner figure: both frames at 40, 50 and 60 dB (notebook formula) |
| `reproducibility_check_60dB.png` | Runner figure: saved reference image, this run's image, and their difference |
| `console_log.txt`, `console_screenshot_1..3.png` | Console text of the run and pictures of it |

## Running the individual code files

`run_team7.py` runs everything at once. To run the team's own files one by one:

`code/B_mode.ipynb` can also be opened on its own with Jupyter (`python3 -m pip install jupyter scipy`, then
`jupyter notebook`), with VS Code (Jupyter extension) or in Google Colab. Run all cells. The notebook starts from the
raw carotid RF, so `code/carotid_1_rf.npy` is placed next to it; it runs Team 6's steps (envelope, log compression)
and then this team's steps (dynamic range, grayscale image), and saves `bmode_carotid_1.*` next to the notebook.
In Colab also upload `carotid_1_rf.npy` next to the notebook. `run_team7.py` does not use this RF file; it starts from
Team 6's `.npz` handoff in `input/`.

In VS Code, open this team folder or the whole `NITK-UsoundSim_Team_Projects` folder, pick a Python interpreter that has the packages from `requirements.txt` (bottom-right corner of VS Code), then open a file and press the Run button.

## Expected runtime

About 3 seconds (measured 2.8 s inside the script on a Mac laptop; a first run can take
a few seconds longer while Python loads its libraries).

## Troubleshooting

| Problem | What to do |
|---|---|
| `ModuleNotFoundError: No module named 'numpy'` (or matplotlib) | Run step 4 again with the same `python3` / `python` you use in step 5 |
| `python3: command not found` (Windows) | Use `python` instead of `python3` |
| `FileNotFoundError: ...reconstructed_carotid_1.npz` | Run from inside this folder and keep `input/` next to `run_team7.py` |
| No windows with pictures appear | Normal: figures are saved as PNG files in `output/` |
| Very small differences (about 1e-6) from the numbers above | Different numpy versions round float32 numbers slightly differently |
