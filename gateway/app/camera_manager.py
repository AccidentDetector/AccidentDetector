import asyncio
import logging

import httpx

from .config import settings
from .stream_processor import Camera, stream_manager

logger = logging.getLogger(__name__)


async def fetch_cameras_from_backend() -> list[Camera]:
    """
    Fetch active cameras from the Go backend.
    Returns empty list if backend is not configured or unreachable.

    Expected response from Go backend:
    {
      "cameras": [
        {
          "id": "uuid",
          "rtsp_url": "rtsp://mediamtx:8554/camera-name",
          "organization_id": "uuid",
          "organization_branch_id": "uuid",
          "incident_type_map": {
            "fall-detection": "incident-type-uuid",
            "fire-detection": "incident-type-uuid"
          }
        }
      ]
    }
    """
    if not settings.backend_url:
        logger.warning('backend_url not set — using manual camera config')
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.get(
                f'{settings.backend_url}/api/v1/cameras/stream-config',
                headers={'X-Api-Key': settings.backend_api_key},
            )
            if r.status_code != 200:
                logger.error(f'failed to fetch cameras | status={r.status_code}')
                return []

            data    = r.json()
            cameras = []
            for c in data.get('cameras', []):
                cameras.append(Camera(
                    id                     = c['id'],
                    rtsp_url               = c['rtsp_url'],
                    organization_id        = c['organization_id'],
                    organization_branch_id = c['organization_branch_id'],
                    incident_type_map      = c.get('incident_type_map', {}),
                ))
            logger.info(f'fetched {len(cameras)} cameras from backend')
            return cameras

        except Exception as e:
            logger.error(f'error fetching cameras: {e}')
            return []


#def get_manual_cameras() -> list[Camera]:
    """
    Fallback — hardcode cameras here for testing before
    the Go backend exposes the stream-config endpoint.

    Remove this once backend integration is complete.
    """
    return [
        Camera(
             id                     = 'test-camera-1',
             rtsp_url               = 'rtsp://mediamtx:8554/test-camera',
             organization_id        = 'org-uuid',
             organization_branch_id = 'branch-uuid',
             incident_type_map      = {
                 'fall-detection': 'incident-type-uuid-for-fall',
                 "theft-detection": "incident-uuid-theft"
             },
         ),
    ]


async def camera_refresh_loop():
    """
    Periodically fetches the camera list from backend and
    updates the stream manager — starts new cameras, stops removed ones.
    """
    while True:
        cameras = await fetch_cameras_from_backend()

        if not cameras:
            cameras = get_manual_cameras()

        if cameras:
            stream_manager.update_cameras(cameras)
        else:
            logger.warning('no cameras configured — stream processor idle')

        await asyncio.sleep(settings.camera_refresh_sec)
