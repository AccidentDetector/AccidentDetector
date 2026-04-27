import logging
from datetime import datetime, timezone

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class BackendReporter:
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
        camera_id             : str,
        organization_id       : str,
        organization_branch_id: str,
        incident_type_id      : str,
        confidence            : float,
        model_name            : str,
        class_name            : str,
        signal_type           : str = 'alert',  # 'warning' or 'alert'
        snapshot_url          : str = '',
    ) -> bool:
        if not self.configured:
            logger.warning(
                f'backend not configured — skipping incident report | '
                f'camera={camera_id} model={model_name} signal={signal_type}'
            )
            return False

        payload = {
            'camera_id'             : camera_id,
            'organization_id'       : organization_id,
            'organization_branch_id': organization_branch_id,
            'incident_type'         : incident_type_id,
            'type'                  : signal_type,
            'probability'           : round(confidence, 4),
            'detected_at'           : datetime.now(timezone.utc).isoformat(),
            'snapshot_url'          : snapshot_url,
            'description'           : f'{class_name} detected by {model_name}',
        }

        logger.info(
            f'reporting incident | camera={camera_id} model={model_name} '
            f'class={class_name} conf={confidence:.3f} signal={signal_type} '
            f'incident_type={incident_type_id}'
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                r = await client.post(
                    f'{self.backend_url}/api/v1/incidents',
                    json=payload,
                    headers=self.headers,
                )
                if r.status_code not in (200, 201):
                    logger.error(
                        f'backend rejected incident | status={r.status_code} '
                        f'body={r.text} camera={camera_id} model={model_name}'
                    )
                    return False

                logger.info(
                    f'incident reported successfully | camera={camera_id} '
                    f'model={model_name} signal={signal_type}'
                )
                return True

            except Exception as e:
                logger.error(
                    f'failed to reach backend | camera={camera_id} '
                    f'model={model_name} error={e}'
                )
                return False


reporter = BackendReporter()
