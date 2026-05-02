import time
import cv2
import torch
import torch.nn as nn
import torchvision.models as models

from PIL import Image
from torchvision import transforms

from app.schemas import Detection


class SuspiciousDetector:

    def __init__(self, weights_path: str):

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.model = models.resnet50(weights=None)

        self.model.fc = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(self.model.fc.in_features, 2)
        )

        self.model.load_state_dict(
            torch.load(weights_path, map_location=self.device)
        )

        self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                [0.485, 0.456, 0.406],
                [0.229, 0.224, 0.225]
            )
        ])

        self.class_names = [
            "Normal",
            "Suspicious"
        ]

    def predict(self, frame, conf_threshold=0.5):

        start = time.perf_counter()

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        image = Image.fromarray(frame)

        image = self.transform(image)
        image = image.unsqueeze(0).to(self.device)

        with torch.no_grad():

            outputs = self.model(image)

            probs = torch.softmax(outputs, dim=1)

            confidence, pred = torch.max(probs, 1)

        confidence = float(confidence.item())
        class_id = int(pred.item())

        detections = []

        if confidence >= conf_threshold:

            detections.append(
                Detection(
                    class_name=self.class_names[class_id],
                    class_id=class_id,
                    confidence=confidence,
                    box=None
                )
            )

        inference_ms = (
            time.perf_counter() - start
        ) * 1000

        return detections, inference_ms