import os
import json
import time
import copy
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader

# Configuration
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
MODEL_DIR = os.path.dirname(__file__)
WEIGHTS_PATH = os.path.join(MODEL_DIR, "weights.pth")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.json")

# Hyperparameters
BATCH_SIZE = 16
NUM_EPOCHS = 25
LEARNING_RATE = 0.001

def check_dataset():
    """Validates if the required dataset folders exist."""
    train_dir = os.path.join(DATA_DIR, "train")
    val_dir = os.path.join(DATA_DIR, "val")
    
    if not os.path.exists(train_dir) or not os.path.exists(val_dir):
        return False, "Error: Dataset folders 'data/raw/train' or 'data/raw/val' not found."
    
    classes = [d for d in os.listdir(train_dir) if os.path.isdir(os.path.join(train_dir, d))]
    if len(classes) < 2:
        return False, f"Error: Found only {len(classes)} classes. Need at least 2 for training."
    
    return True, ""

def train_model():
    print("--- MotherCare AI: Model Training Pipeline ---")
    
    valid, message = check_dataset()
    if not valid:
        print(message)
        print("\nPlease ensure your folder structure looks like this:")
        print("data/raw/train/skin_allergy/")
        print("data/raw/train/burn/")
        print("...")
        return

    # 1. Data Augmentation and Transforms
    data_transforms = {
        'train': transforms.Compose([
            transforms.RandomResizedCrop(224),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    # 2. Loading Dataset
    image_datasets = {x: datasets.ImageFolder(os.path.join(DATA_DIR, x), data_transforms[x])
                      for x in ['train', 'val']}
    dataloaders = {x: DataLoader(image_datasets[x], batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
                   for x in ['train', 'val']}
    dataset_sizes = {x: len(image_datasets[x]) for x in ['train', 'val']}
    class_names = image_datasets['train'].classes

    print(f"Dataset loaded: {dataset_sizes['train']} training images, {dataset_sizes['val']} validation images.")
    print(f"Classes: {class_names}")

    # 3. Save Labels Mapping
    labels_map = {i: name for i, name in enumerate(class_names)}
    with open(LABELS_PATH, 'w') as f:
        json.dump(labels_map, f, indent=2)
    print(f"Labels mapping saved to {LABELS_PATH}")

    # 4. Model Setup
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model = models.resnet18(pretrained=True)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, len(class_names))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    # 5. Training Loop
    since = time.time()
    best_model_wts = copy.deepcopy(model.state_dict())
    best_acc = 0.0

    for epoch in range(NUM_EPOCHS):
        print(f'Epoch {epoch}/{NUM_EPOCHS - 1}')
        print('-' * 10)

        for phase in ['train', 'val']:
            if phase == 'train':
                model.train()
            else:
                model.eval()

            running_loss = 0.0
            running_corrects = 0

            for inputs, labels in dataloaders[phase]:
                inputs = inputs.to(device)
                labels = labels.to(device)

                optimizer.zero_grad()

                with torch.set_grad_enabled(phase == 'train'):
                    outputs = model(inputs)
                    _, preds = torch.max(outputs, 1)
                    loss = criterion(outputs, labels)

                    if phase == 'train':
                        loss.backward()
                        optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                running_corrects += torch.sum(preds == labels.data)

            epoch_loss = running_loss / dataset_sizes[phase]
            epoch_acc = running_corrects.double() / dataset_sizes[phase]

            print(f'{phase} Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

            if phase == 'val' and epoch_acc > best_acc:
                best_acc = epoch_acc
                best_model_wts = copy.deepcopy(model.state_dict())

        print()

    time_elapsed = time.time() - since
    print(f'Training complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s')
    print(f'Best val Acc: {best_acc:4f}')

    # 6. Save Weights
    model.load_state_dict(best_model_wts)
    torch.save(model.state_dict(), WEIGHTS_PATH)
    print(f"Best model weights saved to {WEIGHTS_PATH}")

if __name__ == "__main__":
    try:
        train_model()
    except Exception as e:
        print(f"Error during training: {e}")
