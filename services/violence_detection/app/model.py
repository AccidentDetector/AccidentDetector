import logging
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision.models.video import r3d_18

from app.config import settings
from app.schemas import Detection

logger = logging.getLogger(__name__)

KINETICS_MEAN = np.array([0.43216, 0.394666, 0.37645], dtype=np.float32)
KINETICS_STD  = np.array([0.22803, 0.22145,  0.216989], dtype=np.float32)


def sample_indices(num_frames: int, clip_len: int):
    if num_frames <= 0:
        return [0] * clip_len
    if num_frames < clip_len:
        idxs = list(range(num_frames))
        idxs += [num_frames - 1] * (clip_len - num_frames)
        return idxs
    return np.linspace(0, num_frames - 1, clip_len).astype(int).tolist()


def build_model(num_classes: int = 2):
    model = r3d_18(weights=None)
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(0.4),
        nn.Linear(in_features, num_classes),
    )
    return model


class ViolenceDetector:
    def __init__(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        path = Path(settings.model_path)
        if not path.exists():
            raise FileNotFoundError(f'weights not found: {path}')
        logger.info(f'loading violence model from {path} on {self.device}')
        self.model  = self._load_model(path)
        self.loaded = True
        logger.info('violence model loaded')

    def _load_model(self, path: Path):
        ckpt  = torch.load(path, map_location=self.device, weights_only=False)
        model = build_model(num_classes=2)
        model.load_state_dict(ckpt['model_state_dict'])
        model.to(self.device)
        model.eval()
        return model

    def _read_clip(self, video_path: str) -> torch.Tensor:
        cap = cv2.VideoCapture(video_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        indices = sample_indices(total, settings.clip_num_frames)

        chosen    = []
        last_good = None

        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, float(idx))
            ok, frame = cap.read()
            if ok and frame is not None:
                last_good = frame
                chosen.append(frame)
            else:
                if last_good is not None:
                    chosen.append(last_good.copy())
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ok0, frame0 = cap.read()
                    if not ok0:
                        cap.release()
                        raise RuntimeError(f'failed reading first frame: {video_path}')
                    last_good = frame0
                    chosen.append(frame)

        cap.release()

        frames = []
        for frame in chosen:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(
                frame,
                (settings.image_size, settings.image_size),
                interpolation=cv2.INTER_LINEAR,
            )
            frames.append(frame)

        frames = np.stack(frames, axis=0).astype(np.float32) / 255.0
        frames = (frames - KINETICS_MEAN[None, None, None, :]) / KINETICS_STD[None, None, None, :]
        frames = np.transpose(frames, (3, 0, 1, 2))  # C,T,H,W
        tensor = torch.from_numpy(frames).unsqueeze(0)  # 1,C,T,H,W
        return tensor.to(self.device, dtype=torch.float32)

    def predict(self, video_path: str) -> tuple[list[Detection], float]:
        start = time.time()
        x = self._read_clip(video_path)

        with torch.no_grad():
            logits = self.model(x)
            probs  = torch.softmax(logits, dim=1)[0]
            conf, cls_id = torch.max(probs, dim=0)

        cls_id   = int(cls_id.item())
        conf     = round(float(conf.item()), 4)
        cls_name = settings.class_names[cls_id]
        ms       = round((time.time() - start) * 1000, 2)

        detections = [Detection(
            class_name = cls_name,
            class_id   = cls_id,
            confidence = conf,
        )]

        logger.info(
            f'inference done | class={cls_name} conf={conf:.3f} ms={ms}'
        )
        return detections, ms


detector = ViolenceDetector()
