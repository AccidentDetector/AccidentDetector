import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import httpx
import numpy as np

from .config import settings, SERVICE_REGISTRY
from .reporter import reporter

logger = logging.getLogger(__name__)


@dataclass
class Camera:
    id                    : str
    rtsp_url              : str
    organization_id       : str
    organization_branch_id: str
    # maps model_name -> incident_type_id in Go backend DB
    incident_type_map     : dict[str, str] = field(default_factory=dict)


@dataclass
class AlertState:
    last_alert: dict[str, float] = field(default_factory=dict)

    def can_alert(self, camera_id: str, model_name: str) -> bool:
        key  = f'{camera_id}:{model_name}'
        last = self.last_alert.get(key, 0)
        return (time.time() - last) >= settings.alert_cooldown_sec

    def mark_alerted(self, camera_id: str, model_name: str):
        self.last_alert[f'{camera_id}:{model_name}'] = time.time()


alert_state = AlertState()


async def run_inference(model_name: str, service_url: str, frame_bytes: bytes) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.post(
                f'{service_url}/predict',
                files={'file': ('frame.jpg', frame_bytes, 'image/jpeg')},
            )
            return r.json()
        except Exception as e:
            logger.error(f'inference error | model={model_name} error={e}')
            return None


async def process_frame(camera: Camera, frame_bytes: bytes):
    tasks = {
        model_name: run_inference(model_name, url, frame_bytes)
        for model_name, url in SERVICE_REGISTRY.items()
    }

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for model_name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception) or result is None:
            continue

        for d in result.get('detections', []):
            logger.info(
                f'detection | camera={camera.id} model={model_name} '
                f'class={d["class_name"]} conf={d["confidence"]:.2f} '
                f'alert={result["alert"]}'
            )

        if not result.get('alert'):
            continue

        if not alert_state.can_alert(camera.id, model_name):
            logger.debug(f'alert suppressed (cooldown) | camera={camera.id} model={model_name}')
            continue

        detections = result.get('detections', [])
        top        = max(detections, key=lambda d: d['confidence'], default=None)
        confidence = top['confidence'] if top else 0.0
        class_name = top['class_name'] if top else 'unknown'

        logger.info(f'ALERT | camera={camera.id} model={model_name} class={class_name} conf={confidence:.2f}')
        alert_state.mark_alerted(camera.id, model_name)

        incident_type_id = camera.incident_type_map.get(model_name)
        if incident_type_id:
            await reporter.report_incident(
                camera_id             = camera.id,
                organization_id       = camera.organization_id,
                organization_branch_id= camera.organization_branch_id,
                incident_type_id      = incident_type_id,
                confidence            = confidence,
                model_name            = model_name,
                class_name            = class_name,
            )
        else:
            logger.warning(f'no incident_type_id for model={model_name} camera={camera.id} — not reported')


def grab_latest_frame(cap: cv2.VideoCapture) -> tuple[bool, Optional[np.ndarray]]:
    ret   = False
    frame = None

    for _ in range(30):
        ret = cap.grab()
        if not ret:
            break

    if not ret:
        return False, None

    ret, frame = cap.retrieve()
    return ret, frame


async def process_camera_stream(camera: Camera):
    logger.info(f'stream processor started | camera={camera.id} url={camera.rtsp_url}')

    while True:
        cap = cv2.VideoCapture(camera.rtsp_url, cv2.CAP_FFMPEG)

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)

        if not cap.isOpened():
            logger.error(f'cannot open stream | camera={camera.id} — retrying in 5s')
            cap.release()
            await asyncio.sleep(5)
            continue

        logger.info(f'stream connected | camera={camera.id}')
        consecutive_failures = 0

        try:
            while True:
                ret, frame = grab_latest_frame(cap)

                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        logger.warning(f'stream lost | camera={camera.id} — reconnecting')
                        break
                    await asyncio.sleep(0.5)
                    continue

                consecutive_failures = 0

                if frame.size == 0:
                    continue
                mean = frame.mean()
                if mean < 5 or mean > 250:
                    await asyncio.sleep(0.1)
                    continue

                _, buffer   = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_bytes = buffer.tobytes()
                asyncio.create_task(process_frame(camera, frame_bytes))

                await asyncio.sleep(settings.frame_interval_sec)

        except Exception as e:
            logger.error(f'stream error | camera={camera.id} error={e}')
        finally:
            cap.release()
            logger.info(f'stream disconnected | camera={camera.id}')

        await asyncio.sleep(2)


class StreamManager:

    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}

    def start_camera(self, camera: Camera):
        if camera.id in self._tasks:
            return
        task = asyncio.create_task(
            process_camera_stream(camera),
            name=f'stream:{camera.id}',
        )
        self._tasks[camera.id] = task
        logger.info(f'started stream task | camera={camera.id}')

    def stop_camera(self, camera_id: str):
        task = self._tasks.pop(camera_id, None)
        if task:
            task.cancel()
            logger.info(f'stopped stream task | camera={camera_id}')

    def active_cameras(self) -> list[str]:
        return list(self._tasks.keys())

    def update_cameras(self, cameras: list[Camera]):
        new_ids     = {c.id for c in cameras}
        current_ids = set(self._tasks.keys())

        for cam_id in current_ids - new_ids:
            self.stop_camera(cam_id)

        for cam in cameras:
            if cam.id not in current_ids:
                self.start_camera(cam)


stream_manager = StreamManager()