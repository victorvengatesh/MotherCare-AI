import os
from pathlib import Path

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
REQUIRED_CLASSES = ["skin_allergy", "burn", "wound", "other"]
IMBALANCE_THRESHOLD = 0.5  # Warn if a class has < 50% images of the largest class

def check_dataset():
    print("--- MotherCare AI: Dataset Verification Utility ---\n")
    
    if not os.path.exists(DATA_DIR):
        print(f"Error: Data directory not found at {DATA_DIR}")
        return

    splits = ["train", "val"]
    results = {}
    errors = []

    for split in splits:
        split_path = os.path.join(DATA_DIR, split)
        if not os.path.exists(split_path):
            errors.append(f"Missing split folder: {split}")
            continue

        results[split] = {}
        print(f"Checking '{split}' split...")
        
        for cls in REQUIRED_CLASSES:
            cls_path = os.path.join(split_path, cls)
            if not os.path.exists(cls_path):
                errors.append(f"Missing class folder: {split}/{cls}")
                results[split][cls] = 0
                continue

            # Count valid images
            files = os.listdir(cls_path)
            valid_images = [f for f in files if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS]
            results[split][cls] = len(valid_images)
            
            non_image_files = [f for f in files if Path(f).suffix.lower() not in SUPPORTED_EXTENSIONS and not os.path.isdir(os.path.join(cls_path, f))]
            if non_image_files:
                print(f"  [!] Warning: Found {len(non_image_files)} unsupported files in {split}/{cls}")

    # Summary Table
    print("\nDataset Summary:")
    print(f"{'Class':<20} | {'Train':<8} | {'Val':<8}")
    print("-" * 42)
    
    total_train = 0
    total_val = 0
    
    for cls in REQUIRED_CLASSES:
        train_count = results.get("train", {}).get(cls, 0)
        val_count = results.get("val", {}).get(cls, 0)
        total_train += train_count
        total_val += val_count
        print(f"{cls:<20} | {train_count:<8} | {val_count:<8}")
    
    print("-" * 42)
    print(f"{'TOTAL':<20} | {total_train:<8} | {total_val:<8}")

    # Validation Checks
    print("\nValidation Results:")
    
    if errors:
        print("[X] Errors found:")
        for err in errors:
            print(f"    - {err}")
    else:
        print("[OK] All required folders are present.")

    if total_train == 0:
        print("[X] Error: No training images found. Dataset is not ready for training.")
    else:
        # Check Imbalance
        counts = [results["train"][cls] for cls in REQUIRED_CLASSES]
        max_count = max(counts)
        if max_count > 0:
            for cls in REQUIRED_CLASSES:
                count = results["train"][cls]
                if count < max_count * IMBALANCE_THRESHOLD:
                    print(f"[!] Warning: Class '{cls}' is significantly under-represented ({count} vs {max_count} in largest class).")

    print("\nNext Steps:")
    if not errors and total_train > 0:
        print("Ready! You can now proceed to run the training script: python model/train.py")
    else:
        print("Please resolve the errors above before attempting to train.")

if __name__ == "__main__":
    check_dataset()
