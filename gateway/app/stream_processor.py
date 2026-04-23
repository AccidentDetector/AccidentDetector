import asyncio
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from typing import Optional
from collections import deque

import cv2
import httpx
import numpy as np

from .config import settings, IMAGE_MODELS, VIDEO_MODELS, MODEL_FRAME_INTERVALS
from .reporter import reporter
from .rules import resolve_action

logger = logging.getLogger(__name__)


@dataclass
class Camera:
    id: str
    rtsp_url: str
    organization_id: str
    organization_branch_id: str
    incident_type_map: dict[str, str] = field(default_factory=dict)
    notification_policy: dict[str, dict] = field(default_factory=dict)


@dataclass
class AlertState:
    last_alert: dict[str, float] = field(default_factory=dict)

    def can_alert(self, camera_id: str, model_name: str, action: str, class_name: str, cooldown_sec: int | None = None) -> bool:
        key = f"{camera_id}:{model_name}:{class_name}:{action}"
        last = self.last_alert.get(key, 0)
        effective_cooldown = cooldown_sec if cooldown_sec is not None else settings.alert_cooldown_sec
        return (time.time() - last) >= effective_cooldown

    def mark_alerted(self, camera_id: str, model_name: str, action: str, class_name: str):
        key = f"{camera_id}:{model_name}:{class_name}:{action}"
        self.last_alert[key] = time.time()


alert_state = AlertState()

async def send_payload(
    model_name: str,
    service_url: str,
    payload_bytes: bytes,
    filename: str,
    content_type: str,
    timeout: float = 10.0,
) -> Optional[dict]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.post(
                f'{service_url}/predict',
                files={'file': (filename, payload_bytes, content_type)},
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f'inference error | model={model_name} error={e}')
            return None

theft_frame_buffers = {}
theft_buffer_lock = asyncio.Lock()

async def send_theft_batch(camera_id: str, frames: list[bytes]) -> Optional[dict]:
    if not frames:
        return None
    files = [("files", (f"frame_{i}.jpg", fb, "image/jpeg")) for i, fb in enumerate(frames)]
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.post(
                f"{settings.THEFT_DETECTION_URL}/predict/batch",
                params={"camera_id": camera_id},
                files=files,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f'theft batch request failed | camera={camera_id} error={e}')
            return None

async def process_theft_frame(camera: Camera, frame_bytes: bytes):
    async with theft_buffer_lock:
        if camera.id not in theft_frame_buffers:
            theft_frame_buffers[camera.id] = deque(maxlen=16)
        buf = theft_frame_buffers[camera.id]
        buf.append(frame_bytes)
        if len(buf) == 16:
            frames = list(buf)
            buf.clear()
            asyncio.create_task(handle_theft_batch(camera, frames))
            
async def handle_theft_batch(camera: Camera, frames: list[bytes]):
    result = await send_theft_batch(camera.id, frames)
    if result:
        adapted = {
            "alert": result.get("alert", False),
            "detections": [
                {
                    "class_name": result.get("class_name", "unknown"),
                    "confidence": result.get("confidence", 0.0),
                }
            ],
        }
        await handle_result(camera, "theft-detection", adapted)

burglary_frame_buffers = {}
burglary_buffer_lock = asyncio.Lock()

async def send_burglary_batch(camera_id: str, frames: list[bytes]) -> Optional[dict]:
    if not frames:
        return None
    files = [("files", (f"frame_{i}.jpg", fb, "image/jpeg")) for i, fb in enumerate(frames)]
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.post(
                f"{settings.BURGLARY_DETECTION_URL}/predict/batch",
                params={"camera_id": camera_id},
                files=files,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f'burglary batch request failed | camera={camera_id} error={e}')
            return None

async def process_burglary_frame(camera: Camera, frame_bytes: bytes):
    async with burglary_buffer_lock:
        if camera.id not in burglary_frame_buffers:
            burglary_frame_buffers[camera.id] = deque(maxlen=16)
        buf = burglary_frame_buffers[camera.id]
        buf.append(frame_bytes)
        if len(buf) == 16:
            frames = list(buf)
            buf.clear()
            asyncio.create_task(handle_burglary_batch(camera, frames))

async def handle_burglary_batch(camera: Camera, frames: list[bytes]):
    result = await send_burglary_batch(camera.id, frames)
    if result:
        adapted = {
            "alert": result.get("alert", False),
            "detections": [
                {
                    "class_name": result.get("class_name", "unknown"),
                    "confidence": result.get("confidence", 0.0),
                }
            ],
        }
        await handle_result(camera, "burglary-detection", adapted)

async def handle_result(camera: Camera, model_name: str, result: dict):
    if not result:
        return

    for d in result.get('detections', []):
        logger.info(
            f'detection | camera={camera.id} model={model_name} '
            f'class={d["class_name"]} conf={d["confidence"]:.2f} '
            f'alert={result.get("alert", False)}'
        )

    action, confidence, class_name, cooldown_sec = resolve_action(camera, model_name, result)

    if action == "ignore":
        return

    if not alert_state.can_alert(
        camera_id=camera.id,
        model_name=model_name,
        action=action,
        class_name=class_name,
        cooldown_sec=cooldown_sec,
    ):
        logger.debug(
            f'{action} suppressed (cooldown) | camera={camera.id} '
            f'model={model_name} class={class_name}'
        )
        return

    logger.info(
        f'{action.upper()} | camera={camera.id} model={model_name} '
        f'class={class_name} conf={confidence:.2f}'
    )

    alert_state.mark_alerted(
        camera_id=camera.id,
        model_name=model_name,
        action=action,
        class_name=class_name,
    )

    incident_type_id = camera.incident_type_map.get(model_name)
    if not incident_type_id:
        logger.warning(f'no incident_type_id for model={model_name} camera={camera.id} — not reported')
        return

    await reporter.report_incident(
        camera_id=camera.id,
        organization_id=camera.organization_id,
        organization_branch_id=camera.organization_branch_id,
        incident_type_id=incident_type_id,
        confidence=confidence,
        model_name=model_name,
        class_name=class_name,
        signal_type=action,   # warning / alert
    )

def grab_latest_frame(cap: cv2.VideoCapture) -> tuple[bool, Optional[np.ndarray]]:
    ret = False
    frame = None
    for _ in range(30):
        ret = cap.grab()
        if not ret:
            break
    if not ret:
        return False, None
    ret, frame = cap.retrieve()
    return ret, frame

async def process_image_frame(camera: Camera, frame_bytes: bytes):
    # Handle batch models (theft, burglary)
    if "theft-detection" in camera.incident_type_map:
        await process_theft_frame(camera, frame_bytes)
    if "burglary-detection" in camera.incident_type_map:
        await process_burglary_frame(camera, frame_bytes)

    # All other image models (non‑batch)
    other_models = {
        name: spec for name, spec in IMAGE_MODELS.items()
        if name not in {"theft-detection", "burglary-detection"} and name in camera.incident_type_map
    }

    tasks = {
        model_name: send_payload(
            model_name=model_name,
            service_url=spec['url'],
            payload_bytes=frame_bytes,
            filename=spec['filename'],
            content_type=spec['content_type'],
            timeout=5.0,
        )
        for model_name, spec in other_models.items()
    }

    if not tasks:
        return

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    for model_name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception) or result is None:
            continue
        await handle_result(camera, model_name, result)

async def collect_clip_frames(
    cap: cv2.VideoCapture,
    first_frame: np.ndarray,
    target_frames: int,
    duration_sec: float,
) -> list[np.ndarray]:
    frames = [first_frame.copy()]
    started = time.time()
    sleep_step = max(duration_sec / max(target_frames - 1, 1), 0.01)

    while len(frames) < target_frames and (time.time() - started) < duration_sec:
        await asyncio.sleep(sleep_step)
        ret, frame = grab_latest_frame(cap)
        if not ret or frame is None or frame.size == 0:
            continue
        frames.append(frame.copy())

    while len(frames) < target_frames:
        frames.append(frames[-1].copy())

    return frames[:target_frames]

def encode_clip_to_avi(frames: list[np.ndarray], fps: int) -> Optional[bytes]:
    if not frames:
        return None
    h, w = frames[0].shape[:2]
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.avi') as tmp:
            temp_path = tmp.name
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        writer = cv2.VideoWriter(temp_path, fourcc, float(fps), (w, h))
        if not writer.isOpened():
            raise RuntimeError('could not open AVI writer')
        for frame in frames:
            if frame.shape[:2] != (h, w):
                frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
            writer.write(frame)
        writer.release()
        with open(temp_path, 'rb') as f:
            return f.read()
    except Exception as e:
        logger.error(f'video encode error: {e}')
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

async def process_camera_video_stream(camera: Camera):
    if not VIDEO_MODELS:
        return
    logger.info(f'video stream processor started | camera={camera.id} url={camera.rtsp_url}')
    while True:
        cap = cv2.VideoCapture(camera.rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
        if not cap.isOpened():
            logger.error(f'cannot open video stream | camera={camera.id} — retrying in 5s')
            cap.release()
            await asyncio.sleep(5)
            continue
        logger.info(f'video stream connected | camera={camera.id}')
        consecutive_failures = 0
        try:
            while True:
                ret, frame = grab_latest_frame(cap)
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        logger.warning(f'video stream lost | camera={camera.id} — reconnecting')
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
                for model_name, spec in VIDEO_MODELS.items():
                    if model_name not in camera.incident_type_map:
                        continue

                    clip_frames = await collect_clip_frames(
                    cap=cap,
                    first_frame=frame,
                    target_frames=spec.get('clip_frames', 16),
                    duration_sec=spec.get('clip_duration_sec', 1.0),
                    )
                    clip_bytes = encode_clip_to_avi(clip_frames, fps=spec.get('clip_fps', 16))
                    if not clip_bytes:
                        continue

                    result = await send_payload(
                    model_name=model_name,
                    service_url=spec['url'],
                    payload_bytes=clip_bytes,
                    filename=spec['filename'],
                    content_type=spec['content_type'],
                    timeout=10.0,
                )
                if result:
                    await handle_result(camera, model_name, result)
                await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f'video stream error | camera={camera.id} error={e}')
        finally:
            cap.release()
            logger.info(f'video stream disconnected | camera={camera.id}')
        await asyncio.sleep(2)

async def process_camera_stream(camera: Camera):
    logger.info(f'image stream processor started | camera={camera.id} url={camera.rtsp_url}')
    while True:
        cap = cv2.VideoCapture(camera.rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 3000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)
        if not cap.isOpened():
            logger.error(f'cannot open image stream | camera={camera.id} — retrying in 5s')
            cap.release()
            await asyncio.sleep(5)
            continue
        logger.info(f'image stream connected | camera={camera.id}')
        consecutive_failures = 0
        try:
            while True:
                ret, frame = grab_latest_frame(cap)
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= 3:
                        logger.warning(f'image stream lost | camera={camera.id} — reconnecting')
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
                ok, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if ok:
                    frame_bytes = buffer.tobytes()
                    if IMAGE_MODELS:
                        asyncio.create_task(process_image_frame(camera, frame_bytes))
                # Dynamic frame interval based on active models
                custom_interval = settings.frame_interval_sec
                for model in camera.incident_type_map.keys():
                    if model in MODEL_FRAME_INTERVALS:
                        custom_interval = min(custom_interval, MODEL_FRAME_INTERVALS[model])
                await asyncio.sleep(custom_interval)
        except Exception as e:
            logger.error(f'image stream error | camera={camera.id} error={e}')
        finally:
            cap.release()
            logger.info(f'image stream disconnected | camera={camera.id}')
        await asyncio.sleep(2)

class StreamManager:
    def __init__(self):
        self._tasks: dict[str, asyncio.Task] = {}

    def start_camera(self, camera: Camera):
        image_key = f'image:{camera.id}'
        video_key = f'video:{camera.id}'
        if image_key not in self._tasks:
            self._tasks[image_key] = asyncio.create_task(
                process_camera_stream(camera),
                name=f'stream:image:{camera.id}',
            )
            logger.info(f'started image stream task | camera={camera.id}')
        if video_key not in self._tasks and VIDEO_MODELS:
            self._tasks[video_key] = asyncio.create_task(
                process_camera_video_stream(camera),
                name=f'stream:video:{camera.id}',
            )
            logger.info(f'started video stream task | camera={camera.id}')

    def stop_camera(self, camera_id: str):
        for key in [f'image:{camera_id}', f'video:{camera_id}']:
            task = self._tasks.pop(key, None)
            if task:
                task.cancel()
                logger.info(f'stopped stream task | key={key}')

    def active_cameras(self) -> list[str]:
        return list(self._tasks.keys())

    def update_cameras(self, cameras: list[Camera]):
        new_ids = {c.id for c in cameras}
        current_camera_ids = {key.split(':', 1)[1] for key in self._tasks.keys()}
        for cam_id in current_camera_ids - new_ids:
            self.stop_camera(cam_id)
        for cam in cameras:
            if cam.id not in current_camera_ids:
                self.start_camera(cam)


stream_manager = StreamManager()