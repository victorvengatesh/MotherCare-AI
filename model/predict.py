import os
import json
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# Configuration
MODEL_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(MODEL_DIR, "weights.pth")
LABELS_PATH = os.path.join(MODEL_DIR, "labels.json")

# Default classes (Fallback)
DEFAULT_CLASSES = ["skin_allergy", "burn", "wound", "other"]

def load_class_names():
    """Load class names from labels.json or return defaults."""
    if os.path.exists(LABELS_PATH):
        try:
            with open(LABELS_PATH, 'r') as f:
                labels_map = json.load(f)
                # Sort keys to ensure correct order
                return [labels_map[str(i)] for i in range(len(labels_map))]
        except Exception as e:
            print(f"Warning: Could not load labels.json: {e}")
    return DEFAULT_CLASSES

CLASSES = load_class_names()

def get_model(num_classes=4):
    """
    Load a ResNet18 model with a custom final layer.
    """
    # Using 'weights' instead of 'pretrained' as per latest torchvision API
    try:
        model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    except Exception:
        # Fallback for older torchvision versions
        model = models.resnet18(pretrained=True)
        
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, num_classes)
    return model

def predict_image(image_path: str) -> dict:
    """
    Performs image classification using a pretrained ResNet18 model.
    """
    try:
        # 1. Image Preprocessing
        preprocess = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        if not os.path.exists(image_path):
            return {"error": "Image file not found"}

        input_image = Image.open(image_path).convert('RGB')
        input_tensor = preprocess(input_image)
        input_batch = input_tensor.unsqueeze(0)

        # 2. Check for device and weights
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = get_model(num_classes=len(CLASSES))
        
        weights_loaded = False
        if os.path.exists(MODEL_PATH):
            try:
                model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
                weights_loaded = True
            except Exception as e:
                print(f"Warning: Could not load weights from {MODEL_PATH}: {e}")

        model.to(device)
        model.eval()

        # 3. Inference
        with torch.no_grad():
            output = model(input_batch.to(device))
            probabilities = torch.nn.functional.softmax(output[0], dim=0)
            
        confidence, index = torch.max(probabilities, 0)
        
        return {
            "predicted_class": CLASSES[index.item()],
            "confidence": round(confidence.item(), 4),
            "model_architecture": "ResNet18",
            "weights_loaded": weights_loaded,
            "status": "success"
        }

    except Exception as e:
        print(f"Error in image prediction: {e}")
        return {
            "predicted_class": "unknown",
            "confidence": 0.0,
            "error": str(e),
            "status": "fallback"
        }

if __name__ == "__main__":
    # Small test if run directly
    import sys
    if len(sys.argv) > 1:
        print(predict_image(sys.argv[1]))
    else:
        print("Usage: python predict.py <image_path>")
