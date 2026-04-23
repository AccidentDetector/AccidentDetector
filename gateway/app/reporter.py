import logging
from datetime import datetime, timezone

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class BackendReporter:
    #when alert=true.


    def __init__(self):
        self.backend_url = settings.backend_url
        self.headers     = {
            'X-Api-Key'   : settings.backend_api_key,
            'Content-Type': 'application/json',
        }

    @property
    def configured(self) -> bool:
        return bool(self.backend_url and settings.backend_api_key)

    async def report_incident(
        self,
        camera_id: str,
        organization_id: str,
        organization_branch_id: str,
        incident_type_id: str,
        confidence: float,
        model_name: str,
        class_name: str,
        signal_type: str = "alert",
        snapshot_url: str = "",
    ) -> bool:
        if not self.configured:
            logger.warning('backend not configured — incident not reported')
            return False

        payload = {
            'camera_id'             : camera_id,
            'organization_id'       : organization_id,
            'organization_branch_id': organization_branch_id,
            'incident_type'         : incident_type_id,
            "type"                  : signal_type,
            'probability'           : round(confidence, 4),
            'detected_at'           : datetime.now(timezone.utc).isoformat(),
            'snapshot_url'          : snapshot_url,
            'description'           : f'{class_name} detected by {model_name} model',
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                r = await client.post(
                    f'{self.backend_url}/api/v1/incidents',
                    json=payload,
                    headers=self.headers,
                )
                if r.status_code == 201:
                    logger.info(f'incident reported | camera={camera_id} model={model_name} conf={confidence:.2f}')
                    return True
                else:
                    logger.error(f'backend rejected incident | status={r.status_code} body={r.text}')
                    return False
            except Exception as e:
                logger.error(f'failed to report incident: {e}')
                return False


reporter = BackendReporter()
