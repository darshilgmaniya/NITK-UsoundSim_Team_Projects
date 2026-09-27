# Team 8: Post-Image Processing (NITK-UsoundSim)

This folder shows the **Post-Image Processing** stage of the NITK-UsoundSim ultrasound simulator project. It is the
**last stage** of the pipeline: it only starts once the grayscale B-mode image exists (made by **B-mode Image Formation,
Team 7**). The module `code/post_processing.py` removes speckle from a finished B-mode image with the self-guided filter
(He et al. 2013, r = 4, eps = 0.001) that the team selected in its study notebook, and measures the image quality before
and after (speckle index, contrast, CNR, gCNR, edge sharpness). One command runs it and saves every result in `output/`.

Full explanation (theory, code walk-through, input, output, run steps, viva questions):
**`Team_8_Post_Image_Processing_Explanation.pdf`**

## Folder contents

| Path | What it is |
|---|---|
| `run_team8.py` | The one script to run. Calls the team's code (does not change it) and saves all outputs. |
| `requirements.txt` | Python packages needed. |
| `code/post_processing.py` | Team's original module: `postprocess()`, `guided()`, metric functions (`scan_convert()` in it belongs to the B-mode stage and is not used here). |
| `code/262SP009_Post_Image_Processing_v2.ipynb` | Team's full study notebook: compares 10 despeckling filters on real ultrasound datasets (needs internet; run in Colab). |
| `code/notebook_results/` | 10 figures saved by that study notebook in an earlier run (not produced by `run_team8.py`). |
| `input/cyst_lesion_image.npz`, `input/scatterers_image.npz` | Sample inputs: two grayscale B-mode images from the project's simulator, 512 x 256 px, values 0-1, 0.078 mm pixels, x = -10..10 mm, z = 0..40 mm (keys `image`, `x_img`, `z_img`; axes in metres). |
| `input/*_preview.png` | Pictures of the two input images. |
| `output/` | Everything written by `run_team8.py` (see below). |

## Requirements

- Python 3.9 or newer (tested with Python 3.12.4, numpy 1.26.4, scipy 1.16.0, matplotlib 3.8.3, opencv-python 4.9.0)
- Packages: `numpy`, `scipy`, `matplotlib`, `opencv-python` (listed in `requirements.txt`)
- No internet connection is needed to run the demo.

## How to run

1. Install Python 3 from https://www.python.org (on Windows tick "Add Python to PATH").
2. Open a terminal (macOS: Terminal; Windows: Command Prompt or PowerShell) in this folder, for example
   - macOS / Linux: `cd path/to/Team_8_Post_Image_Processing`
   - Windows: `cd path\to\Team_8_Post_Image_Processing`
3. Install the packages (once):
   - macOS / Linux: `python3 -m pip install -r requirements.txt`
   - Windows: `python -m pip install -r requirements.txt`
4. Run the demo:
   - macOS / Linux: `python3 run_team8.py`
   - Windows: `python run_team8.py`
5. Open the `output/` folder to see the pictures and the console log.

To open the study notebook: upload `code/262SP009_Post_Image_Processing_v2.ipynb` to https://colab.research.google.com
(File > Upload notebook). It installs its own extra packages in its first cell and downloads public datasets from
Kaggle/Zenodo, so it needs internet and takes several minutes.

## What you will see

The console prints a table of quality metrics before and after the filter. Key lines from a real run:

```
scatterers   speckle index SI (lower = smoother)     0.178     0.163      -8.3%
cyst_lesion  speckle index SI (lower = smoother)     0.308     0.241     -21.7%
cyst_lesion  contrast lesion-ring (dB, 50 dB DR)   -19.404   -19.317     +0.087
cyst_lesion  CNR (higher = better)                  2.323     2.425     +0.102
cyst_lesion  gCNR (0..1, higher = better)           0.860     0.871     +0.010
cyst_lesion  edge sharpness (Sobel, grey/px)      145.728   140.534     -5.194
cyst_lesion  edge sharpness kept                              96.4%
```

Files in `output/`:

| File | Meaning |
|---|---|
| `B1_before_after.png` | Both input images before and after the guided filter, with the speckle index. |
| `B2_cyst_edge_zoom.png` | Close-up of the cyst border before and after. |
| `B3_difference_map.png` | After minus before: where brightness changed. |
| `B4_brightness_profile.png` | Brightness along one row through the cyst centre (z = 30 mm), before and after. |
| `B5_histograms.png` | Grey-level histograms before and after. |
| `B6_eps_comparison.png` | Cyst with eps = 0.001, 0.002, 0.005, 0.01 and a plot of edge kept and gCNR vs eps. |
| `B_postprocessed_images.npz` | The two filtered images as numbers (float32, 0-1). |
| `console_log.txt` | Everything printed on the screen. |
| `console_screenshot.png` | The same console output as a picture. |

## Expected runtime

About 3-8 seconds in total on a MacBook (this run: 2.9 s reported by the script). The filter itself takes only a few
milliseconds per image; saving the figures takes most of the time.

## Troubleshooting

| Problem | What to do |
|---|---|
| `python3: command not found` (macOS/Linux) or `python` not found (Windows) | Install Python 3; on Windows use `py run_team8.py` or re-install with "Add Python to PATH". |
| `ModuleNotFoundError: No module named 'cv2'` | `python3 -m pip install opencv-python` (the package name differs from the import name). |
| `ModuleNotFoundError` for numpy / scipy / matplotlib | Run step 3 again: `python3 -m pip install -r requirements.txt`. |
| `FileNotFoundError` for `input/...npz` or `code/...` | Keep the folder structure as it is; run the command from inside this folder or give the full path to `run_team8.py`. |
| Note "project config.py not in this folder" | Normal. `post_processing.py` imports the project's `config` only for `scan_convert()`, which this demo does not use; the runner gives it an empty placeholder. |
| `pip` refuses to install ("externally managed environment") | Make a virtual environment: `python3 -m venv venv`, then `source venv/bin/activate` (Windows: `venv\Scripts\activate`), then step 3 again. |
| No windows open with plots | Normal: plots are saved as PNG files in `output/` instead of being shown. |
