import logging
import time
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from .config import settings
from .schemas import Detection, BoundingBox

logger = logging.getLogger(__name__)


class FallDetector:
    def __init__(self):
        path = Path(settings.model_path)
        if not path.exists():
            raise FileNotFoundError(f'weights not found: {path}')
        logger.info(f'loading model from {path}')
        self.model  = YOLO(str(path))
        self.loaded = True
        logger.info('model loaded')

    def predict(self, image: np.ndarray) -> tuple[list[Detection], float]:
        start  = time.time()
        result = self.model.predict(image, conf=settings.conf_threshold, verbose=False)[0]
        ms     = round((time.time() - start) * 1000, 2)

        detections = []
        for box in (result.boxes or []):
            cls_id   = int(box.cls.item())
            cls_name = settings.class_names[cls_id]
            conf     = round(float(box.conf.item()), 4)
            x1, y1, x2, y2 = [round(float(v), 2) for v in box.xyxy[0].tolist()]
            detections.append(Detection(
                class_name = cls_name,
                class_id   = cls_id,
                confidence = conf,
                box        = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
            ))

        logger.info(
            f'inference done | detections={len(detections)} '
            f'classes={[d.class_name for d in detections]} ms={ms}'
        )
        return detections, ms


detector = FallDetector()
