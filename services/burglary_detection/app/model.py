import logging
import time
from pathlib import Path
import numpy as np
import torch
import torchvision.transforms as transforms
from PIL import Image
import cv2

from app.config import settings

logger = logging.getLogger(__name__)

class BurglaryDetector:
    def __init__(self):
        path = Path(settings.model_path)
        if not path.exists():
            raise FileNotFoundError(f'weights not found: {path}')
        
        logger.info(f'loading model from {path}')
        self.model = torch.jit.load(str(path), map_location='cpu')
        self.model.eval()
        logger.info('TorchScript model loaded successfully on CPU')
        
        self.transform = transforms.Compose([
            transforms.Resize((settings.img_size, settings.img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                               std=[0.229, 0.224, 0.225])
        ])
        self.loaded = True

    def preprocess_frame(self, frame: np.ndarray) -> torch.Tensor:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        return self.transform(pil_image)

    def predict_sequence(self, frames: list[np.ndarray]) -> tuple:
        """Принимает ровно 16 кадров, возвращает (alert, confidence, class_name, inference_ms)."""
        if len(frames) != settings.sequence_length:
            raise ValueError(f'Expected {settings.sequence_length} frames, got {len(frames)}')
        
        start = time.time()
        tensors = [self.preprocess_frame(f) for f in frames]
        sequence = torch.stack(tensors).unsqueeze(0)  # (1, 16, C, H, W)
        
        with torch.no_grad():
            output = self.model(sequence)
            probs = torch.softmax(output, dim=1)
            confidence, pred_class = torch.max(probs, dim=1)
            confidence = confidence.item()
            class_id = pred_class.item()
            class_name = settings.class_names[class_id]
        
        ms = round((time.time() - start) * 1000, 2)
        alert = (class_name == settings.alert_class and confidence >= settings.conf_threshold)
        
        if alert:
            logger.warning(f'🚨 ALERT! {class_name} ({confidence:.3f})')
        else:
            logger.info(f'Prediction: {class_name} ({confidence:.3f})')
        
        return alert, confidence, class_name, ms

detector = BurglaryDetector()