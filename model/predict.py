import os
import json
import logging
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model-inference")

class MedicalConditionClassifier:
    """
    Modular classifier for medical skin conditions using ResNet18.
    Implements singleton-like model loading to optimize performance.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MedicalConditionClassifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.model_dir = os.path.dirname(__file__)
        self.weights_path = os.path.join(self.model_dir, "weights.pth")
        self.labels_path = os.path.join(self.model_dir, "labels.json")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Hyperparameters & Constants
        self.confidence_threshold = 0.60
        self.image_size = (224, 224)
        self.mean = [0.485, 0.456, 0.406]
        self.std = [0.229, 0.224, 0.225]
        
        # Load classes and model
        self.classes = self._load_class_names()
        self.model = self._initialize_model()
        self.weights_loaded = self._load_weights()
        
        self.model.to(self.device).eval()
        self._initialized = True
        logger.info(f"Classifier initialized on {self.device}")

    def _load_class_names(self):
        """Loads valid class names from labels.json."""
        default_classes = ["burn", "other", "skin_allergy", "wound"]
        if os.path.exists(self.labels_path):
            try:
                with open(self.labels_path, 'r') as f:
                    labels_map = json.load(f)
                    return [labels_map[str(i)] for i in range(len(labels_map))]
            except Exception as e:
                logger.warning(f"Failed to load labels.json: {e}")
        return default_classes

    def _initialize_model(self):
        """Builds the ResNet18 architecture."""
        try:
            # Prefer 'weights' for newer torchvision versions
            model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        except Exception:
            # Fallback for older versions
            model = models.resnet18(pretrained=True)
            
        num_ftrs = model.fc.in_features
        model.fc = nn.Linear(num_ftrs, len(self.classes))
        return model

    def _load_weights(self):
        """Loads trained weights onto the model architecture."""
        if os.path.exists(self.weights_path):
            try:
                self.model.load_state_dict(torch.load(self.weights_path, map_location=self.device))
                logger.info(f"Loaded tailored weights from {self.weights_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to load weights: {e}")
        else:
            logger.warning("Weights file not found. Using pre-trained backbone.")
        return False

    def _get_preprocess_pipeline(self):
        """Standardized image preprocessing."""
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(self.image_size),
            transforms.ToTensor(),
            transforms.Normalize(self.mean, self.std)
        ])

    def predict(self, image_path: str) -> dict:
        """
        Executes inference on a single image and applies safety logic.
        """
        if not os.path.exists(image_path):
            return {"status": "error", "message": "Image not found"}

        try:
            # 1. Image Preprocessing
            img = Image.open(image_path).convert('RGB')
            preprocess = self._get_preprocess_pipeline()
            input_tensor = preprocess(img).unsqueeze(0).to(self.device)

            # 2. Inference
            with torch.no_grad():
                output = self.model(input_tensor)
                probabilities = torch.nn.functional.softmax(output[0], dim=0)
                
            confidence, index = torch.max(probabilities, 0)
            confidence_val = confidence.item()
            predicted_class = self.classes[index.item()]

            # 3. Safety Thresholding
            if confidence_val < self.confidence_threshold:
                logger.info(f"Low confidence ({confidence_val:.2f}) for {predicted_class}. Reverting to 'other/unclear'.")
                return {
                    "status": "success",
                    "predicted_class": "other",
                    "original_prediction": predicted_class,
                    "confidence": round(confidence_val, 4),
                    "interpretation": "unclear",
                    "weights_loaded": self.weights_loaded
                }

            return {
                "status": "success",
                "predicted_class": predicted_class,
                "confidence": round(confidence_val, 4),
                "interpretation": "confident",
                "weights_loaded": self.weights_loaded
            }

        except Exception as e:
            logger.exception("Inference failure")
            return {
                "status": "error",
                "message": str(e),
                "predicted_class": "unknown",
                "confidence": 0.0
            }

# Compatibility Layer for current integration
def predict_image(image_path: str) -> dict:
    """Functional wrapper for the singleton classifier."""
    classifier = MedicalConditionClassifier()
    return classifier.predict(image_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        res = predict_image(sys.argv[1])
        print(json.dumps(res, indent=2))
    else:
        print("Usage: python predict.py <image_path>")
