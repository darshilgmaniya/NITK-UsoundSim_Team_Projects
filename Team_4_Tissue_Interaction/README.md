# Team 4: Tissue Interaction (NITK-UsoundSim)

Team 4 models what happens when the ultrasound pulse hits tissue. The tissue is
made of many tiny point scatterers (a "liver phantom"). Each scatterer sends
back a copy of the incoming (incident) pressure pulse, scaled by a gain
`G = amp * (1 + |R|) * interaction_scale`, where `R` is the pressure reflection
coefficient from acoustic impedances. The phantom can contain a lesion that is
darker (hypoechoic), equal (isoechoic), brighter (hyperechoic) or empty
(anechoic) compared to the background. In the full simulator this module sits
between forward propagation and return propagation (Team 3).

The full explanation (theory, code walk-through, inputs, outputs, viva
questions) is in **`Team_4_Tissue_Interaction_Explanation.pdf`**.

## Folder contents

| Path | What it is |
|---|---|
| `run_team4.py` | One command that runs everything and saves all results to `output/` |
| `requirements.txt` | Python packages needed |
| `code/tissue_interaction.py` | Team's original code: reflection coefficient, gain, `tissue_interaction()` |
| `code/phantom.py` | Team's original code: `generate_liver_phantom()` with optional lesion |
| `code/validate_phantom.py` | Team's original validation-plot script |
| `code/tests/` | Team's original unit tests (`test_tissue_interaction.py`, `conftest.py`) |
| `code/README.md` | Team's original technical README |
| `input/` | Sample inputs used by the run (8 MHz pulse, scatterer cases, phantom configs) |
| `output/` | Everything produced by the run (plots, CSV files, console log, console screenshot) |
| `Team_4_Tissue_Interaction_Explanation.pdf` | Explanation document |

The files in `code/` are exact copies of the team's files. They are not changed;
`run_team4.py` only calls them.

## Requirements

- Python 3.9 or newer (tested with Python 3.12.4)
- numpy, scipy, matplotlib (see `requirements.txt`)
- pytest is **not** needed. The runner runs the team's test functions directly.

## How to run

1. Install Python 3 from https://www.python.org if it is not installed.
2. Open a terminal (macOS/Linux: Terminal; Windows: Command Prompt or PowerShell).
3. Go into this folder:
   - macOS/Linux: `cd path/to/Team_4_Tissue_Interaction`
   - Windows: `cd path\to\Team_4_Tissue_Interaction`
4. Install the packages (only the first time):
   - macOS/Linux: `python3 -m pip install -r requirements.txt`
   - Windows: `python -m pip install -r requirements.txt`
5. Run the demo:
   - macOS/Linux: `python3 run_team4.py`
   - Windows: `python run_team4.py`
6. Open the `output/` folder to see the results.

## What you will see

The console shows five steps and a summary:

1. **validate_phantom.py** (team's script): prints `Generated 300 scatterers` and
   `Lesion-region scatterers: 28`, and makes 4 plots.
2. **Unit tests**: each of the 13 tests is listed as PASS or FAIL.
   Result on our run: `13/13 tests passed`.
3. **Pulse demo**: a table of gain `G` and peak output for 8 scatterer cases, and a
   table of reflection coefficients `R` for example impedances (fat, water, blood,
   muscle, bone, air; these impedance values are example textbook-style inputs we chose).
4. **Phantoms**: number of scatterers and amplitude spread (std) inside and outside
   the lesion for background, hypo-, iso-, hyper-echoic and anechoic phantoms.
5. **Speckle illustration**: a 1-D example showing how many echoes add up.

Output files (in `output/`):

| File | Meaning |
|---|---|
| `validation_plots/01_phantom_geometry.png` | Team's plot: scatterer positions and the lesion outline |
| `validation_plots/02_scatterer_amplitudes.png` | Team's plot: histogram of amplitudes, background vs lesion |
| `validation_plots/03_waveform.png` | Team's plot: incident vs scattered wave for one scatterer |
| `validation_plots/04_scattering_strength_map.png` | Team's plot: map of scatterer strength \|amp\| |
| `demo_00_incident_pulse.png` | The sample 8 MHz incident pulse (input to Step 3) |
| `demo_01_incident_vs_reflected.png` | Incident vs reflected pulse for 8 scatterer settings |
| `demo_02_reflection_coefficients.png` | Bar chart of R from soft tissue into other materials |
| `demo_03_phantoms_scatterers.png` | 5 phantoms: scatterer positions coloured by amplitude |
| `demo_04_amplitude_histograms.png` | Amplitude histograms, background vs lesion, for the 5 phantoms |
| `demo_05_speckle_1d.png` | Sum of many scatterer echoes and its envelope (speckle) |
| `phantom_<type>_scatterers.csv` | Scatterer list (x, z in mm, amp, is_lesion) for each phantom |
| `console_log.txt` | Full text of the console output |
| `console_screenshot.png` | Picture of the console output |

## Expected runtime

About 3 to 7 seconds on a laptop (measured: 2.6 to 4.2 s inside the script,
about 7 s including Python start-up).

## Troubleshooting

| Problem | What to do |
|---|---|
| `python3: command not found` (Windows) | Use `python` instead of `python3` |
| `ModuleNotFoundError: No module named 'numpy'` (or scipy / matplotlib) | Run step 4 again: `python3 -m pip install -r requirements.txt` |
| `pip` refuses to install ("externally managed environment") | Create a virtual environment: `python3 -m venv venv`, activate it (`source venv/bin/activate` or `venv\Scripts\activate`), then install again |
| No plots in `output/` | Make sure you run the command from inside this folder and that the folder is not read-only |
| A test shows FAIL | Check that the files in `code/` were not edited; they must be the team's originals |
| Want to use real pytest | `pip install pytest`, then from `code/` run `python3 -m pytest -q tests` (the runner does not need this) |
