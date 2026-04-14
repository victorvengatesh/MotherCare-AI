# MotherCare AI - Dataset Preparation Guide

This guide outlines how to prepare and organize image data for training the MotherCare AI image classification model.

## Folder Structure

The training pipeline expects a specific directory structure under `data/raw/`. Each subdirectory represents a classification category.

```text
data/
└── raw/
    ├── train/                # Training dataset (80-90% of data)
    │   ├── skin_allergy/     # Images for skin allergy
    │   ├── burn/             # Images for burns
    │   ├── wound/            # Images for wounds
    │   └── other/            # Images for other conditions
    └── val/                  # Validation dataset (10-20% of data)
        ├── skin_allergy/
        ├── burn/
        ├── wound/
        └── other/
```

## Image Requirements

- **Supported Formats**: `.jpg`, `.jpeg`, `.png`, `.webp`
- **Resolution**: Minimum recommended 224x224 pixels. Images will be automatically resized during training.
- **Content**: Images should be clear and focused on the relevant symptom or condition.

## Workflow

1. **Collection**: Gather images for each category.
2. **Sorting**: Place images into their respective `train/` category folders.
3. **Splitting**: Move a small, random subset (approx 15%) from each `train/` folder to the corresponding `val/` folder.
4. **Validation**: Run the verification utility to ensure the dataset is ready:
   ```bash
   python model/check_dataset.py
   ```
5. **Training**: Once validated, proceed to training using the `model/train.py` script.

## Notes on Class Balance

For best results, try to have a similar number of images in each class (e.g., 100 images for burns, 100 for wounds). Large imbalances may lead to a biased model.
