# MotherCare AI - Model Training Guide

This directory contains the pipeline for training and fine-tuning the image classification model used in MotherCare AI.

## Dataset Structure

The training script (`train.py`) uses PyTorch's `ImageFolder` structure. You must organize your raw images into the following directory format:

```text
data/
└── raw/
    ├── train/
    │   ├── skin_allergy/
    │   ├── burn/
    │   ├── wound/
    │   └── other/
    └── val/
        ├── skin_allergy/
        ├── burn/
        ├── wound/
        └── other/
```

- **train/**: Contains images used for model training.
- **val/**: Contains images used for model validation during training.
- **class_name/**: Each class must have its own directory containing `.jpg`, `.png`, or `.webp` images.

## How to Run Training

1. Ensure you have the required dependencies installed (see `backend/requirements.txt`).
2. Populate the `data/raw/train` and `data/raw/val` folders with your medical image dataset.
3. Run the training script from the root of the project:
   ```bash
   python model/train.py
   ```

## Artifacts

- **weights.pth**: The best model weights (highest validation accuracy) are automatically saved here.
- **labels.json**: The mapping of numeric indices to class names is saved here to ensure consistency with the inference engine.

## Inference Integration

The inference engine in `backend/app/services/image_service.py` (via `model/predict.py`) automatically looks for `weights.pth` and `labels.json` to perform real predictions.
