# NITK-UsoundSim: Individual Team Projects

This folder holds one self-contained demo per team of the NITK-UsoundSim ultrasound simulator. Each team folder
runs on its own, without the integrated pipeline project. The integrated pipeline is kept separately in the
`NITK-UsoundSim` project (https://github.com/darshilgmaniya/NITK-UsoundSim).

## Pipeline order

Transducer -> TX Beamforming -> Acoustic Propagation -> Tissue Interaction -> RX Beamforming ->
Image Reconstruction -> B-mode Image Formation -> Post-Image Processing

## Team folders

| Folder | Stage | Run command | Explanation PDF |
|---|---|---|---|
| `Team_1_Transducer` | Piezoelectric material registry | `python3 run_team1.py` | `Team_1_Transducer_Explanation.pdf` |
| `Team_2_TX_Beamforming` | Transmit beamforming | `python3 run_team2.py` | `Team_2_TX_Beamforming_Explanation.pdf` |
| `Team_3_Acoustic_Propagation` | Acoustic propagation | `python3 run_team3.py` | `Team_3_Acoustic_Propagation_Explanation.pdf` |
| `Team_4_Tissue_Interaction` | Tissue interaction | `python3 run_team4.py` | `Team_4_Tissue_Interaction_Explanation.pdf` |
| `Team_5_RX_Beamforming` | Receive beamforming (delay-and-sum) | `python3 run_team5.py` | `Team_5_RX_Beamforming_Explanation.pdf` |
| `Team_6_Image_Reconstruction` | Hilbert envelope, normalisation, log compression | `python3 run_team6.py` | `Team_6_Image_Reconstruction_Explanation.pdf` |
| `Team_7_B_mode_Image_Formation` | Dynamic range, grayscale B-mode image | `python3 run_team7.py` | `Team_7_B_mode_Image_Formation_Explanation.pdf` |
| `Team_8_Post_Image_Processing` | Despeckling and image-quality metrics | `python3 run_team8.py` | `Team_8_Post_Image_Processing_Explanation.pdf` |

## How to run one team

```
cd Team_6_Image_Reconstruction
python3 -m pip install -r requirements.txt
python3 run_team6.py
```

On Windows use `python` instead of `python3`. Results are saved in that team's `output/` folder. Each team's
`README.md` has the full steps, expected output and troubleshooting.
